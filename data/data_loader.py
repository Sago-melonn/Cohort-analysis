"""
Carga de datos desde Redshift con caché en memoria.

Patrón unificado para orders, revenue y forecast:
  1. _load_*_raw()  → ejecuta la query V2 (sin filtros) y cachea el DataFrame completo
  2. load_*()       → obtiene el raw cacheado y aplica filtros en Python

Esto garantiza que un cambio de filtro en la UI nunca dispara una nueva
query a Redshift — solo reorganiza datos ya en memoria.

Expone cuatro funciones públicas:
  load_orders(filters)      → DataFrame seller × order_month × lifecycle_month × order_count
  load_revenue(filters)     → DataFrame seller × revenue_month × lifecycle_month × total_revenue
  load_forecast(filters)    → DataFrame seller × forecast_month × lifecycle_month × forecasted_orders
  load_last_order_month()   → date | None — último mes con órdenes reales (para landing)

Filtros válidos (dict):
  segments           : list[str]  – default ['Starter','Plus','Top','Enterprise']
  include_churn      : bool       – default True
  country_id         : int|None   – None=ambos, 1=COL, 2=MEX
  order_type         : str|None   – None=ambos, 'D2C', 'B2B'  (solo revenue)
  include_credit_notes: bool      – default False              (solo revenue)
"""
import logging
import os
import threading
from pathlib import Path

import pandas as pd
from cachetools import TTLCache

from data.connection import get_connection, release_connection

logger = logging.getLogger(__name__)

_QUERIES_DIR = Path(__file__).parent.parent / "queries"
_TTL = int(os.environ.get("CACHE_TTL_SECONDS", 1800))  # 30 min default

# Cachés raw — una entrada por tipo de dato (sin filtros)
_orders_raw_cache:   TTLCache = TTLCache(maxsize=4, ttl=_TTL)
_revenue_raw_cache:  TTLCache = TTLCache(maxsize=4, ttl=_TTL)
_forecast_raw_cache: TTLCache = TTLCache(maxsize=4, ttl=_TTL)
_budget_cache:       TTLCache = TTLCache(maxsize=4, ttl=_TTL)

# Cachés de resultados filtrados — evita re-filtrar si el usuario vuelve al mismo combo
_orders_cache:   TTLCache = TTLCache(maxsize=50, ttl=_TTL)
_revenue_cache:  TTLCache = TTLCache(maxsize=50, ttl=_TTL)
_forecast_cache: TTLCache = TTLCache(maxsize=50, ttl=_TTL)

_status_cache:   TTLCache = TTLCache(maxsize=4, ttl=3600)  # 1 h — para landing

_lock = threading.Lock()

# ── Aliases y defaults ────────────────────────────────────────────────────────

_DEFAULT_SEGMENTS = ["Starter", "Plus", "Top", "Enterprise"]
_SEGMENT_ALIASES  = {"Starter": ["Starter", "Tiny"]}


def _default_filters() -> dict:
    return {
        "segments":             _DEFAULT_SEGMENTS,
        "include_churn":        True,
        "country_id":           None,
        "order_type":           None,
        "include_credit_notes": False,
    }


def _merge_filters(filters: dict | None) -> dict:
    merged = _default_filters()
    if filters:
        merged.update(filters)
    return merged


def _cache_key(filters: dict) -> tuple:
    return tuple(
        sorted(
            (k, tuple(v) if isinstance(v, list) else v)
            for k, v in filters.items()
        )
    )


# ── Ejecución SQL ─────────────────────────────────────────────────────────────

def _run_query(sql: str, _retries: int = 2) -> pd.DataFrame:
    last_exc: Exception | None = None
    for attempt in range(1, _retries + 2):
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            release_connection(conn)          # ← devuelve al pool en vez de cerrar
            return pd.DataFrame(rows, columns=cols)
        except Exception as exc:
            if conn:
                try: conn.close()
                except: pass
            last_exc = exc
            is_conn_err = any(
                kw in str(exc).lower()
                for kw in ("connection", "communication", "10054", "broken pipe", "reset")
            )
            if is_conn_err and attempt <= _retries:
                logger.warning("Redshift connection error (intento %d/%d): %s — reintentando…", attempt, _retries + 1, exc)
                continue
            break
    logger.error("Error ejecutando query en Redshift: %s", last_exc)
    return pd.DataFrame()

def _read_sql(filename: str) -> str:
    return (_QUERIES_DIR / filename).read_text(encoding="utf-8")


# ── Filtros Python (comunes a orders y forecast) ──────────────────────────────

