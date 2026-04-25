"""
Entry point — Cohort Analysis v2
"""
import logging
import threading

logger = logging.getLogger(__name__)

# 1. Instancia Dash
from app import dash_app          # noqa: F401

# 2. Layout: sidebar fijo + dcc.Location + área de contenido
import app.layout                 # noqa: F401

# 3. Routing: URL → página activa + nav resaltado
import callbacks.routing          # noqa: F401

# 4. Vista Inputs — datos reales desde Redshift
import callbacks.cb_inputs        # noqa: F401

# 5. Callbacks stub (PreventUpdate si la página no está activa)
import callbacks.cb_nor           # noqa: F401
import callbacks.cb_ndr           # noqa: F401
import callbacks.cb_nnr           # noqa: F401
import callbacks.cb_rolling       # noqa: F401
import callbacks.cb_config        # noqa: F401


# ── Cache warm-up ─────────────────────────────────────────────────────────────
# Dispara load_orders y load_revenue en background al arrancar la app.
# Cuando el usuario llegue a Inputs los datos ya estarán en caché.

def _warmup():
    from data.data_loader import (
        _load_orders_raw, _load_revenue_raw, _load_forecast_raw, load_budget_nnr,
    )
    logger.info("Cache warm-up: cargando datos raw...")
    try:
        _load_orders_raw()
        _load_revenue_raw()
        _load_forecast_raw()
        load_budget_nnr()
        logger.info("Cache warm-up: completado.")
    except Exception as exc:
        logger.warning("Cache warm-up falló (no crítico): %s", exc)


threading.Thread(target=_warmup, daemon=True).start()


if __name__ == "__main__":
    dash_app.run(debug=True, port=8052)
