"""
Entry point — Cohort Analysis v2
Uso: python run.py
"""
# 1. Crear instancia Dash
from app import dash_app          # noqa: F401

# 2. Registrar layout (sidebar + dcc.Location + page-content)
import app.layout                 # noqa: F401

# 3. Registrar callbacks (orden importa: routing debe ir primero)
import callbacks.routing          # noqa: F401
import callbacks.cb_inputs        # noqa: F401
import callbacks.cb_nor           # noqa: F401
import callbacks.cb_ndr           # noqa: F401
import callbacks.cb_nnr           # noqa: F401

if __name__ == "__main__":
    dash_app.run(debug=True, port=8052)
