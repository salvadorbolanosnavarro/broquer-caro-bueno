import httpx
from .config import configuracion
from .errores import ErrorProducto

def solicitar(ruta: str, datos: dict | None = None, *, metodo: str = 'POST', token: str | None = None):
    cfg = configuracion()
    if not cfg.disponible:
        raise ErrorProducto(503, 'conexion_pendiente', 'El acceso todavía no está conectado.')
    headers = {'apikey': cfg.supabase_publishable_key}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        with httpx.Client(timeout=12, follow_redirects=False) as cliente:
            return cliente.request(metodo, cfg.supabase_url.rstrip('/') + '/auth/v1/' + ruta,
                                   headers=headers, json=datos)
    except httpx.HTTPError:
        raise ErrorProducto(503, 'acceso_no_disponible', 'No pudimos conectar. Intenta de nuevo.')
