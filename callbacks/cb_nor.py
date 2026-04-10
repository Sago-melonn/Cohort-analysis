"""
Vista: NOR / NRR — Retención Base

Aplica a sellers con entrada ≤ corte Base (default Dic 2024).
NOR (órdenes suavizadas) es la métrica preferida; NRR (revenue) como complemento.

Fase 2 — scaffold: layout completo, callback stub con placeholder.
Fase 3 — implementar: suavizado 3 períodos → ratio NOR/NRR mensual → línea chart.

Fórmula NOR:
  NOR(mes_t) = Σ Orders_smooth(cohortes edad > 12m, en mes_t)
             / Σ Orders_smooth(cohortes edad > 12m, en mes_t − 12)
"""
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate


# ── Layout ───────────────────────────────────────────────────────────────────

def nor_layout() -> html.Div:
    return html.Div(
        [
            # Cabecera
            html.Div(
                [
                    html.H2("NOR / NRR — Retención Base", className="page-title"),
                    html.P(
                        "Retención YoY de la base de sellers maduros (entrada ≤ corte Base).",
                        className="page-subtitle",
                    ),
                ],
                className="page-header",
            ),

            # KPIs
            html.Div(
                [
                    _kpi_card("NOR LTM",         "—", "Últimos 12 meses (promedio)", "verde"),
                    _kpi_card("NRR LTM",          "—", "Últimos 12 meses (promedio)", "verde"),
                    _kpi_card("NOR último mes",   "—", "Ratio más reciente", "primary"),
                    _kpi_card("Tendencia NOR",    "—", "vs trimestre anterior", "muted"),
                ],
                className="kpi-strip",
                id="nor-kpis",
            ),

            # Gráfico de línea NOR / NRR mensual
            html.Div(
                [
                    html.Div(
                        [html.P("Gráfico NOR / NRR mensual", className="placeholder-title"),
                         html.P(
                             "Fase 3: línea NOR + línea NRR + banda de referencia 100%.",
                             className="placeholder-hint",
                         )],
                        className="placeholder-box",
                    )
                ],
                id="nor-chart-container",
                className="page-section card",
            ),

            # Tabla de datos suavizados
            html.Div(
                [
                    html.Div(
                        [
                            html.P("Tabla suavizada (3 períodos)", className="placeholder-title"),
                            html.P(
                                "Misma estructura que Inputs pero con smooth aplicado. "
                                "Solo cohortes con ≥ 13 meses de historia.",
                                className="placeholder-hint",
                            ),
                        ],
                        className="placeholder-box",
                    )
                ],
                id="nor-table",
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
    Output("nor-kpis",           "children"),
    Output("nor-chart-container","children"),
    Output("nor-table",          "children"),
    Input("filter-pais",          "value"),
    Input("filter-segmentos",     "value"),
    Input("filter-churn",         "value"),
    Input("filter-order-type",    "value"),
    Input("filter-corte-base",    "value"),
    Input("url",                  "pathname"),
    prevent_initial_call=False,
)
def update_nor(pais, segmentos, churn, order_type, corte_base, pathname):
    if pathname != "/nor":
        raise PreventUpdate

    # TODO Fase 3:
    #   1. filters = build_filters(pais, segmentos, churn, order_type)
    #   2. df_orders = load_orders(filters)
    #   3. Filtrar cohortes con entrada ≤ corte_base
    #   4. Aplicar suavizado 3 períodos por cohorte × mes
    #   5. Para cada mes_t: num = Σ smooth(cohortes edad>12m, mes_t)
    #                       den = Σ smooth(cohortes edad>12m, mes_t-12)
    #   6. Calcular NOR = num/den; idem para NRR con revenue
    #   7. Renderizar línea chart + KPIs + tabla suavizada

    kpis = [
        _kpi_card("NOR LTM",        "—", "Últimos 12 meses", "verde"),
        _kpi_card("NRR LTM",        "—", "Últimos 12 meses", "verde"),
        _kpi_card("NOR último mes", "—", "Ratio más reciente", "primary"),
        _kpi_card("Tendencia NOR",  "—", "vs trimestre anterior", "muted"),
    ]

    chart = html.Div(
        [html.P("Gráfico NOR / NRR mensual", className="placeholder-title"),
         html.P(f"Filtros: {pais} · {churn} · corte ≤ {corte_base}", className="placeholder-text"),
         html.P("Implementación en Fase 3.", className="placeholder-hint")],
        className="placeholder-box",
    )

    table = html.Div(
        [html.P("Tabla de datos suavizados", className="placeholder-title"),
         html.P("Implementación en Fase 3.", className="placeholder-hint")],
        className="placeholder-box",
    )

    return kpis, chart, table
