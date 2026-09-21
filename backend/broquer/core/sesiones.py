from datetime import datetime, timezone, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID
from fastapi import Request, Response
from .base import transaccion
from .cifrado import cifrar, descifrar
from .jwt import verificar_token
from .proveedor_auth import solicitar
from .errores import ErrorProducto

NOMBRE = 'broquer_sesion'
RUTA = '/api/v1'

def hash_sesion(token: str):
    return sha256(token.encode()).hexdigest()

def limpiar_cookie(response: Response):
    response.delete_cookie(NOMBRE, path=RUTA, secure=True, httponly=True, samesite='lax')
    # Clear the legacy cookie from the first scaffold as well.
    response.delete_cookie('broquer_refresh', path=RUTA, secure=True, httponly=True, samesite='lax')

def crear_sesion(datos: dict, response: Response, proposito: str = 'normal'):
    claims = verificar_token(datos['access_token'])
    uid = UUID(claims['sub'])
    token = token_urlsafe(48)
    h = hash_sesion(token)
    segundos = 900 if proposito == 'recuperacion' else 30 * 24 * 60 * 60
    credenciales = {'access_token': datos['access_token'], 'refresh_token': datos['refresh_token'],
                    'exp': claims['exp'], 'meta': datos.get('user', {}).get('user_metadata', {})}
    with transaccion(uid, sesion_hash=h) as db:
        activo = db.execute('SELECT activo FROM broquer.usuarios WHERE id=%s', (uid,)).fetchone()
        if activo and not activo['activo']:
            raise ErrorProducto(403, 'cuenta_inactiva', 'Tu cuenta no está activa.')
        db.execute('''INSERT INTO broquer.sesiones(usuario_id,token_hash,credenciales_cifradas,proposito,expira_en)
            VALUES(%s,%s,%s,%s,%s)''', (uid,h,cifrar(credenciales),proposito,datetime.now(timezone.utc)+timedelta(seconds=segundos)))
    limpiar_cookie(response)
    response.set_cookie(NOMBRE, token, max_age=segundos, httponly=True, secure=True, samesite='lax', path=RUTA)
    return uid

def leer_sesion(request: Request, *, permitir_recuperacion=False):
    token = request.cookies.get(NOMBRE, '')
    if not 40 <= len(token) <= 128:
        raise ErrorProducto(401, 'sesion_requerida', 'Inicia sesión para continuar.')
    h = hash_sesion(token)
    with transaccion(sesion_hash=h) as db:
        fila = db.execute('''SELECT * FROM broquer.sesiones WHERE token_hash=%s AND revocada_en IS NULL
            AND expira_en>now() FOR UPDATE''', (h,)).fetchone()
        if not fila:
            raise ErrorProducto(401, 'sesion_invalida', 'Tu sesión terminó. Inicia sesión de nuevo.')
        if fila['proposito'] != 'normal' and not permitir_recuperacion:
            raise ErrorProducto(403, 'recuperacion_pendiente', 'Termina de restablecer tu contraseña.')
        datos = descifrar(fila['credenciales_cifradas'])
        if datos['exp'] <= datetime.now(timezone.utc).timestamp() + 60:
            respuesta = solicitar('token?grant_type=refresh_token', {'refresh_token': datos['refresh_token']})
            if respuesta.status_code != 200:
                raise ErrorProducto(401, 'sesion_invalida', 'Inicia sesión de nuevo.')
            nuevos = respuesta.json()
            claims = verificar_token(nuevos['access_token'])
            if UUID(claims['sub']) != fila['usuario_id']:
                raise ErrorProducto(401, 'sesion_invalida', 'Inicia sesión de nuevo.')
            datos.update(access_token=nuevos['access_token'], refresh_token=nuevos['refresh_token'], exp=claims['exp'])
            db.execute('UPDATE broquer.sesiones SET credenciales_cifradas=%s WHERE id=%s', (cifrar(datos), fila['id']))
        claims = verificar_token(datos['access_token'])
        if UUID(claims['sub']) != fila['usuario_id']:
            raise ErrorProducto(401, 'sesion_invalida', 'Inicia sesión de nuevo.')
        db.execute('UPDATE broquer.sesiones SET ultimo_uso=now() WHERE id=%s', (fila['id'],))
    # Reject disabled accounts even in refresh/profile/recovery flows.
    with transaccion(fila['usuario_id']) as db:
        usuario = db.execute('SELECT activo FROM broquer.usuarios WHERE id=%s', (fila['usuario_id'],)).fetchone()
        if usuario and not usuario['activo']:
            raise ErrorProducto(403, 'cuenta_inactiva', 'Tu cuenta no está activa.')
    return {'usuario_id': fila['usuario_id'], 'id': fila['id'], 'hash': h,
            'proposito': fila['proposito'], 'credenciales': datos}

def revocar_actual(request: Request):
    token = request.cookies.get(NOMBRE, '')
    if token:
        h = hash_sesion(token)
        with transaccion(sesion_hash=h) as db:
            db.execute('UPDATE broquer.sesiones SET revocada_en=now() WHERE token_hash=%s', (h,))

def revocar_todas(uid):
    with transaccion(uid) as db:
        db.execute('UPDATE broquer.sesiones SET revocada_en=now() WHERE usuario_id=%s AND revocada_en IS NULL', (uid,))
