"""
Transformaciones puras sobre DataFrames — compartidas por todos los callbacks.
Sin I/O ni imports de Dash.
"""
import numpy as np
import pandas as pd


# ── Mapeos ────────────────────────────────────────────────────────────────────

_COUNTRY_MAP = {"CONSOLIDADO": None, "COL": 1, "MEX": 2}
_CHURN_MAP   = {"incluir": True, "excluir": False}
_OT_MAP      = {"ambos": None, "D2C": "D2C", "B2B": "B2B"}


def build_filters(pais: str, segmentos: list, churn: str, order_type: str) -> dict:
    """Traduce valores del sidebar al dict de filtros que acepta data_loader."""
    return {
        "segments":             list(segmentos) if segmentos else ["Starter", "Plus", "Top", "Enterprise"],
        "include_churn":        _CHURN_MAP.get(churn, True),
        "country_id":           _COUNTRY_MAP.get(pais),
        "order_type":           _OT_MAP.get(order_type),
        "include_credit_notes": False,
    }


# ── Revenue display ───────────────────────────────────────────────────────────

def revenue_display_unit(pais: str, moneda: str = "local") -> str:
    """Etiqueta de la unidad de display según país y moneda."""
    if pais == "CONSOLIDADO" or moneda == "usd":
        return "K USD"
    if pais == "COL":
        return "MM COP"
    if pais == "MEX":
        return "K MXN"
    return "K USD"


def prepare_revenue(
    df_rev: pd.DataFrame,
    pais: str,
    moneda: str,
    fx_cop: float,
    fx_mxn: float,
) -> pd.DataFrame:
    """
    Agrega columna 'display_value' según país y moneda:
      COL  + local → MM COP  (÷ 1_000_000)
      MEX  + local → K MXN   (÷ 1_000)
      *    + usd   → K USD   (÷ FX ÷ 1_000)
      CONSOLIDADO  → K USD   (siempre, ambos países convertidos)
    Retorna una copia; no modifica el original.
    """
    if df_rev.empty:
        df = df_rev.copy()
        df["display_value"] = pd.Series(dtype=float)
        return df

    df = df_rev.copy()
    fx_cop = float(fx_cop or 3800)
    fx_mxn = float(fx_mxn or 17.5)
    moneda = moneda or "local"

    if pais == "COL" and moneda == "local":
        df["display_value"] = df["total_revenue"] / 1_000_000
    elif pais == "MEX" and moneda == "local":
        df["display_value"] = df["total_revenue"] / 1_000          # K MXN
    else:
        # USD o CONSOLIDADO: convertir cada fila según country_id
        df["display_value"] = df.apply(
            lambda r: r["total_revenue"] / (fx_cop * 1_000)
            if r["country_id"] == 1
            else r["total_revenue"] / (fx_mxn * 1_000),
            axis=1,
        )
    return df


# ── KPIs ──────────────────────────────────────────────────────────────────────

def calc_nnr(
    df_rev_prepared: pd.DataFrame,
    corte_base: str,
    estacionalidad: float,
) -> float | None:
    """
    NNR = avg(display_value en M2 y M3) por seller × factor estacionalidad.
    Espera df con columna 'display_value' ya calculada (de prepare_revenue).
    Solo cohortes con cohort_month > corte_base (sellers "nuevos").
    """
    if df_rev_prepared.empty or "display_value" not in df_rev_prepared.columns:
        return None
    try:
        cutoff = pd.Timestamp(corte_base)
    except Exception:
        return None

    nuevos = df_rev_prepared[df_rev_prepared["cohort_month"] > cutoff]
    m23 = nuevos[nuevos["lifecycle_month"].isin([2, 3])]
    if m23.empty:
        return None

    per_seller = m23.groupby("seller_id")["display_value"].mean()
    return round(float(per_seller.mean()) * float(estacionalidad or 1.0), 2)


def calc_nno(df_orders: pd.DataFrame, corte_base: str) -> float | None:
    """
    NNO = avg(order_count en M2 y M3) por seller.
    Solo cohortes con cohort_month > corte_base.
    """
    if df_orders.empty:
        return None
    try:
        cutoff = pd.Timestamp(corte_base)
    except Exception:
        return None

    nuevos = df_orders[df_orders["cohort_month"] > cutoff]
    m23 = nuevos[nuevos["lifecycle_month"].isin([2, 3])]
    if m23.empty:
        return None

    per_seller = m23.groupby("seller_id")["order_count"].mean()
    return round(float(per_seller.mean()), 1)


# ── Pivot ─────────────────────────────────────────────────────────────────────

