"""
Shell principal de la app: sidebar fijo + dcc.Location + área de contenido.
Importar este módulo en run.py para registrar el layout en dash_app.
"""
from dash import dcc, html

from app import dash_app
from components.sidebar import sidebar

dash_app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        sidebar(),
        html.Div(id="page-content", className="page-content"),
    ],
    className="app-shell",
)
