from uuid import UUID
from urllib.parse import quote, urlparse
import httpx
from fastapi import APIRouter, Depends
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.config import configuracion
from ..core.errores import ErrorProducto

router = APIRouter(prefix='/v1/archivos')

def validar_ruta(ruta: str, org_id: UUID):
    partes = ruta.split('/')
    if len(partes) != 2 or partes[0] != str(org_id) or not partes[1] or '..' in ruta or '\\' in ruta or '%' in ruta:
        raise ErrorProducto(404, 'archivo_no_encontrado', 'No encontramos ese archivo.')

@router.get('/{archivo_id}/descarga')
def descargar(archivo_id: UUID, ctx=Depends(contexto)):
    with transaccion(ctx.usuario_id) as db:
        archivo = db.execute('SELECT ruta FROM broquer.archivos WHERE id=%s AND org_id=%s AND archivado_en IS NULL',
                             (archivo_id, ctx.org_id)).fetchone()
    if not archivo:
        raise ErrorProducto(404, 'archivo_no_encontrado', 'No encontramos ese archivo.')
    validar_ruta(archivo['ruta'], ctx.org_id)
    cfg = configuracion()
    if not cfg.supabase_storage_key:
        raise ErrorProducto(503, 'archivos_no_conectados', 'El servicio de archivos no está conectado.')
    base = cfg.supabase_url.rstrip('/')
    bucket = quote(cfg.storage_bucket, safe='')
    ruta = quote(archivo['ruta'], safe='/')
    try:
        with httpx.Client(timeout=12, follow_redirects=False) as cliente:
            r = cliente.post(f'{base}/storage/v1/object/sign/{bucket}/{ruta}',
                             headers={'apikey':cfg.supabase_storage_key,'Authorization':'Bearer '+cfg.supabase_storage_key},
                             json={'expiresIn':120})
            r.raise_for_status()
            firmado = r.json()['signedURL']
        esperado = f'/object/sign/{bucket}/{ruta}?'
        if not firmado.startswith(esperado) or urlparse(firmado).netloc:
            raise ValueError()
        return {'url':base+'/storage/v1'+firmado,'expira_en_segundos':120}
    except (httpx.HTTPError, ValueError, KeyError):
        raise ErrorProducto(503, 'archivo_no_disponible', 'No pudimos preparar la descarga. Intenta de nuevo.')
