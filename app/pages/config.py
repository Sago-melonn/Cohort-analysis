"""
Página de Configuración — Ajuste de Cohortes por Seller.

Permite reasignar la cohorte de inicio de sellers que entraron con un
piloto pequeño antes de operar a plena capacidad. El ajuste afecta
todas las páginas del tablero (NDR/ODR, NOR/NRR, Inputs).
"""
from dash import dcc, html


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [html.H2("Configuración — Ajuste de Cohortes", className="page-title")],
                className="page-header",
            ),

            # ── Panel de entrada ──────────────────────────────────────────────
            html.Div([
                html.P(
                    "Algunos sellers inician con un piloto pequeño antes de operar a plena "
                    "capacidad. Cambiar su cohorte de inicio corrige el NDR/ODR. "
                    "Los ajustes se aplican de forma transversal a todas las páginas.",
                    style={"color": "#555", "fontSize": "13px", "margin": "0 0 16px"},
                ),

                html.Div([
                    # Seller dropdown
                    html.Div([
                        html.P("Seller", className="fb-label"),
                        dcc.Dropdown(
                            id="cfg-seller-dd",
                            options=[],
                            placeholder="Buscar seller...",
                            searchable=True,
                            clearable=True,
                            className="fb-select",
                            style={"minWidth": "280px"},
                        ),
                    ], className="fb-group"),

                    # Cohorte original (read-only, se rellena al seleccionar seller)
                    html.Div([
                        html.P("Cohorte original", className="fb-label"),
                        html.Div(
                            "—",
                            id="cfg-original-cohort",
                            style={
                                "minWidth": "110px", "padding": "5px 10px",
                                "border": "1px solid #D0CAEA", "borderRadius": "6px",
                                "fontSize": "13px", "color": "#888", "background": "#F9F8FE",
                                "fontWeight": "500",
                            },
                        ),
                    ], className="fb-group"),

                    # Nueva cohorte
                    html.Div([
                        html.P("Nueva cohorte", className="fb-label"),
                        dcc.DatePickerSingle(
                            id="cfg-new-cohort",
                            placeholder="MMM YYYY",
                            display_format="MMM YYYY",
                            first_day_of_week=1,
                            clearable=True,
                            className="fb-date-picker",
                        ),
                    ], className="fb-group"),

                    # Botón agregar
                    html.Div([
                        html.P("\u00a0", className="fb-label"),   # spacer
                        html.Button(
                            "+ Agregar",
                            id="cfg-add-btn",
                            n_clicks=0,
                            style={
                                "padding": "6px 16px", "fontSize": "13px", "fontWeight": "600",
                                "borderRadius": "6px", "border": "1.5px solid #4827BE",
                                "background": "#4827BE", "color": "#fff", "cursor": "pointer",
                            },
                        ),
                    ], className="fb-group"),
                ], className="filter-bar", style={"flexWrap": "wrap", "gap": "12px"}),

                # Mensaje de validación
                html.Div(id="cfg-msg", style={"marginTop": "8px", "fontSize": "12px"}),

            ], className="page-section card"),

            # ── Tabla de overrides activos ────────────────────────────────────
            html.Div(id="cfg-overrides-table", className="page-section card"),
        ],
        className="page",
    )
