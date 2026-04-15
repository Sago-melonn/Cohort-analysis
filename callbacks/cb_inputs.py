"""
Vista: Inputs — Datos Reales

Tabla por año calendario con dos niveles:
  Nivel 1 (siempre visible) : fila resumen por cohorte-año + fila Total
  Nivel 2 (desplegable)     : click en "Cohorte 2024" → filas de cohorte-mes inline

Filtros de página: metric, pais, moneda, fx-cop, fx-mxn, order-type.
"""
import concurrent.futures
from datetime import date
import numpy as np
import pandas as pd
from dash import Input, Output, callback, html
from dash.exceptions import PreventUpdate

from components.page_filters import inputs_filters
from data.data_loader import load_orders, load_revenue
from data.transforms import (
    build_filters,
    calc_nnr,
    calc_nno,
    pivot_cohort,
    pivot_cohort_by_year,
    prepare_revenue,
    revenue_display_unit,
)

_OPEN_YEARS = {date.today().year}
_CORTE_BASE = "2024-12-01"


# ── Layout ────────────────────────────────────────────────────────────────────

def inputs_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Inputs — Datos Reales", className="page-title"),
                    html.P(
                        "Revenue y órdenes por cohorte × mes calendario (Feb 2021 → presente)",
                        className="page-subtitle",
                    ),
                ],
                className="page-header",
            ),
            inputs_filters(),
            html.Div(id="inputs-kpis",    className="kpi-strip"),
            html.Div(id="inputs-content", className="page-section"),
        ],
        className="page",
    )


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _kpi_card(title, value, subtitle, variant="primary", tooltip=None):
    kwargs = {"className": "kpi-card"}
    if tooltip:
        kwargs["title"] = tooltip
    return html.Div(
        [
            html.P(title,    className="kpi-title"),
            html.P(value,    className=f"kpi-value kpi-value--{variant}"),
            html.P(subtitle, className="kpi-subtitle"),
        ],
        **kwargs,
    )


def _kpis_empty():
    return [
        _kpi_card("NNR Promedio",     "—", "Sin datos", "muted"),
        _kpi_card("NNO Promedio",     "—", "Sin datos", "muted"),
        _kpi_card("Sellers activos",  "—", "Sin datos", "muted"),
    ]


def _count_active_sellers(df_orders: pd.DataFrame) -> int:
    """Sellers con al menos 1 orden en el último mes del dataset y sin churn."""
    if df_orders.empty:
        return 0
    last_month = df_orders["order_month"].max()
    active = df_orders[
        (df_orders["order_month"] == last_month) &
        (df_orders["churn_flag"] == 0)
    ]
    return int(active["seller_id"].nunique())


def _error_content(msg):
    return html.Div(
        html.Div(
            [html.Span("⚠", className="placeholder-icon"),
             html.P(msg, className="placeholder-text")],
            className="placeholder-box",
        )
    )


# ── Helpers de tabla custom ───────────────────────────────────────────────────

def _cell_style(val, q1: float, q2: float, q3: float) -> dict:
    """Devuelve inline style (bg + color) según cuartil del valor."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return {}
    if pd.isna(v) or v <= 0:
        return {}
    if v <= q1:
        return {"backgroundColor": "#F0EDFC", "color": "#1A1659"}
    if v <= q2:
        return {"backgroundColor": "#D4C9F5", "color": "#1A1659"}
    if v <= q3:
        return {"backgroundColor": "#9684E1", "color": "#FFFFFF"}
    return {"backgroundColor": "#4827BE", "color": "#FFFFFF"}


def _fmt(val, fmt_spec: str) -> str:
    """Formatea un número con separador de miles."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    if pd.isna(v):
        return "—"
    return f"{v:,.1f}" if "1f" in fmt_spec else f"{v:,.0f}"


# ── Sección por año ───────────────────────────────────────────────────────────

