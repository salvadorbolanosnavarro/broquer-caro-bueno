import base64
import hashlib
import secrets
from urllib.parse import urlencode
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from ..core.config import configuracion
from ..core.cifrado import cifrador
from ..core.errores import ErrorProducto
from ..core.limites import limitar_acceso
from ..core.proveedor_auth import solicitar
from ..core.sesiones import crear_sesion, revocar_actual
from .cuentas import completar_desde_proveedor, respuesta_perfil
from ..core.jwt import verificar_token
from uuid import UUID
from cryptography.fernet import InvalidToken

router = APIRouter(prefix='/v1/auth/google')
class Codigo(BaseModel):
    model_config = ConfigDict(extra='forbid')
    codigo: str = Field(min_length=10, max_length=2048)

@router.post('/iniciar')
def iniciar(request: Request, response: Response):
    cfg = configuracion()
    if not cfg.google_habilitado:
        raise ErrorProducto(503, 'google_no_disponible', 'El acceso con Google no está habilitado.')
    limitar_acceso(request)
    verificador = secrets.token_urlsafe(64)
    desafio = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).decode().rstrip('=')
    response.set_cookie('broquer_pkce', cifrador().encrypt(verificador.encode()).decode(),
                        max_age=600, httponly=True, secure=True, samesite='lax', path='/api/v1/auth/google')
    parametros = urlencode({'provider':'google','redirect_to':cfg.sitio_url+'/acceso/confirmar',
                             'code_challenge':desafio,'code_challenge_method':'s256'})
    return {'url': cfg.supabase_url.rstrip('/') + '/auth/v1/authorize?' + parametros}

@router.post('/confirmar')
def confirmar(datos: Codigo, request: Request, response: Response):
    if not configuracion().google_habilitado:
        raise ErrorProducto(503, 'google_no_disponible', 'El acceso con Google no está habilitado.')
    limitar_acceso(request)
    try:
        verificador = cifrador().decrypt(request.cookies.get('broquer_pkce','').encode(), ttl=600).decode()
    except (InvalidToken, ValueError):
        raise ErrorProducto(400, 'oauth_vencido', 'Vuelve a iniciar el acceso con Google desde este navegador.')
    r = solicitar('token?grant_type=pkce', {'auth_code':datos.codigo,'code_verifier':verificador})
    if r.status_code != 200:
        raise ErrorProducto(400, 'oauth_invalido', 'No se pudo completar el acceso con Google. Intenta de nuevo.')
    response.delete_cookie('broquer_pkce',path='/api/v1/auth/google',secure=True,httponly=True,samesite='lax')
    d = r.json()
    uid = UUID(verificar_token(d['access_token'])['sub'])
    completar_desde_proveedor(uid, d)
    revocar_actual(request)
    crear_sesion(d, response)
    return respuesta_perfil(uid)
