"""
Callback de routing: URL → page-content + clases activas del nav.

Rutas:
  /        → landing (sin nav activo)
  /inputs  → Inputs
  /nor     → NOR / NRR
  /ndr     → NDR / ODR
  /nnr     → NNR / NNO
"""
from dash import Input, Output, callback

from app.pages.landing import layout as landing_layout
from callbacks.cb_inputs import inputs_layout
from callbacks.cb_nor import nor_layout
from callbacks.cb_ndr import ndr_layout
from callbacks.cb_nnr import nnr_layout

_BASE   = "nav-item"
_ACTIVE = "nav-item nav-active"

# active_idx: índice del nav item activo (0-3), None = ninguno (landing)
_ROUTES = {
    "/":       (landing_layout, None),
    "/inputs": (inputs_layout,  0),
    "/nor":    (nor_layout,     1),
    "/ndr":    (ndr_layout,     2),
    "/nnr":    (nnr_layout,     3),
}


@callback(
    Output("page-content", "children"),
    Output("nav-inputs",   "className"),
    Output("nav-nor",      "className"),
    Output("nav-ndr",      "className"),
    Output("nav-nnr",      "className"),
    Input("url", "pathname"),
)
def route(pathname: str):
    layout_fn, active_idx = _ROUTES.get(pathname, (landing_layout, None))
    nav_classes = [_ACTIVE if i == active_idx else _BASE for i in range(4)]
    return (layout_fn(), *nav_classes)
