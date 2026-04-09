"""
Carga de datos desde Redshift con caché por combinación de filtros.

Expone cuatro funciones públicas:
  load_orders(filters)      → DataFrame seller × order_month × lifecycle_month × order_count
  load_revenue(filters)     → DataFrame seller × revenue_month × lifecycle_month × total_revenue
  load_forecast(filters)    → DataFrame seller × forecast_month × lifecycle_month × forecasted_orders
  load_last_order_month()   → date | None — último mes con órdenes reales (para landing)

Filtros válidos (dict):
  segments           : list[str]  – default ['Starter','Plus','Top','Enterprise']
  include_churn      : bool       – default True
  country_id         : int|None   – None=ambos, 1=COL, 2=MEX
  order_type         : str|None   – None=ambos, 'D2C', 'B2B'
  include_credit_notes: bool      – default False (solo revenue)
"""
import os
import re
import logging
import threading
from pathlib import Path

import pandas as pd
from cachetools import TTLCache

from data.connection import get_connection

logger = logging.getLogger(__name__)

_QUERIES_DIR = Path(__file__).parent.parent / "queries"
_TTL = int(os.environ.get("CACHE_TTL_SECONDS", 1800))  # 30 min default

_orders_cache: TTLCache = TTLCache(maxsize=50, ttl=_TTL)
_revenue_cache: TTLCache = TTLCache(maxsize=50, ttl=_TTL)
_forecast_cache: TTLCache = TTLCache(maxsize=50, ttl=_TTL)
_status_cache: TTLCache = TTLCache(maxsize=4, ttl=3600)   # 1 h — para landing
_lock = threading.Lock()

# ── Defaults ────────────────────────────────────────────────────────────────

_DEFAULT_SEGMENTS = ["Starter", "Plus", "Top", "Enterprise"]


def _default_filters() -> dict:
    return {
        "segments": _DEFAULT_SEGMENTS,
        "include_churn": True,
        "country_id": None,
        "order_type": None,
        "include_credit_notes": False,
    }


def _merge_filters(filters: dict | None) -> dict:
    merged = _default_filters()
    if filters:
        merged.update(filters)
    return merged


# ── Cache key ────────────────────────────────────────────────────────────────

def _cache_key(filters: dict) -> tuple:
    """Convierte el dict de filtros a una tupla hashable."""
    return tuple(
        sorted(
            (k, tuple(v) if isinstance(v, list) else v)
            for k, v in filters.items()
        )
    )


# ── SQL injection ────────────────────────────────────────────────────────────

def _build_params_cte(filters: dict) -> str:
    """Construye el CTE 'params' con los valores del filtro."""
    segments = filters["segments"]
    seg_array = "ARRAY[" + ", ".join(f"'{s}'" for s in segments) + "]"
    churn_val = "TRUE" if filters["include_churn"] else "FALSE"
    country_id = filters["country_id"]
    country_val = f"{country_id}::INTEGER" if country_id is not None else "NULL::INTEGER"
    order_type = filters["order_type"]
    ot_val = f"'{order_type}'::VARCHAR" if order_type else "NULL::VARCHAR"
    cn_val = "TRUE" if filters["include_credit_notes"] else "FALSE"

    return (
        "params AS (\n"
        "    SELECT\n"
        f"        {seg_array}  AS segment_filter,\n"
        f"        {churn_val}                                           AS include_churn,\n"
        f"        {country_val}                                         AS country_filter,\n"
        f"        {ot_val}                                              AS order_type_filter,\n"
        f"        {cn_val}                                              AS include_credit_notes\n"
        "),"
    )


def _inject_filters(sql: str, filters: dict) -> str:
    """Reemplaza el CTE 'params' en el SQL con los valores del filtro."""
    new_params = _build_params_cte(filters)

    # Encuentra el bloque params AS (...), y lo reemplaza
    lines = sql.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if re.match(r"\s*params\s+AS\s*\(", line, re.IGNORECASE):
            start = i
        if start is not None and i > start and re.match(r"\s*\)\s*,", line):
            end = i
            break

    if start is not None and end is not None:
        return "\n".join(lines[:start] + new_params.splitlines() + lines[end + 1:])

    logger.warning("No se encontró el bloque params CTE en el SQL; se ejecuta sin modificar.")
    return sql


# ── Ejecución ────────────────────────────────────────────────────────────────