def _apply_common_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Aplica segmento, país y churn sobre un DataFrame ya cargado."""
    if df.empty:
        return df

    # Segmentos (con alias Tiny = Starter)
    segments = filters["segments"]
    expanded: list[str] = []
    for s in segments:
        expanded.extend(_SEGMENT_ALIASES.get(s, [s]))
    df = df[df["segment"].isin(expanded)]

    # País
    if filters["country_id"] is not None:
        df = df[df["country_id"] == filters["country_id"]]

    # Churn
    if not filters["include_churn"] and "churn_flag" in df.columns:
        df = df[df["churn_flag"] == 0]

    return df


# ── ORDERS ────────────────────────────────────────────────────────────────────

def _load_orders_raw() -> pd.DataFrame:
    """Carga TODOS los datos de órdenes (V2 sin filtros). Resultado cacheado."""
    key = "orders_raw"
    with _lock:
        if key in _orders_raw_cache:
            return _orders_raw_cache[key]

    sql = _read_sql("01_inputs_orders_V2.sql")
    df  = _run_query(sql)

    if not df.empty:
        df["cohort_month"]    = pd.to_datetime(df["cohort_month"])
        df["order_month"]     = pd.to_datetime(df["order_month"])
        df["order_count"]     = pd.to_numeric(df["order_count"], errors="coerce").fillna(0)
        df["lifecycle_month"] = pd.to_numeric(df["lifecycle_month"], errors="coerce").astype("Int64")
        df["churn_flag"]      = pd.to_numeric(df["churn_flag"], errors="coerce").fillna(0).astype(int)

    with _lock:
        _orders_raw_cache[key] = df

    return df


def load_orders(filters: dict | None = None) -> pd.DataFrame:
    """
    Órdenes totales (D2C + B2B) por seller × mes.

    Columnas:
        seller_id, seller_name, segment, country_id, country_name,
        cohort_month, churn_flag, order_month, lifecycle_month, order_count
    """
    filters = _merge_filters(filters)
    key = ("orders",) + _cache_key(filters)

    with _lock:
        if key in _orders_cache:
            return _orders_cache[key]

    df = _apply_common_filters(_load_orders_raw().copy(), filters)

    with _lock:
        _orders_cache[key] = df

    return df


# ── REVENUE ───────────────────────────────────────────────────────────────────

def _load_revenue_raw() -> pd.DataFrame:
    """Carga TODO el revenue (V2 sin filtros). Resultado cacheado."""
    key = "revenue_raw"
    with _lock:
        if key in _revenue_raw_cache:
            return _revenue_raw_cache[key]

    sql = _read_sql("02_inputs_revenue_V2.sql")
    df  = _run_query(sql)

    if not df.empty:
        df["cohort_month"]    = pd.to_datetime(df["cohort_month"])
        df["revenue_month"]   = pd.to_datetime(df["revenue_month"])
        df["lifecycle_month"] = pd.to_numeric(df["lifecycle_month"], errors="coerce").astype("Int64")
        df["churn_flag"]      = pd.to_numeric(df["churn_flag"], errors="coerce").fillna(0).astype(int)
        for col in ["total_revenue", "fulfillment_revenue", "d2c_fulfillment_revenue",
                    "b2b_fulfillment_revenue", "returns_revenue", "warehousing_revenue",
                    "inbound_revenue", "saas_revenue", "external_revenue",
                    "adjecencies_revenue", "credit_notes_amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    with _lock:
        _revenue_raw_cache[key] = df

    return df


def load_revenue(filters: dict | None = None) -> pd.DataFrame:
    """
    Revenue P&L por seller × mes — filtros aplicados en memoria.

    Columnas:
        seller_id, seller_name, segment, country_id, country_name,
        cohort_month, churn_flag, revenue_month, lifecycle_month,
        fulfillment_revenue, d2c_fulfillment_revenue, b2b_fulfillment_revenue,
        returns_revenue, warehousing_revenue, inbound_revenue, saas_revenue,
        external_revenue, adjecencies_revenue, credit_notes_amount, total_revenue
    """
    filters = _merge_filters(filters)
    key = ("revenue",) + _cache_key(filters)

    with _lock:
        if key in _revenue_cache:
            return _revenue_cache[key]

    df = _apply_common_filters(_load_revenue_raw().copy(), filters)

    if not df.empty:
        # Tipo de orden: recomponer total_revenue con split D2C o B2B
        order_type = filters["order_type"]
        if order_type in ("D2C", "B2B"):
            fulf_col = "d2c_fulfillment_revenue" if order_type == "D2C" else "b2b_fulfillment_revenue"
            other = ["returns_revenue", "warehousing_revenue", "inbound_revenue",
                     "saas_revenue", "external_revenue", "adjecencies_revenue"]
            df = df.copy()
            df["total_revenue"] = df[[fulf_col] + [c for c in other if c in df.columns]].sum(axis=1)

        # Credit notes
        if filters["include_credit_notes"] and "credit_notes_amount" in df.columns:
            if filters["order_type"] not in ("D2C", "B2B"):
                df = df.copy()
            df["total_revenue"] = df["total_revenue"] - df["credit_notes_amount"]

    with _lock:
        _revenue_cache[key] = df

    return df


# ── FORECAST ──────────────────────────────────────────────────────────────────

def _load_forecast_raw() -> pd.DataFrame:
    """Carga TODO el forecast (V2 sin filtros). Resultado cacheado."""
    key = "forecast_raw"
    with _lock:
        if key in _forecast_raw_cache:
            return _forecast_raw_cache[key]

    sql = _read_sql("03_inputs_forecast_V2.sql")
    df  = _run_query(sql)

    if not df.empty:
        df["cohort_month"]      = pd.to_datetime(df["cohort_month"])
        df["forecast_month"]    = pd.to_datetime(df["forecast_month"])
        df["forecasted_orders"] = pd.to_numeric(df["forecasted_orders"], errors="coerce").fillna(0)
        df["lifecycle_month"]   = pd.to_numeric(df["lifecycle_month"], errors="coerce").astype("Int64")
        if "churn_flag" in df.columns:
            df["churn_flag"] = pd.to_numeric(df["churn_flag"], errors="coerce").fillna(0).astype(int)

    with _lock:
        _forecast_raw_cache[key] = df

    return df


def load_forecast(filters: dict | None = None) -> pd.DataFrame:
    """
    Forecast de órdenes por seller × mes (hasta Dic 2026).

    Columnas:
        seller_id, seller_name, cohort_month, segment, country_id,
        churn_flag, lifecycle_month, forecast_month, forecasted_orders
    """
    filters = _merge_filters(filters)
    key = ("forecast",) + _cache_key(filters)

    with _lock:
        if key in _forecast_cache:
            return _forecast_cache[key]

    df = _apply_common_filters(_load_forecast_raw().copy(), filters)

    with _lock:
        _forecast_cache[key] = df

    return df


# ── LAST ORDER MONTH (landing) ────────────────────────────────────────────────

def load_last_order_month() -> "date | None":
    """Retorna el último mes calendario con órdenes reales. Cacheado 1 hora."""
    from datetime import date as _date  # evitar shadowing

    key = "last_order_month"
    with _lock:
        if key in _status_cache:
            return _status_cache[key]

    sql = """
    SELECT MAX(
        DATE_TRUNC('month',
            CONVERT_TIMEZONE('UTC', w.timezone_code, iri.date)
        )::DATE
    ) AS last_month
    FROM staging.orbita.sell_order AS so
    INNER JOIN staging.orbita.warehouse AS w
        ON so.assigned_warehouse_id = w.id
    INNER JOIN (
        SELECT sell_order_id, MIN(action_date) AS date
        FROM staging.orbita.sell_order_log
        WHERE sell_order_state_id = 2
        GROUP BY sell_order_id
    ) AS iri
        ON so.id = iri.sell_order_id
    WHERE w.operated_by_melonn = 1
      AND iri.date IS NOT NULL
    """

    df = _run_query(sql)
    result = None
    if not df.empty and df.iloc[0, 0] is not None:
        result = pd.to_datetime(df.iloc[0, 0]).date()

    with _lock:
        _status_cache[key] = result

    return result


# ── BUDGET NNR/NNO ────────────────────────────────────────────────────────────

def load_budget_nnr() -> pd.DataFrame:
    """
    Budget NNR/NNO 2026 desde staging.finance.financial_planning_budget_nnr.

    Columnas: date, country_id,
              budget_nnr_base, budget_nno_base,   ← escenario Base / "Junta"
              budget_nnr_bear, budget_nno_bear     ← escenario Bear
    budget_nnr_* en USD brutos; budget_nno_* en órdenes.
    """
    key = "budget_nnr"
    with _lock:
        if key in _budget_cache:
            return _budget_cache[key]

    sql = _read_sql("04_inputs_budget_nnr.sql")
    df  = _run_query(sql)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        for col in ["budget_nnr_base", "budget_nno_base",
                    "budget_nnr_bear", "budget_nno_bear"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    with _lock:
        _budget_cache[key] = df

    return df


# ── SELLERS (config page) ─────────────────────────────────────────────────────

def load_sellers() -> pd.DataFrame:
    """Lista única de sellers con su cohort_month original desde Redshift."""
    df = _load_orders_raw()
    if df.empty:
        return pd.DataFrame(columns=["seller_id", "seller_name", "cohort_month", "country_id", "country_name"])

    cols = [c for c in ["seller_id", "seller_name", "cohort_month", "country_id", "country_name"] if c in df.columns]
    return (
        df[cols]
        .sort_values("cohort_month")
        .drop_duplicates(subset=["seller_id"], keep="first")
        .sort_values("seller_name")
        .reset_index(drop=True)
    )


# ── Utilidades ────────────────────────────────────────────────────────────────

def clear_cache() -> None:
    """Limpia todas las cachés manualmente (útil para testing)."""
    with _lock:
        _orders_raw_cache.clear()
        _revenue_raw_cache.clear()
        _forecast_raw_cache.clear()
        _budget_cache.clear()
        _orders_cache.clear()
        _revenue_cache.clear()
        _forecast_cache.clear()
        _status_cache.clear()
