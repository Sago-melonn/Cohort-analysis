"""
Instancia global de Dash para Cohort Analysis v2.
Importar siempre desde aquí: `from app import dash_app`
"""
import os
import dash

# assets/ está en la raíz del proyecto, no dentro de app/
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

dash_app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=_ASSETS,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,600;0,700&display=swap"
    ],
    title="Cohortes · Melonn",
    update_title=None,
)

server = dash_app.server
