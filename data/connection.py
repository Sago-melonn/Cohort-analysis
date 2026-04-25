"""
Conexión a Amazon Redshift con pool.
"""
import os
import threading
import redshift_connector
from redshift_connector import Connection
from dotenv import load_dotenv

load_dotenv()

_pool: list[Connection] = []
_pool_lock = threading.Lock()
_POOL_SIZE = 3  # máximo de conexiones simultáneas


def _new_connection() -> Connection:
    return redshift_connector.connect(
        host=os.environ["REDSHIFT_HOST"],
        database=os.environ["REDSHIFT_DB"],
        port=int(os.environ.get("REDSHIFT_PORT", 5439)),
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
        timeout=300,
        tcp_keepalive=True,
    )


def get_connection() -> Connection:
    """Retorna una conexión del pool, o crea una nueva si hay espacio."""
    with _pool_lock:
        # Reutiliza una conexión existente si está viva
        while _pool:
            conn = _pool.pop()
            try:
                conn.cursor().execute("SELECT 1")  # verifica que sigue viva
                return conn
            except Exception:
                pass  # conexión muerta, descartarla

    # No había conexiones disponibles, crea una nueva
    return _new_connection()


def release_connection(conn: Connection) -> None:
    """Devuelve una conexión al pool para reutilizarla."""
    with _pool_lock:
        if len(_pool) < _POOL_SIZE:
            _pool.append(conn)
        else:
            conn.close()