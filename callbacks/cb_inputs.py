"""
Vista: Inputs — Datos Reales

Tabla triangular cohorte × mes calendario, agrupada por año con secciones
html.Details desplegables. 2025 y 2026 abiertas por defecto; el resto cerradas.

Fase 3 — implementación completa con datos reales desde Redshift.
"""
import numpy as np
import pandas as pd
from dash import Input, Output, callback, dash_table, dcc, html
from dash.exceptions import PreventUpdate

from data.data_loader import load_orders, load_revenue
from data.transforms import (
    build_filters,
    calc_nnr,
    calc_nno,
    pivot_cohort,
    prepare_revenue,
    quartile_styles,
    revenue_display_unit,
)

# Años abiertos por defecto
_OPEN_YEARS = {2025, 2026}


# ── Layout ────────────────────────────────────────────────────────────────────

def inputs_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Inputs — Datos Reales", className="page-title"),
                            html.P(
                                "Revenue y órdenes por cohorte × mes calendario (Feb 2021 → presente)",
                                className="page-subtitle",
                            ),
                        ]
                    ),
                    html.Div(
                        dcc.RadioItems(
                            id="inputs-metric",
                            options=[
                                {"label": "Revenue", "value": "revenue"},
                                {"label": "Órdenes", "value": "orders"},
                            ],
                            value="revenue",
                            inline=True,
                            className="metric-radio",
                            labelClassName="metric-radio-label",
                            inputClassName="metric-radio-input",
                        ),
                        className="page-header-controls",
                    ),
                ],
                className="page-header",
            ),
            html.Div(id="inputs-kpis", className="kpi-strip"),
            html.Div(id="inputs-content", className="page-section"),
        ],
        className="page",
    )


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _kpi_card(title: str, value: str, subtitle: str, variant: str = "primary") -> html.Div:
    return html.Div(
        [
            html.P(title, className="kpi-title"),
            html.P(value, className=f"kpi-value kpi-value--{variant}"),
            html.P(subtitle, className="kpi-subtitle"),
        ],
        className="kpi-card",
    )


def _kpis_empty() -> list:
    return [
        _kpi_card("NNR Promedio",     "—", "Sin datos", "muted"),
        _kpi_card("NNO Promedio",     "—", "Sin datos", "muted"),
        _kpi_card("Cohortes activas", "—", "Sin datos", "muted"),
        _kpi_card("Sellers únicos",   "—", "Sin datos", "muted"),
    ]


def _error_content(msg: str) -> html.Div:
    return html.Div(
        html.Div(
            [
                html.Span("⚠", className="placeholder-icon"),
                html.P(msg, className="placeholder-text"),
            ],
            className="placeholder-box",
        )
    )


def _safe_records(df: pd.DataFrame) -> list[dict]:
    """
    Convierte DataFrame a list-of-dicts garantizando que NaN → None
    (JSON-serializable). Usa astype(object) para que pandas no revierta None a NaN.
    """
    return (
        df.astype(object)
        .where(pd.notnull(df), None)
        .to_dict("records")
    )


# ── Sección por año ───────────────────────────────────────────────────────────

def _year_section(
    year: int,
    pivot_df: pd.DataFrame,
    global_styles: list,
    fmt_spec: str,
) -> html.Details | None:
    """
    Crea una sección html.Details con DataTable para el año dado.
    fmt_spec: especificador de formato d3, e.g. ',.1f' o ',.0f'.
    """
    cols_year = [c for c in pivot_df.columns if c.startswith(str(year))]
    if not cols_year:
        return None

    # Los column IDs usan guión bajo para evitar que el parser de filter_query
    # interprete el guión como resta: "2021-02" → "2021_02"
    safe_id = {c: c.replace("-", "_") for c in cols_year}

    df_show = pivot_df[cols_year].reset_index().copy()
    df_show = df_show.rename(columns=safe_id)
    records = _safe_records(df_show)

    dt_columns = [{"name": "Cohorte", "id": "Cohorte", "type": "text"}] + [
        {
            "name": col,                   # display: "2021-02"
            "id":   safe_id[col],          # key:     "2021_02"
            "type": "numeric",
            "format": {"specifier": fmt_spec},
        }
        for col in cols_year
    ]

    # Reasignar column_id y filter_query de los estilos globales al safe_id
    year_styles = []
    for s in global_styles:
        orig = s.get("if", {}).get("column_id", "")
        if orig not in safe_id:
            continue
        sid = safe_id[orig]
        fq  = s["if"].get("filter_query", "").replace(f"{{{orig}}}", f"{{{sid}}}")
        year_styles.append({
            **s,
            "if": {**s["if"], "column_id": sid, "filter_query": fq},
        })

    table = dash_table.DataTable(
        columns=dt_columns,
        data=records,
        fixed_columns={"headers": True, "data": 1},
        style_table={"overflowX": "auto", "minWidth": "100%"},
        style_cell={
            "fontFamily": "'Poppins', sans-serif",
            "fontSize":   "12px",
            "padding":    "6px 10px",
            "textAlign":  "center",
            "minWidth":   "78px",
            "border":     "1px solid #EDE9F8",
            "whiteSpace": "nowrap",
            "overflow":   "hidden",
        },
        style_cell_conditional=[
            {
                "if": {"column_id": "Cohorte"},
                "textAlign":       "left",
                "fontWeight":      "700",
                "color":           "#1A1659",
                "minWidth":        "90px",
                "maxWidth":        "90px",
                "backgroundColor": "#FFFFFF",
                "borderRight":     "2px solid #D4C9F5",
            }
        ],
        style_header={
            "backgroundColor": "#1A1659",
            "color":           "#FFFFFF",
            "fontWeight":      "700",
            "fontSize":        "11px",
            "padding":         "8px 10px",
            "border":          "1px solid #1A1659",
            "whiteSpace":      "nowrap",
        },
        style_header_conditional=[
            {
                "if": {"column_id": "Cohorte"},
                "backgroundColor": "#1A1659",
            }
        ],
        style_data={"backgroundColor": "#FFFFFF", "color": "#1A1659"},
        style_data_conditional=year_styles,
        page_action="none",
        sort_action="none",
    )

    return html.Details(
        [html.Summary(str(year), className="year-summary"), table],
        open=(year in _OPEN_YEARS),
        className="year-section",
    )


