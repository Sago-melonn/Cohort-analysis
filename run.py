"""
Entry point — Cohort Analysis v2
Paso 2: Shell (sidebar + routing)
"""
# 1. Instancia Dash
from app import dash_app          # noqa: F401

# 2. Layout: sidebar fijo + dcc.Location + área de contenido
import app.layout                 # noqa: F401

# 3. Routing: URL → página activa + nav resaltado
import callbacks.routing          # noqa: F401

# 4. Callbacks stub (PreventUpdate si la página no está activa)
import callbacks.cb_nor           # noqa: F401
import callbacks.cb_ndr           # noqa: F401
import callbacks.cb_nnr           # noqa: F401

if __name__ == "__main__":
    dash_app.run(debug=True, port=8052)