def _run_query(sql: str) -> pd.DataFrame:
    """Ejecuta una query en Redshift y retorna un DataFrame."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception as exc:
        logger.error("Error ejecutando query en Redshift: %s", exc)
        return pd.DataFrame()


def _read_sql(filename: str) -> str:
    path = _QUERIES_DIR / filename
    return path.read_text(encoding="utf-8")


# ── API pública ──────────────────────────────────────────────────────────────

def load_orders(filters: dict | None = None) -> pd.DataFrame:
    """
    Carga órdenes por seller × mes desde staging.orbita.sell_order.

    Columnas del DataFrame:
        seller_id, seller_name, segment, country_id, country_name,
        cohort_month, churn_flag, order_month, order_type,
        lifecycle_month, order_count
    """
    filters = _merge_filters(filters)
    key = ("orders",) + _cache_key(filters)

    with _lock:
        if key in _orders_cache:
            return _orders_cache[key]

    sql = _read_sql("01_inputs_orders.sql")
    sql = _inject_filters(sql, filters)
    df = _run_query(sql)

    if not df.empty:
        df["cohort_month"] = pd.to_datetime(df["cohort_month"])
        df["order_month"] = pd.to_datetime(df["order_month"])
        df["order_count"] = pd.to_numeric(df["order_count"], errors="coerce").fillna(0)
        df["lifecycle_month"] = pd.to_numeric(df["lifecycle_month"], errors="coerce").astype("Int64")

    with _lock:
        _orders_cache[key] = df

    return df


def load_revenue(filters: dict | None = None) -> pd.DataFrame:
    """
    Carga revenue P&L por seller × mes (dual source: histórico + Redshift).

    Columnas del DataFrame:
        seller_id, seller_name, segment, country_id, country_name,
        cohort_month, churn_flag, revenue_month, lifecycle_month,
        fulfillment_revenue, returns_revenue, warehousing_revenue,
        inbound_revenue, saas_revenue, external_revenue,
        adjecencies_revenue, credit_notes_adjustment, total_revenue
    """
    filters = _merge_filters(filters)
    key = ("revenue",) + _cache_key(filters)

    with _lock:
        if key in _revenue_cache:
            return _revenue_cache[key]

    sql = _read_sql("02_inputs_revenue.sql")
    sql = _inject_filters(sql, filters)
    df = _run_query(sql)

    if not df.empty:
        df["cohort_month"] = pd.to_datetime(df["cohort_month"])
        df["revenue_month"] = pd.to_datetime(df["revenue_month"])
        df["total_revenue"] = pd.to_numeric(df["total_revenue"], errors="coerce").fillna(0)
        df["lifecycle_month"] = pd.to_numeric(df["lifecycle_month"], errors="coerce").astype("Int64")

    with _lock:
        _revenue_cache[key] = df

    return df


def load_forecast(filters: dict | None = None) -> pd.DataFrame:
    """
    Carga el forecast de órdenes por seller × mes desde core.forecast.official_forecast_temp.
    La tabla ya expone el forecast oficial vigente — no se filtra por version_id.
    Cubre hasta Dic 2026.

    Filtros aplicados: country_id, segments (vía params CTE).
    No aplican: include_churn, order_type, include_credit_notes.

    Columnas del DataFrame:
        seller_id, cohort_month, segment, country_id,
        lifecycle_month, forecast_month, forecasted_orders
    """
    filters = _merge_filters(filters)
    key = ("forecast",) + _cache_key(filters)

    with _lock:
        if key in _forecast_cache:
            return _forecast_cache[key]

    sql = _read_sql("03_inputs_forecast.sql")

    # El query 03 tiene un params CTE distinto (country_filter + segment_filter como VARCHAR)
    # Se inyecta manualmente para respetar su estructura particular.
    country_id = filters["country_id"]
    segments = filters["segments"]
    country_val = f"{country_id}::INTEGER" if country_id is not None else "NULL::INTEGER"
    # segment_filter en el query 03 es un único valor VARCHAR (o NULL para todos)
    # Si hay múltiples segmentos activos se pasa NULL y el filtro del WHERE usa la lista fija
    seg_val = "NULL::VARCHAR"

    new_params = (
        "params AS (\n"
        "    SELECT\n"
        f"        {country_val}  AS country_filter,\n"
        f"        {seg_val}      AS segment_filter\n"
        "),"
    )

    lines = sql.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if re.match(r"\s*params\s+AS\s*\(", line, re.IGNORECASE):
            start = i
        if start is not None and i > start and re.match(r"\s*\)\s*,", line):
            end = i
            break

    if start is not None and end is not None:
        sql = "\n".join(lines[:start] + new_params.splitlines() + lines[end + 1:])

    # Si los segmentos no son el default completo, filtramos en Python post-query
    df = _run_query(sql)

    if not df.empty:
        df["cohort_month"] = pd.to_datetime(df["cohort_month"])
        df["forecast_month"] = pd.to_datetime(df["forecast_month"])
        df["forecasted_orders"] = pd.to_numeric(df["forecasted_orders"], errors="coerce").fillna(0)
        df["lifecycle_month"] = pd.to_numeric(df["lifecycle_month"], errors="coerce").astype("Int64")

        # Filtrar segmentos en Python si el usuario no quiere todos
        if segments != _DEFAULT_SEGMENTS:
            df = df[df["segment"].isin(segments)]

    with _lock:
        _forecast_cache[key] = df

    return df


def load_last_order_month() -> "date | None":
    """
    Retorna el último mes calendario con órdenes reales en Redshift.
    Usa la misma fuente que 01_inputs_orders.sql (staging.orbita.sell_order_log
    con sell_order_state_id = 2 y bodega operada por Melonn).

    Resultado cacheado 1 hora — ideal para la landing page.
    """
    from datetime import date as _date  # evitar shadowing del módulo

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


def clear_cache() -> None:
    """Limpia todas las cachés manualmente (útil para testing)."""
    with _lock:
        _orders_cache.clear()
        _revenue_cache.clear()
        _forecast_cache.clear()
        _status_cache.clear()