def pivot_cohort(df: pd.DataFrame, value_col: str, date_col: str) -> pd.DataFrame:
    """
    Pivot: cohort_month (filas) × date_col (columnas), valores = sum(value_col).
    - Index formateado como "YYYY-MM" (nombre "Cohorte").
    - Columnas formateadas como "YYYY-MM".
    - Celdas sin dato → NaN.
    """
    if df.empty:
        return pd.DataFrame()

    agg = (
        df.groupby(["cohort_month", date_col])[value_col]
        .sum()
        .reset_index()
    )
    pivot = agg.pivot(index="cohort_month", columns=date_col, values=value_col)
    pivot.index = pd.to_datetime(pivot.index).strftime("%Y-%m")
    pivot.columns = pd.to_datetime(pivot.columns).strftime("%Y-%m")
    pivot.index.name = "Cohorte"
    pivot.columns.name = None
    return pivot.sort_index()


def pivot_cohort_by_year(df: pd.DataFrame, value_col: str, date_col: str) -> pd.DataFrame:
    """
    Pivot: cohort_year (filas) × date_col (columnas), valores = sum(value_col).
    Agrupa cohort_month por año de cohorte ("2021", "2022", ...).
    - Index: año de cohorte como string (nombre "Cohorte").
    - Columnas: date_col formateado como "YYYY-MM".
    - Celdas sin dato → NaN.
    """
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["cohort_year"] = pd.to_datetime(tmp["cohort_month"]).dt.year.astype(str)

    agg = (
        tmp.groupby(["cohort_year", date_col])[value_col]
        .sum()
        .reset_index()
    )
    pivot = agg.pivot(index="cohort_year", columns=date_col, values=value_col)
    pivot.columns = pd.to_datetime(pivot.columns).strftime("%Y-%m")
    pivot.index.name = "Cohorte"
    pivot.columns.name = None
    return pivot.sort_index()


# ── Retención NOR / NRR ───────────────────────────────────────────────────────

