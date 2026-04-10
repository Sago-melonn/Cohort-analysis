from datetime import date, timedelta

from dash import html, dcc

from data.data_loader import load_last_order_month

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
LOGO_URL = "https://i.postimg.cc/bNP45qQ2/MELONN-LOGO-Oscuro.png"

MESES_CORTO = {
    1: "Ene",  2: "Feb",  3: "Mar",  4: "Abr",
    5: "May",  6: "Jun",  7: "Jul",  8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _prev_month(d: date) -> date:
    return d.replace(day=1) - timedelta(days=1)


def _status_card_consolidado(max_date: date | None) -> html.Div:
    header = html.Div(
        [
            html.Span("🌎", className="status-globe"),
            html.Span("Consolidado", className="status-country-name"),
        ],
        className="status-header",
    )

    if not max_date:
        badges = html.Div(
            html.Span("Sin datos", className="status-pill no-data"),
            className="status-badges-col",
        )
    else:
        prev = _prev_month(max_date)
        badges = html.Div(
            [
                html.Span(
                    f"{MESES_CORTO[prev.month]} {prev.year}  Cerrado",
                    className="status-pill closed",
                ),
                html.Span(
                    f"{MESES_CORTO[max_date.month]} {max_date.year}  Parcial",
                    className="status-pill partial",
                ),
            ],
            className="status-badges-col",
        )

    return html.Div([header, badges], className="status-card")


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def layout() -> html.Div:
    try:
        max_date = load_last_order_month()
    except Exception:
        max_date = None

    return html.Div(
        html.Div(
            [
                html.Div(
                    html.Img(src=LOGO_URL, alt="Melonn"),
                    className="logo-container",
                ),
                html.H1("Cohort Analysis", className="landing-title"),
                html.P("Análisis de Retención de Sellers", className="landing-subtitle"),
                html.Div(
                    [_status_card_consolidado(max_date)],
                    className="status-cards-row",
                ),
                dcc.Link(
                    html.Button("Entrar al Dashboard", className="btn-primary"),
                    href="/inputs",
                    style={"textDecoration": "none"},
                ),
            ],
            className="landing-hero",
        ),
        className="landing-wrap",
    )
