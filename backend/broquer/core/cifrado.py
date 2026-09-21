import json
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from .config import configuracion
from .errores import ErrorProducto

def cifrador():
    claves = configuracion().sesiones_claves
    if not claves:
        raise ErrorProducto(503, 'configuracion_pendiente', 'El acceso no está disponible.')
    return MultiFernet([Fernet(c.encode()) for c in claves])

def cifrar(datos: dict) -> str:
    return cifrador().encrypt(json.dumps(datos).encode()).decode()

def descifrar(valor: str) -> dict:
    try:
        return json.loads(cifrador().decrypt(valor.encode()))
    except (InvalidToken, ValueError):
        raise ErrorProducto(401, 'sesion_invalida', 'Inicia sesión de nuevo.')