def calc_retention_series(
    df: pd.DataFrame,
    value_col: str,
    month_col: str,
    universe_mode: str,
    corte_base: str,
    df_forecast: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Calcula la serie mensual de retención (NOR u NRR).

    Algoritmo:
      1. Agrega value_col por (cohort_month, month_col).
      2. Suavizado rolling 3 meses por cohorte (min_periods=1).
      3. Por cada mes M filtra el universo y calcula ratio = smooth(M) / smooth(M-12).

    universe_mode:
      "base"  → cohort_month ≤ corte_base  (fijo)
      "todos" → cohort_month < M-12        (dinámico; para Mar-2026 → hasta Feb-2025)

    df_forecast: extiende la serie con forecasted_orders para meses futuros.
                 Solo aplica cuando month_col == "order_month".

    Retorna DataFrame con columnas:
        month, cohorts_cutoff, smooth_num, smooth_den, ratio, is_forecast
    """
    _empty = pd.DataFrame(
        columns=["month", "cohorts_cutoff", "smooth_num", "smooth_den", "ratio", "is_forecast"]
    )
    if df.empty:
        return _empty

    df = df.copy()
    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    df[month_col] = pd.to_datetime(df[month_col])

    # Paso 1 — agregar por (cohorte, mes)
    agg = (
        df.groupby(["cohort_month", month_col])[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: "_val"})
    )

    last_actual = agg[month_col].max()

    # Agregar meses de forecast (solo órdenes, futuros al último mes real)
    if df_forecast is not None and not df_forecast.empty:
        df_fc = df_forecast.copy()
        df_fc["cohort_month"]   = pd.to_datetime(df_fc["cohort_month"])
        df_fc["forecast_month"] = pd.to_datetime(df_fc["forecast_month"])
        fc_agg = (
            df_fc.groupby(["cohort_month", "forecast_month"])["forecasted_orders"]
            .sum()
            .reset_index()
            .rename(columns={"forecast_month": month_col, "forecasted_orders": "_val"})
        )
        fc_future = fc_agg[fc_agg[month_col] > last_actual]
        if not fc_future.empty:
            agg = pd.concat([agg, fc_future], ignore_index=True)

    # Paso 2 — suavizado rolling 3 por cohorte (min_periods=1 → usa lo que hay)
    agg = agg.sort_values(["cohort_month", month_col])
    agg["smooth"] = (
        agg.groupby("cohort_month")["_val"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )

    try:
        cutoff_base = pd.Timestamp(corte_base)
    except Exception:
        cutoff_base = pd.Timestamp("2024-12-01")

    all_months = sorted(agg[month_col].unique())
    records = []

    for M in all_months:
        M = pd.Timestamp(M)

        if universe_mode == "base":
            cutoff = cutoff_base
        else:
            # "todos": cohort_month < M-12  ≡  cohort_month ≤ M-13 meses
            cutoff = pd.Timestamp(M - pd.DateOffset(months=13))

        # Numerador: smooth del universo en mes M
        num_rows = agg[(agg[month_col] == M) & (agg["cohort_month"] <= cutoff)]
        smooth_M = float(num_rows["smooth"].sum())

        # Denominador: smooth del mismo universo en mes M-12
        M12 = pd.Timestamp(M - pd.DateOffset(months=12))
        den_rows = agg[(agg[month_col] == M12) & (agg["cohort_month"] <= cutoff)]
        smooth_M12 = float(den_rows["smooth"].sum())

        ratio = smooth_M / smooth_M12 if smooth_M12 > 0 else None

        records.append({
            "month":          M,
            "cohorts_cutoff": cutoff,
            "smooth_num":     round(smooth_M,  2),
            "smooth_den":     round(smooth_M12, 2),
            "ratio":          round(ratio, 4) if ratio is not None else None,
            "is_forecast":    M > last_actual,
        })

    return pd.DataFrame(records) if records else _empty


# ── NDR / ODR — Cohort matrix ─────────────────────────────────────────────────

def calc_cohort_matrix(
    df: pd.DataFrame,
    value_col: str,
    lifecycle_col: str = "lifecycle_month",
) -> "tuple[pd.DataFrame, pd.Series]":
    """
    Builds a cohort × lifecycle_month matrix with forward-smoothed values.

    Smoothing (forward, 3 periods):
        smooth(C, Mn) = mean(raw(C,Mn), raw(C,Mn+1), raw(C,Mn+2))
        using only available months (min_periods=1, max 3).

    Returns:
        smooth_df : DataFrame — cohort_month (index) × lifecycle_month (int cols).
                    Values = smoothed value_col; NaN where no data.
        weights   : Series — cohort_month → Σ raw(M1..M12) for weighted average.
    """
    if df.empty:
        return pd.DataFrame(), pd.Series(dtype=float)

    tmp = df.copy()
    tmp["cohort_month"] = pd.to_datetime(tmp["cohort_month"])
    tmp[lifecycle_col] = pd.to_numeric(tmp[lifecycle_col], errors="coerce")
    tmp = tmp.dropna(subset=["cohort_month", lifecycle_col, value_col])

    # Raw aggregate per (cohort_month, lifecycle_month)
    agg = (
        tmp.groupby(["cohort_month", lifecycle_col])[value_col]
        .sum()
        .unstack(lifecycle_col)          # NaN for missing (cohort, month) pairs
    )
    agg.columns = agg.columns.astype(int)
    sorted_cols = sorted(agg.columns.tolist())
    agg = agg.reindex(columns=sorted_cols)

    # Weights: Σ raw(M1..M12) per cohort — used for weighted average
    w_cols = [c for c in sorted_cols if 1 <= c <= 12]
    weights = agg[w_cols].sum(axis=1, skipna=True)

    # Forward 3-period smooth: smooth[col_i] = mean(raw[col_i..col_i+2])
    # pandas mean(axis=1) ignores NaN → uses 1, 2, or 3 months as available
    smooth = pd.DataFrame(index=agg.index, columns=sorted_cols, dtype=float)
    for i, col in enumerate(sorted_cols):
        window = agg.iloc[:, i: i + 3]
        smooth[col] = window.mean(axis=1)

    return smooth, weights


# ── Heatmap styles ────────────────────────────────────────────────────────────

def quartile_styles(pivot_df: pd.DataFrame, data_cols: list[str]) -> list[dict]:
    """
    Genera style_data_conditional con 4 bandas de cuartiles (escala lilac→primary).
    Los valores 0 / NaN no reciben color.
    """
    if pivot_df.empty or not data_cols:
        return []

    all_vals = pivot_df[data_cols].values.flatten()
    all_vals = all_vals[~pd.isna(all_vals) & (all_vals > 0)]
    if len(all_vals) < 4:
        return []

    q1 = float(np.percentile(all_vals, 25))
    q2 = float(np.percentile(all_vals, 50))
    q3 = float(np.percentile(all_vals, 75))

    # Guard: si los cuartiles colapsan, usar un único color
    if q1 == q3:
        return [
            {
                "if": {"filter_query": f"{{{col}}} > 0", "column_id": col},
                "backgroundColor": "#9684E1",
                "color": "#FFFFFF",
            }
            for col in data_cols
        ]

    styles = []
    for col in data_cols:
        styles += [
            {
                "if": {
                    "filter_query": f"{{{col}}} > 0 && {{{col}}} <= {q1}",
                    "column_id": col,
                },
                "backgroundColor": "#F0EDFC",
                "color": "#1A1659",
            },
            {
                "if": {
                    "filter_query": f"{{{col}}} > {q1} && {{{col}}} <= {q2}",
                    "column_id": col,
                },
                "backgroundColor": "#D4C9F5",
                "color": "#1A1659",
            },
            {
                "if": {
                    "filter_query": f"{{{col}}} > {q2} && {{{col}}} <= {q3}",
                    "column_id": col,
                },
                "backgroundColor": "#9684E1",
                "color": "#FFFFFF",
            },
            {
                "if": {
                    "filter_query": f"{{{col}}} > {q3}",
                    "column_id": col,
                },
                "backgroundColor": "#4827BE",
                "color": "#FFFFFF",
            },
        ]
    return styles
