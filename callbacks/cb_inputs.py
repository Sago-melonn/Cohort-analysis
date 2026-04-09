"""
Vista: Inputs — Datos Reales

Muestra la tabla triangular de cohortes × meses calendario con datos brutos
de revenue u órdenes antes de aplicar suavizado o cálculos de retención.

Fase 2 — scaffold: layout completo, callback stub con placeholder.
Fase 3 — implementar: llamar data_loader, pivot y renderizar DataTable/heatmap.
"""
from dash import Input, Output, State, callback, dcc, html


# ── Layout ───────────────────────────────────────────────────────────────────

def inputs_layout() -> html.Div:
    return html.Div(
        [
            # Cabecera de página
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
                    # Selector de métrica
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

            # KPI strip: NNR y NNO del período seleccionado
            html.Div(
                [
                    _kpi_card("NNR Promedio", "—", "Revenue nuevo por cohorte (avg M2+M3)", "primary"),
                    _kpi_card("NNO Promedio", "—", "Órdenes nuevas por cohorte (avg M2+M3)", "primary"),
                    _kpi_card("Cohortes activas", "—", "Con al menos 1 mes de historia", "muted"),
                    _kpi_card("Sellers totales", "—", "Según filtros aplicados", "muted"),
                ],
                className="kpi-strip",
                id="inputs-kpis",
            ),

            # Tabla principal (placeholder hasta Fase 3)
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("▦", className="placeholder-icon"),
                            html.P("Tabla de cohortes", className="placeholder-title"),
                            html.P(
                                "Conecta los filtros del sidebar y la tabla se cargará aquí.",
                                className="placeholder-text",
                            ),
                            html.P(
                                "Fase 3: pivot seller×mes → heatmap con scroll sincronizado.",
                                className="placeholder-hint",
                            ),
                        ],
                        className="placeholder-box",
                    )
                ],
                id="inputs-content",
                className="page-section",
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
    Output("inputs-content", "children"),
    Output("inputs-kpis",    "children"),
    Input("filter-pais",          "value"),
    Input("filter-segmentos",     "value"),
    Input("filter-churn",         "value"),
    Input("filter-order-type",    "value"),
    Input("filter-corte-base",    "value"),
    Input("filter-fx-cop",        "value"),
    Input("filter-fx-mxn",        "value"),
    Input("filter-estacionalidad","value"),
    Input("inputs-metric",        "value"),
    Input("url",                  "pathname"),
    prevent_initial_call=False,
)
def update_inputs(pais, segmentos, churn, order_type, corte_base,
                  fx_cop, fx_mxn, estacionalidad, metric, pathname):
    if pathname not in ("/", "/inputs"):
        raise Exception("Callback ignorado — página no activa")

    # TODO Fase 3: construir filters dict, llamar load_orders / load_revenue,
    #              hacer pivot cohort_month × calendar_month, renderizar heatmap.

    content = html.Div(
        [
            html.Div(
                [
                    html.Span("▦", className="placeholder-icon"),
                    html.P("Tabla de cohortes", className="placeholder-title"),
                    html.P(
                        f"País: {pais} · Segmentos: {', '.join(segmentos or [])} · "
                        f"Churn: {churn} · Métrica: {metric}",
                        className="placeholder-text",
                    ),
                    html.P("Implementación completa en Fase 3.", className="placeholder-hint"),
                ],
                className="placeholder-box",
            )
        ]
    )

    kpis = [
        _kpi_card("NNR Promedio",    "—", "avg M2+M3 revenue × factor estacionalidad", "primary"),
        _kpi_card("NNO Promedio",    "—", "avg M2+M3 órdenes", "primary"),
        _kpi_card("Cohortes activas","—", "Con ≥ 1 mes de historia", "muted"),
        _kpi_card("Sellers totales", "—", "Según filtros aplicados", "muted"),
    ]

    return content, kpis
