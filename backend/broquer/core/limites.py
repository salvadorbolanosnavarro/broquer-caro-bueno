import hashlib
import hmac
from datetime import datetime, timezone
from .config import configuracion
from .base import transaccion
from .errores import ErrorProducto

def limitar(clave: str, maximo: int, segundos: int = 900):
    cfg = configuracion()
    if len(cfg.rate_limit_secret) < 32:
        raise ErrorProducto(503, 'configuracion_pendiente', 'El acceso no está disponible.')
    clave_hash = hmac.new(cfg.rate_limit_secret.encode(), clave.encode(), hashlib.sha256).hexdigest()
    ventana = int(datetime.now(timezone.utc).timestamp()) // segundos
    with transaccion(limite_hash=clave_hash) as db:
        fila = db.execute('''INSERT INTO broquer.limites_solicitudes(clave_hash,ventana,usadas,expira_en)
            VALUES(%s,%s,1,to_timestamp(%s)) ON CONFLICT(clave_hash,ventana)
            DO UPDATE SET usadas=broquer.limites_solicitudes.usadas+1 WHERE broquer.limites_solicitudes.usadas<%s RETURNING usadas''',
            (clave_hash,ventana,(ventana+1)*segundos,maximo)).fetchone()
        if not fila:
            raise ErrorProducto(429, 'demasiados_intentos', 'Demasiados intentos. Espera unos minutos antes de volver a intentar.')

def limitar_acceso(request, email: str | None = None):
    if not configuracion().disponible:
        raise ErrorProducto(503, 'conexion_pendiente', 'El acceso todavía no está conectado.')
    # Only trusted BFF requests reach these endpoints (proxy shared secret).
    origen = request.headers.get('x-broquer-client-ip', 'desconocido')
    limitar('acceso:ip:' + origen, 120)
    if email:
        limitar('acceso:correo:' + email.strip().casefold(), 10)
