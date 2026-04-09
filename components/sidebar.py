"""
Sidebar fijo de 240px — idéntico en estructura al SG&A Control.

Zonas:
  1. Header oscuro (#1A1659) con logo Melonn
  2. Nav items: Inputs / NOR·NRR / NDR·ODR / NNR·NNO
  3. Separador
  4. Panel de filtros globales

IDs de los filtros (usados por los callbacks):
  filter-pais          RadioItems   COL | MEX | CONSOLIDADO
  filter-segmentos     Checklist    Starter | Plus | Top | Enterprise | Tiny
  filter-churn         RadioItems   incluir | excluir
  filter-order-type    RadioItems   ambos | D2C | B2B
  filter-outliers      RadioItems   no_remover | remover
  filter-corte-base    Input text   YYYY-MM-DD  (default 2024-12-01)
  filter-fx-cop        Input number default 3800
  filter-fx-mxn        Input number default 17.5
  filter-estacionalidad Input number default 1.0
"""
from dash import dcc, html

LOGO_URL = "https://i.postimg.cc/bNP45qQ2/MELONN-LOGO-Oscuro.png"

_NAV_ITEMS = [
    {"label": "Inputs",     "icon": "▦",  "href": "/",     "id": "nav-inputs"},
    {"label": "NOR / NRR",  "icon": "↗",  "href": "/nor",  "id": "nav-nor"},
    {"label": "NDR / ODR",  "icon": "◈",  "href": "/ndr",  "id": "nav-ndr"},
    {"label": "NNR / NNO",  "icon": "★",  "href": "/nnr",  "id": "nav-nnr"},
]


def _filter_label(text: str) -> html.P:
    return html.P(text, className="filter-section-label")


def sidebar() -> html.Div:
    nav_links = [
        dcc.Link(
            [
                html.Span(item["icon"], className="nav-icon"),
                html.Span(item["label"], className="nav-label"),
            ],
            href=item["href"],
            id=item["id"],
            className="nav-item",
            refresh=False,
        )
        for item in _NAV_ITEMS
    ]

    filters = html.Div(
        [
            # ── País ─────────────────────────────────────────────────────────
            _filter_label("PAÍS"),
            dcc.RadioItems(
                id="filter-pais",
                options=[
                    {"label": "Consolidado", "value": "CONSOLIDADO"},
                    {"label": "Colombia",    "value": "COL"},
                    {"label": "México",      "value": "MEX"},
                ],
                value="CONSOLIDADO",
                className="filter-radio",
                labelClassName="filter-radio-label",
            ),

            html.Hr(className="filter-hr"),

            # ── Segmentos ─────────────────────────────────────────────────────
            _filter_label("SEGMENTOS"),
            dcc.Checklist(
                id="filter-segmentos",
                options=[
                    {"label": "Starter",    "value": "Starter"},
                    {"label": "Plus",       "value": "Plus"},
                    {"label": "Top",        "value": "Top"},
                    {"label": "Enterprise", "value": "Enterprise"},
                    {"label": "Tiny",       "value": "Tiny"},
                ],
                value=["Starter", "Plus", "Top", "Enterprise"],
                className="filter-checklist",
                labelClassName="filter-check-label",
            ),

            html.Hr(className="filter-hr"),

            # ── Churn ─────────────────────────────────────────────────────────
            _filter_label("CHURN"),
            dcc.RadioItems(
                id="filter-churn",
                options=[
                    {"label": "Incluir churn", "value": "incluir"},
                    {"label": "Excluir churn", "value": "excluir"},
                ],
                value="incluir",
                className="filter-radio",
                labelClassName="filter-radio-label",
            ),

            html.Hr(className="filter-hr"),

            # ── Tipo de orden ─────────────────────────────────────────────────
            _filter_label("TIPO DE ORDEN"),
            dcc.RadioItems(
                id="filter-order-type",
                options=[
                    {"label": "D2C + B2B", "value": "ambos"},
                    {"label": "Solo D2C",  "value": "D2C"},
                    {"label": "Solo B2B",  "value": "B2B"},
                ],
                value="ambos",
                className="filter-radio",
                labelClassName="filter-radio-label",
            ),

            html.Hr(className="filter-hr"),

            # ── Corte Base / Nuevos ────────────────────────────────────────────
            _filter_label("CORTE BASE (≤)"),
            html.Div(
                [
                    dcc.Input(
                        id="filter-corte-base",
                        type="text",
                        value="2024-12-01",
                        placeholder="AAAA-MM-DD",
                        debounce=True,
                        className="filter-input-text",
                    ),
                    html.Span("Base: sellers con entrada ≤ esta fecha", className="filter-hint"),
                ],
                className="filter-input-wrap",
            ),

            html.Hr(className="filter-hr"),

            # ── FX ────────────────────────────────────────────────────────────
            _filter_label("FX (moneda local → USD)"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("COP/USD", className="filter-fx-label"),
                            dcc.Input(
                                id="filter-fx-cop",
                                type="number",
                                value=3800,
                                min=1,
                                debounce=True,
                                className="filter-input-number",
                            ),
                        ],
                        className="filter-fx-row",
                    ),
                    html.Div(
                        [
                            html.Span("MXN/USD", className="filter-fx-label"),
                            dcc.Input(
                                id="filter-fx-mxn",
                                type="number",
                                value=17.5,
                                min=1,
                                debounce=True,
                                className="filter-input-number",
                            ),
                        ],
                        className="filter-fx-row",
                    ),
                ],
                className="filter-fx-block",
            ),

            html.Hr(className="filter-hr"),

            # ── Factor estacionalidad NNR ─────────────────────────────────────
            _filter_label("FACTOR ESTACIONALIDAD"),
            html.Div(
                [
                    dcc.Input(
                        id="filter-estacionalidad",
                        type="number",
                        value=1.0,
                        min=0.01,
                        step=0.01,
                        debounce=True,
                        className="filter-input-number",
                    ),
                    html.Span("Ajuste para NNR (×factor)", className="filter-hint"),
                ],
                className="filter-input-wrap",
            ),
        ],
        className="sidebar-filters",
    )

    return html.Div(
        [
            # ── Header logo ───────────────────────────────────────────────────
            html.Div(
                html.Img(src=LOGO_URL, className="sidebar-logo", alt="Melonn"),
                className="sidebar-header",
            ),

            # ── Nav ───────────────────────────────────────────────────────────
            html.Nav(nav_links, className="sidebar-nav"),

            html.Hr(className="sidebar-sep"),

            # ── Filtros ───────────────────────────────────────────────────────
            filters,
        ],
        className="sidebar",
        id="sidebar",
    )
