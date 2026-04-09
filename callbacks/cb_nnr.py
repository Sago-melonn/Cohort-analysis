"""
Vista: NNR / NNO — Revenue y Órdenes Nuevas

Mide el "tamaño" de los sellers que entran cada mes.
Insumo directo del modelo financiero.

NNR = avg(Rev_smooth_M2, Rev_smooth_M3) × factor_estacionalidad
NNO = avg(Orders_M2, Orders_M3)
M0 = mes de entrada; M2/M3 = primeros meses completos estables.

Fase 2 — scaffold: layout completo, callback stub con placeholder.
Fase 3 — implementar: calcular NNR/NNO por cohorte → bar chart con desglose segmento.
"""
from dash import Input, Output, callback, dcc, html


# ── Layout ───────────────────────────────────────────────────────────────────

def nnr_layout() -> html.Div:
    return html.Div(
        [
            # Cabecera
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("NNR / NNO — Revenue y Órdenes Nuevas", className="page-title"),
                            html.P(
                                "Tamaño de cada cohorte nueva. "
                                "Insumo directo del modelo financiero.",
                                className="page-subtitle",
                            ),
                        ]
                    ),
                    # Selector NNR / NNO
                    html.Div(
                        dcc.RadioItems(
                            id="nnr-metric",
                            options=[
                                {"label": "NNO — Órdenes (preferido)", "value": "orders"},
                                {"label": "NNR — Revenue",              "value": "revenue"},
                            ],
                            value="orders",
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

            # KPIs trimestre actual vs anterior
            html.Div(
                [
                    _kpi_card("NNR Q actual",    "—", "Revenue nuevos este trimestre", "primary"),
                    _kpi_card("NNR Q anterior",  "—", "Revenue nuevos trimestre anterior", "muted"),
                    _kpi_card("NNO Q actual",    "—", "Órdenes nuevos este trimestre", "primary"),
                    _kpi_card("Variación YoY",   "—", "% vs mismo trimestre año anterior", "verde"),
                ],
                className="kpi-strip",
                id="nnr-kpis",
            ),

            # Gráfico de barras por cohorte
            html.Div(
                [
                    html.H3("NNR / NNO por Cohorte de Entrada", className="section-title"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P("Gráfico de barras NNR / NNO", className="placeholder-title"),
                                    html.P(
                                        "Una barra por mes de entrada. "
                                        "Coloreado por segmento (stack).",
                                        className="placeholder-text",
                                    ),
                                    html.P("Implementación en Fase 3.", className="placeholder-hint"),
                                ],
                                className="placeholder-box",
                            )
                        ],
                        id="nnr-chart",
                    ),
                ],
                className="page-section card",
            ),

            # Tabla resumen trimestral
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


# ── Callback stub ─────────────────────────────────────────────────────────────

@callback(
    Output("nnr-kpis",  "children"),
    Output("nnr-chart", "children"),
    Output("nnr-table", "children"),
    Input("filter-pais",           "value"),
    Input("filter-segmentos",      "value"),
    Input("filter-churn",          "value"),
    Input("filter-order-type",     "value"),
    Input("filter-corte-base",     "value"),
    Input("filter-fx-cop",         "value"),
    Input("filter-fx-mxn",         "value"),
    Input("filter-estacionalidad", "value"),
    Input("nnr-metric",            "value"),
    Input("url",                   "pathname"),
    prevent_initial_call=False,
)
def update_nnr(pais, segmentos, churn, order_type, corte_base,
               fx_cop, fx_mxn, estacionalidad, metric, pathname):
    if pathname != "/nnr":
        raise Exception("Callback ignorado — página no activa")

    # TODO Fase 3:
    #   1. filters = build_filters(pais, segmentos, churn, order_type)
    #   2. df = load_orders(filters) si metric='orders' else load_revenue(filters)
    #   3. Filtrar lifecycle_month IN (2, 3) → avg por cohort_month → NNO / NNR
    #   4. NNR *= factor_estacionalidad; convertir a USD con fx_cop / fx_mxn
    #   5. Agrupar por trimestre para KPIs y comparación YoY
    #   6. Renderizar bar chart con desglose por segmento + tabla trimestral

    kpis = [
        _kpi_card("NNR Q actual",   "—", f"Factor est. ×{estacionalidad}", "primary"),
        _kpi_card("NNR Q anterior", "—", "Revenue nuevos Q-1", "muted"),
        _kpi_card("NNO Q actual",   "—", "Órdenes nuevos Q actual", "primary"),
        _kpi_card("Variación YoY",  "—", "vs mismo trimestre año anterior", "verde"),
    ]

    chart = html.Div(
        [html.P("Gráfico barras NNR / NNO", className="placeholder-title"),
         html.P(f"Métrica: {metric} · {pais} · FX COP={fx_cop} MXN={fx_mxn}", className="placeholder-text"),
         html.P("Implementación en Fase 3.", className="placeholder-hint")],
        className="placeholder-box",
    )

    table = html.Div(
        [html.P("Tabla resumen trimestral", className="placeholder-title"),
         html.P("Implementación en Fase 3.", className="placeholder-hint")],
        className="placeholder-box",
    )

    return kpis, chart, table
