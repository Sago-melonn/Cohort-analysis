"""
Sidebar fijo — solo navegación.
Los filtros se movieron a cada página.
"""
from dash import dcc, html

LOGO_URL = "https://i.postimg.cc/bNP45qQ2/MELONN-LOGO-Oscuro.png"

_NAV_ITEMS = [
    {"label": "Inputs",    "icon": "▦", "href": "/inputs", "id": "nav-inputs"},
    {"label": "NRR / NOR", "icon": "↗", "href": "/nor",    "id": "nav-nor"},
    {"label": "NDR / ODR", "icon": "◈", "href": "/ndr",    "id": "nav-ndr"},
    {"label": "NNR / NNO", "icon": "★", "href": "/nnr",    "id": "nav-nnr"},
    {"label": "Config",    "icon": "⚙", "href": "/config", "id": "nav-config"},
]


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

    return html.Div(
        [
            html.Div(
                html.Img(src=LOGO_URL, className="sidebar-logo", alt="Melonn"),
                className="sidebar-header",
            ),
            html.Nav(nav_links, className="sidebar-nav"),
        ],
        className="sidebar",
        id="sidebar",
    )
