"""
Instancia global de Dash para Cohort Analysis v2.
Importar siempre desde aquí: `from app import dash_app`
"""
import dash

dash_app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,600;0,700&display=swap"
    ],
    title="Cohortes · Melonn",
    update_title=None,
)

server = dash_app.server