# ── Callback ──────────────────────────────────────────────────────────────────

@callback(
    Output("inputs-content", "children"),
    Output("inputs-kpis",    "children"),
    Input("filter-pais",           "value"),
    Input("filter-segmentos",      "value"),
    Input("filter-churn",          "value"),
    Input("filter-order-type",     "value"),
    Input("filter-corte-base",     "value"),
    Input("filter-fx-cop",         "value"),
    Input("filter-fx-mxn",         "value"),
    Input("filter-estacionalidad", "value"),
    Input("inputs-metric",         "value"),
    Input("url",                   "pathname"),
    prevent_initial_call=False,
)
def update_inputs(
    pais, segmentos, churn, order_type, corte_base,
    fx_cop, fx_mxn, estacionalidad, metric, pathname,
):
    # Solo activo en /inputs (no en landing)
    if pathname != "/inputs":
        raise PreventUpdate

    # Defaults defensivos
    pais           = pais or "CONSOLIDADO"
    segmentos      = segmentos or ["Starter", "Plus", "Top", "Enterprise"]
    churn          = churn or "incluir"
    order_type     = order_type or "ambos"
    corte_base     = corte_base or "2024-12-01"
    fx_cop         = float(fx_cop or 3800)
    fx_mxn         = float(fx_mxn or 17.5)
    estacionalidad = float(estacionalidad or 1.0)

    filters = build_filters(pais, segmentos, churn, order_type)

    # Cargar ambos DataFrames (TTL cache 30 min)
    df_orders = load_orders(filters)
    df_rev    = load_revenue(filters)
    df_rev_p  = prepare_revenue(df_rev, pais, fx_cop, fx_mxn)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    nnr_val = calc_nnr(df_rev_p, corte_base, estacionalidad)
    nno_val = calc_nno(df_orders, corte_base)
    unit    = revenue_display_unit(pais)
    nnr_str = f"{nnr_val:,.1f}" if nnr_val is not None else "—"
    nno_str = f"{nno_val:,.0f}" if nno_val is not None else "—"

    # ── Pivot según métrica ───────────────────────────────────────────────────
    if metric == "revenue":
        if df_rev_p.empty:
            return _error_content("Sin datos de revenue para los filtros seleccionados."), _kpis_empty()
        pivot     = pivot_cohort(df_rev_p, "display_value", "revenue_month")
        fmt_spec  = ",.1f"
        n_sellers = int(df_rev["seller_id"].nunique()) if not df_rev.empty else 0
    else:
        if df_orders.empty:
            return _error_content("Sin datos de órdenes para los filtros seleccionados."), _kpis_empty()
        pivot     = pivot_cohort(df_orders, "order_count", "order_month")
        fmt_spec  = ",.0f"
        n_sellers = int(df_orders["seller_id"].nunique()) if not df_orders.empty else 0

    if pivot.empty:
        return _error_content("Sin datos para los filtros seleccionados."), _kpis_empty()

    # ── Construir secciones por año ───────────────────────────────────────────
    data_cols = list(pivot.columns)
    styles    = quartile_styles(pivot, data_cols)
    years     = sorted({int(c[:4]) for c in data_cols})
    sections  = [_year_section(y, pivot, styles, fmt_spec) for y in years]
    sections  = [s for s in sections if s is not None]

    unit_label_text = unit if metric == "revenue" else "órdenes"
    content = html.Div(
        [
            html.Div(
                html.Span(f"Unidad: {unit_label_text}", className="table-unit-label"),
                className="table-unit-row",
            ),
            *sections,
        ],
        className="cohort-sections",
    )

    kpis = [
        _kpi_card(
            "NNR Promedio", nnr_str,
            f"avg M2+M3 × {estacionalidad:.2f} ({unit})",
            "primary",
        ),
        _kpi_card("NNO Promedio",     nno_str,        "avg M2+M3 (órdenes)",           "primary"),
        _kpi_card("Cohortes activas", str(n_cohorts := len(pivot.index)), "Con al menos 1 mes de historia", "muted"),
        _kpi_card("Sellers únicos",   str(n_sellers), "Según filtros aplicados",        "muted"),
    ]

    return content, kpis
