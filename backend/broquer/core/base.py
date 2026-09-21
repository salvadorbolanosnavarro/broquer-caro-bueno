from contextlib import contextmanager
from uuid import UUID
import psycopg
from psycopg.rows import dict_row
from .config import configuracion
from .errores import ErrorProducto

@contextmanager
def transaccion(usuario_id: UUID | None = None, *, sesion_hash: str = '', limite_hash: str = ''):
    cfg = configuracion()
    if not cfg.database_url:
        raise ErrorProducto(503, 'conexion_pendiente', 'El servicio todavía no está conectado.')
    with psycopg.connect(cfg.database_url, row_factory=dict_row, connect_timeout=5) as conexion:
        conexion.execute('SET LOCAL ROLE broquer_api')
        conexion.execute("SELECT set_config('broquer.usuario_id',%s,true)", (str(usuario_id) if usuario_id else '',))
        conexion.execute("SELECT set_config('broquer.sesion_hash',%s,true)", (sesion_hash,))
        conexion.execute("SELECT set_config('broquer.limite_hash',%s,true)", (limite_hash,))
        yield conexion
