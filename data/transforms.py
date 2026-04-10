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

def revenue_display_unit(pais: str) -> str:
    """Etiqueta de la unidad de display según el país."""
    if pais == "COL":
        return "MM COP"
    if pais == "MEX":
        return "MM MXN"
    return "K USD"


def prepare_revenue(df_rev: pd.DataFrame, pais: str, fx_cop: float, fx_mxn: float) -> pd.DataFrame:
    """
    Agrega columna 'display_value' al DataFrame de revenue según el país:
      COL         → MM COP  (÷ 1_000_000)
      MEX         → MM MXN  (÷ 1_000_000)
      CONSOLIDADO → K USD   (÷ FX_local ÷ 1_000, sumando ambos países)
    Retorna una copia; no modifica el original.
    """
    if df_rev.empty:
        df = df_rev.copy()
        df["display_value"] = pd.Series(dtype=float)
        return df

    df = df_rev.copy()
    fx_cop = float(fx_cop or 3800)
    fx_mxn = float(fx_mxn or 17.5)

    if pais == "COL":
        df["display_value"] = df["total_revenue"] / 1_000_000
    elif pais == "MEX":
        df["display_value"] = df["total_revenue"] / 1_000_000
    else:  # CONSOLIDADO
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
