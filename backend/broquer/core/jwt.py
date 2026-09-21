from functools import lru_cache
from uuid import UUID
import jwt
from .config import configuracion
from .errores import ErrorProducto

@lru_cache
def cliente_jwks(url):
    # Cache the JWKS, not individual signing keys indefinitely.
    return jwt.PyJWKClient(url + '/auth/v1/.well-known/jwks.json', cache_keys=False, lifespan=300, timeout=5)

def verificar_token(token: str):
    cfg = configuracion()
    if not cfg.disponible:
        raise ErrorProducto(503, 'conexion_pendiente', 'El acceso todavía no está conectado.')
    try:
        clave = cliente_jwks(cfg.supabase_url.rstrip('/')).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, clave.key, algorithms=['ES256', 'RS256'], audience='authenticated',
                            issuer=cfg.supabase_url.rstrip('/') + '/auth/v1',
                            options={'require': ['exp', 'iat', 'sub', 'aud', 'iss']})
        UUID(claims['sub'])
        if claims.get('role') != 'authenticated':
            raise ValueError()
        return claims
    except (jwt.PyJWTError, ValueError, KeyError):
        raise ErrorProducto(401, 'sesion_invalida', 'Tu sesión terminó. Inicia sesión de nuevo.')
