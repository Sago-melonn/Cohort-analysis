"""
Conexión a Amazon Redshift.
Patrón idéntico al SG&A Control — leer credenciales desde .env en la raíz del proyecto.
"""
import os
import redshift_connector
from dotenv import load_dotenv

load_dotenv()


def get_connection() -> redshift_connector.Connection:
    """Abre y retorna una conexión a Redshift."""
    return redshift_connector.connect(
        host=os.environ["REDSHIFT_HOST"],
        database=os.environ["REDSHIFT_DB"],
        port=int(os.environ.get("REDSHIFT_PORT", 5439)),
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
        timeout=300,
        tcp_keepalive=True,
    )
