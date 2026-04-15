"""
Vista: NNR / NNO — Revenue y Órdenes Nuevas

Tamaño de los sellers que entran cada mes.
Insumo directo del modelo financiero.

Fase 2 — scaffold: layout + filtros + callback stub.
"""
from dash import Input, Output, callback, html
from dash.exceptions import PreventUpdate

from components.page_filters import nnr_filters


# ── Layout ────────────────────────────────────────────────────────────────────

def nnr_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H2("NNR / NNO — Revenue y Órdenes Nuevas", className="page-title"),
                    html.P(
                        "Tamaño de cada cohorte nueva. "
                        "Insumo directo del modelo financiero.",
                        className="page-subtitle",
                    ),
                ],
                className="page-header",
            ),
            nnr_filters(),
            html.Div(id="nnr-kpis",  className="kpi-strip"),
            html.Div(
                [
                    html.H3("NNR / NNO por Cohorte de Entrada", className="section-title"),
                    html.Div(id="nnr-chart"),
                ],
                className="page-section card",
            ),
            html.Div(
                [
                    html.H3("Resumen Trimestral", className="section-title"),
                    html.Div(id="nnr-table", className="page-section"),
                ],
                className="page-section card",
            ),
        ],
        className="page",
    )


# ── Helper UI ─────────────────────────────────────────────────────────────────

def _kpi_card(title, value, subtitle, variant="primary"):
    return html.Div(
        [
            html.P(title,    className="kpi-title"),
            html.P(value,    className=f"kpi-value kpi-value--{variant}"),
            html.P(subtitle, className="kpi-subtitle"),
        ],
        className="kpi-card",
    )


# ── Callback principal (stub) ─────────────────────────────────────────────────

@callback(
    Output("nnr-kpis",  "children"),
    Output("nnr-chart", "children"),
    Output("nnr-table", "children"),
    Input("nnr-metric", "value"),
    Input("nnr-pais",   "value"),
    Input("nnr-fx-cop", "value"),
    Input("nnr-fx-mxn", "value"),
    Input("url",        "pathname"),
    prevent_initial_call=False,
)
def update_nnr(metric, pais, fx_cop, fx_mxn, pathname):
    if pathname != "/nnr":
        raise PreventUpdate

    kpis = [
        _kpi_card("NNR Q actual",   "—", "Revenue nuevos este trimestre",          "primary"),
        _kpi_card("NNR Q anterior", "—", "Revenue nuevos trimestre anterior",       "muted"),
        _kpi_card("NNO Q actual",   "—", "Órdenes nuevos este trimestre",           "primary"),
        _kpi_card("Variación YoY",  "—", "% vs mismo trimestre año anterior",       "verde"),
    ]
    chart = html.Div(
        [html.P("Gráfico barras NNR / NNO", className="placeholder-title"),
         html.P("Implementación pendiente.", className="placeholder-hint")],
        className="placeholder-box",
    )
    table = html.Div(
        [html.P("Tabla resumen trimestral", className="placeholder-title"),
         html.P("Implementación pendiente.", className="placeholder-hint")],
        className="placeholder-box",
    )
    return kpis, chart, table