def _year_section(year: int, pivot_yearly: pd.DataFrame,
                  pivot_monthly: pd.DataFrame, fmt_spec: str):
    """
    html.Details para un año calendario:
    - Fila resumen por cohorte-año (con ▶ para expandir) + fila Total.
    - Al expandir un cohorte-año aparecen sus cohorte-mes inline.
    """
    cols_year = [c for c in pivot_yearly.columns if c.startswith(str(year))]
    if not cols_year:
        return None

    # ── Cuartiles para heatmap (datos anuales del año) ─────────────
    all_vals = pivot_yearly[cols_year].values.flatten()
    all_vals = all_vals[~pd.isna(all_vals) & (all_vals > 0)]
    if len(all_vals) >= 4:
        q1, q2, q3 = (float(np.percentile(all_vals, p)) for p in (25, 50, 75))
        if q1 == q3:
            q1, q2 = q3 * 0.33, q3 * 0.66
    else:
        q1 = q2 = q3 = float("inf")  # sin coloreado si hay muy pocos valores

    # ── Header ────────────────────────────────────────────────────
    header = html.Div(
        [html.Span("Cohorte", className="ct-cell ct-cell-first ct-header-cell")]
        + [html.Span(c, className="ct-cell ct-header-cell") for c in cols_year],
        className="ct-row ct-header-row",
    )

    # ── Filas por cohorte-año ─────────────────────────────────────
    cohort_years = sorted(pivot_yearly.index.tolist())
    groups = []

    for cy in cohort_years:
        # Valores de la fila resumen
        yr_vals = [pivot_yearly.loc[cy, c] for c in cols_year]

        summary_content = html.Div(
            [html.Span(f"Cohorte {cy}", className="ct-cell ct-cell-first ct-year-label")]
            + [html.Span(_fmt(v, fmt_spec), className="ct-cell",
                         style=_cell_style(v, q1, q2, q3))
               for v in yr_vals],
            className="ct-row ct-year-row",
        )

        # Filas de detalle (cohorte-mes individuales de este año de cohorte)
        rows_cy    = [r for r in pivot_monthly.index if r.startswith(cy + "-")]
        cols_avail = [c for c in cols_year if c in pivot_monthly.columns]
        detail_rows = []

        if rows_cy and cols_avail:
            for cm in rows_cy:
                mo_vals = [
                    pivot_monthly.loc[cm, c] if c in cols_avail else None
                    for c in cols_year
                ]
                detail_rows.append(
                    html.Div(
                        [html.Span(cm, className="ct-cell ct-cell-first ct-month-label")]
                        + [html.Span(_fmt(v, fmt_spec), className="ct-cell ct-detail-cell",
                                     style=_cell_style(v, q1, q2, q3))
                           for v in mo_vals],
                        className="ct-row ct-detail-row",
                    )
                )

        if detail_rows:
            groups.append(
                html.Details(
                    [
                        html.Summary(summary_content, className="ct-summary"),
                        html.Div(detail_rows, className="ct-detail-body"),
                    ],
                    open=False,
                    className="ct-group",
                )
            )
        else:
            # Sin cohorte-mes disponibles → fila estática sin flecha
            groups.append(
                html.Div(summary_content, className="ct-group-nodrill")
            )

    # ── Total ─────────────────────────────────────────────────────
    total_vals = [float(pivot_yearly[c].sum(skipna=True)) for c in cols_year]
    total_row = html.Div(
        [html.Span("Total", className="ct-cell ct-cell-first ct-total-label")]
        + [html.Span(_fmt(v, fmt_spec), className="ct-cell ct-total-cell")
           for v in total_vals],
        className="ct-row ct-total-row",
    )

    return html.Details(
        [
            html.Summary(str(year), className="year-summary"),
            html.Div(
                html.Div([header, *groups, total_row], className="ct-table"),
                className="ct-wrap",
            ),
        ],
        open=(year in _OPEN_YEARS),
        className="year-section",
    )


# ── Callback principal ────────────────────────────────────────────────────────

@callback(
    Output("inputs-content", "children"),
    Output("inputs-kpis",    "children"),
    Input("inputs-metric",  "value"),
    Input("inputs-pais",    "value"),
    Input("inputs-moneda",  "value"),
    Input("inputs-fx-cop",  "value"),
    Input("inputs-fx-mxn",  "value"),
    Input("url",            "pathname"),
    prevent_initial_call=False,
)
def update_inputs(metric, pais, moneda, fx_cop, fx_mxn, pathname):
    if pathname != "/inputs":
        raise PreventUpdate

    pais   = pais   or "CONSOLIDADO"
    moneda = moneda or "local"
    fx_cop = float(fx_cop or 3800)
    fx_mxn = float(fx_mxn or 17.5)

    filters = build_filters(pais, None, None, None)   # order_type=None → siempre ambos

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fut_orders = ex.submit(load_orders,  filters)
        fut_rev    = ex.submit(load_revenue, filters)
        df_orders  = fut_orders.result()
        df_rev     = fut_rev.result()

    df_rev_p = prepare_revenue(df_rev, pais, moneda, fx_cop, fx_mxn)

    # ── KPIs ──────────────────────────────────────────────────────
    unit    = revenue_display_unit(pais, moneda)
    nnr_val = calc_nnr(df_rev_p, _CORTE_BASE, 1.0)
    nno_val = calc_nno(df_orders, _CORTE_BASE)
    nnr_str = f"{nnr_val:,.1f}" if nnr_val is not None else "—"
    nno_str = f"{nno_val:,.0f}" if nno_val is not None else "—"

    # ── Pivots: yearly (resumen) y monthly (drill-down) ────────────
    if metric == "revenue":
        if df_rev_p.empty:
            return _error_content("Sin datos de revenue para los filtros seleccionados."), _kpis_empty()
        pivot_yr = pivot_cohort_by_year(df_rev_p, "display_value", "revenue_month")
        pivot_mo = pivot_cohort(df_rev_p, "display_value", "revenue_month")
        fmt_spec = ",.0f"
    else:
        if df_orders.empty:
            return _error_content("Sin datos de órdenes para los filtros seleccionados."), _kpis_empty()
        pivot_yr = pivot_cohort_by_year(df_orders, "order_count", "order_month")
        pivot_mo = pivot_cohort(df_orders, "order_count", "order_month")
        fmt_spec = ",.0f"

    if pivot_yr.empty:
        return _error_content("Sin datos para los filtros seleccionados."), _kpis_empty()

    # ── Secciones por año calendario ──────────────────────────────
    years    = sorted({int(c[:4]) for c in pivot_yr.columns})
    sections = [
        s for s in (
            _year_section(y, pivot_yr, pivot_mo, fmt_spec) for y in years
        ) if s
    ]

    unit_label = unit if metric == "revenue" else "órdenes"
    content = html.Div(
        [
            html.Div(html.Span(f"Unidad: {unit_label}", className="table-unit-label"),
                     className="table-unit-row"),
            *sections,
        ],
        className="cohort-sections",
    )

    n_active = _count_active_sellers(df_orders)
    kpis = [
        _kpi_card(
            "NNR Promedio", nnr_str, unit, "primary",
            tooltip="avg(Revenue M2 + M3) de sellers nuevos (entrada > corte base)",
        ),
        _kpi_card(
            "NNO Promedio", nno_str, "órdenes", "primary",
            tooltip="avg(Órdenes M2 + M3) de sellers nuevos (entrada > corte base)",
        ),
        _kpi_card(
            "Sellers activos", str(n_active),
            "Con órdenes en el último mes y sin churn", "muted",
        ),
    ]
    return content, kpis
