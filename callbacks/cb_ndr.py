"""
Vista: NDR / ODR — Retención por Cohorte

Aplica a sellers con entrada ≥ Ene 2025 (post-corte Base).
ODR (órdenes) es la métrica preferida; NDR (revenue) como complemento.

Curva atemporal: M0 = 100% → Mn (cada cohorte en su propio eje de tiempo).

Fase 2 — scaffold: layout completo, callback stub con placeholder.
Fase 3 — implementar: suavizado → ODR/NDR por cohorte → heatmap + curva.

Fórmulas:
  ODR(cohorte, Mn) = Orders_smooth(cohorte, Mn) / Orders_smooth(cohorte, M0)
  NDR(cohorte, Mn) = Revenue_smooth(cohorte, Mn) / Revenue_smooth(cohorte, M0)
  M0 = lifecycle_month = 1 (mes de entrada)

Hitos clave: M13 y M25 — resaltados en verde #00C97A.
"""
from dash import Input, Output, callback, dcc, html


# ── Layout ───────────────────────────────────────────────────────────────────

def ndr_layout() -> html.Div:
    return html.Div(
        [
            # Cabecera
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("NDR / ODR — Retención por Cohorte", className="page-title"),
                            html.P(
                                "Curva atemporal de retención (M0=100%). "
                                "Sellers con entrada ≥ Ene 2025.",
                                className="page-subtitle",
                            ),
                        ]
                    ),
                    # Selector ODR / NDR
                    html.Div(
                        dcc.RadioItems(
                            id="ndr-metric",
                            options=[
                                {"label": "ODR — Órdenes (preferido)", "value": "orders"},
                                {"label": "NDR — Revenue",              "value": "revenue"},
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

            # Layout de dos columnas: heatmap (izq) + curva promedio (der)
            html.Div(
                [
                    # Heatmap principal
                    html.Div(
                        [
                            html.Div(
                                className="page-section-title-row",
                                children=[
                                    html.H3("Heatmap por Cohorte", className="section-title"),
                                    html.Span(
                                        "M13 y M25 resaltados en verde",
                                        className="section-badge badge--verde",
                                    ),
                                ],
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.P("Tabla heatmap NDR / ODR", className="placeholder-title"),
                                            html.P(
                                                "Filas: cohortes (nuevas primero) · "
                                                "Columnas: M0 → M24. M0 = 100%.",
                                                className="placeholder-text",
                                            ),
                                            html.P(
                                                "Colores: ≥100% verde · 80-99% verde suave · <80% lila.",
                                                className="placeholder-text",
                                            ),
                                            html.P("Implementación en Fase 3.", className="placeholder-hint"),
                                        ],
                                        className="placeholder-box",
                                    )
                                ],
                                id="ndr-table",
                            ),
                        ],
                        className="ndr-left card page-section",
                    ),

                    # Curva de retención promedio
                    html.Div(
                        [
                            html.H3("Curva de Retención Promedio", className="section-title"),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.P("Gráfico curva promedio", className="placeholder-title"),
                                            html.P(
                                                "Línea ponderada (principal) + línea simple. "
                                                "Marcadores en M13 y M25.",
                                                className="placeholder-hint",
                                            ),
                                        ],
                                        className="placeholder-box",
                                    )
                                ],
                                id="ndr-chart",
                            ),
                            # Promedios
                            html.Div(id="ndr-averages", className="ndr-averages"),
                        ],
                        className="ndr-right card page-section",
                    ),
                ],
                className="ndr-grid",
            ),
        ],
        className="page",
    )


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _kpi_row(m: int, simple: str, weighted: str) -> html.Div:
    return html.Div(
        [
            html.Span(f"M{m}", className="avg-month"),
            html.Span(simple,   className="avg-simple"),
            html.Span(weighted, className="avg-weighted"),
        ],
        className="avg-row",
    )


# ── Callback stub ─────────────────────────────────────────────────────────────

@callback(
    Output("ndr-table",    "children"),
    Output("ndr-chart",    "children"),
    Output("ndr-averages", "children"),
    Input("filter-pais",          "value"),
    Input("filter-segmentos",     "value"),
    Input("filter-churn",         "value"),
    Input("filter-order-type",    "value"),
    Input("filter-corte-base",    "value"),
    Input("ndr-metric",           "value"),
    Input("url",                  "pathname"),
    prevent_initial_call=False,
)
def update_ndr(pais, segmentos, churn, order_type, corte_base, metric, pathname):
    if pathname != "/ndr":
        raise Exception("Callback ignorado — página no activa")

    # TODO Fase 3:
    #   1. filters = build_filters(pais, segmentos, churn, order_type)
    #   2. df = load_orders(filters) si metric='orders' else load_revenue(filters)
    #   3. Filtrar sellers con cohort_month >= corte_base + 1 mes (sellers nuevos)
    #   4. Aplicar suavizado 3 períodos por seller × mes
    #   5. Pivot → cohorte × lifecycle_month; dividir por M0 → retención %
    #   6. Calcular avg simple y ponderado por lifecycle_month
    #   7. Renderizar heatmap con colores + curva Plotly

    table = html.Div(
        [html.P("Heatmap NDR / ODR", className="placeholder-title"),
         html.P(f"Métrica: {metric} · {pais} · {churn}", className="placeholder-text"),
         html.P("Implementación en Fase 3.", className="placeholder-hint")],
        className="placeholder-box",
    )

    chart = html.Div(
        [html.P("Curva de retención promedio", className="placeholder-title"),
         html.P("Implementación en Fase 3.", className="placeholder-hint")],
        className="placeholder-box",
    )

    averages = html.Div(
        [
            html.Div(
                [html.Span("Mes", className="avg-month avg-header"),
                 html.Span("Avg simple", className="avg-simple avg-header"),
                 html.Span("Avg ponderado", className="avg-weighted avg-header")],
                className="avg-row avg-header-row",
            ),
            _kpi_row(1, "—", "—"),
            _kpi_row(13, "—", "—"),
            _kpi_row(25, "—", "—"),
        ],
        className="ndr-averages-table",
    )

    return table, chart, averages
