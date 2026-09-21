from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
from fastapi import APIRouter, Depends, Response, Request
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from ..core.config import configuracion
from ..core.errores import ErrorProducto
from ..core.auth import contexto
from ..core.jwt import verificar_token
from ..core.base import transaccion
from ..core.limites import limitar_acceso
from ..core.proveedor_auth import solicitar
from ..core.sesiones import crear_sesion, leer_sesion, revocar_actual, revocar_todas, limpiar_cookie

router = APIRouter(prefix='/v1')

class Modelo(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Perfil(Modelo):
    nombre: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=120)
    telefono: str
    zona_horaria: str = 'America/Mexico_City'

    @field_validator('nombre', 'apellidos')
    @classmethod
    def texto(cls, v):
        if not v.strip():
            raise ValueError('Campo requerido')
        return v.strip()

    @field_validator('telefono')
    @classmethod
    def movil(cls, v):
        v = re.sub(r'[\s()-]', '', v)
        if re.fullmatch(r'[0-9]{10}', v):
            v = '+52' + v
        if not re.fullmatch(r'\+52[0-9]{10}', v):
            raise ValueError('Celular mexicano inválido')
        return v

    @field_validator('zona_horaria')
    @classmethod
    def zona(cls, v):
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Zona horaria inválida')
        return v

class Ingreso(Modelo):
    email: EmailStr
    contrasena: str = Field(min_length=1, max_length=128)

class Registro(Perfil):
    email: EmailStr
    contrasena: str = Field(min_length=12, max_length=128)

class Correo(Modelo):
    email: EmailStr

class Confirmacion(Modelo):
    token_hash: str = Field(min_length=20, max_length=512)
    tipo: Literal['email', 'recovery']

class Contrasena(Modelo):
    nueva: str = Field(min_length=12, max_length=128)
    actual: str | None = Field(default=None, max_length=128)


def respuesta_perfil(uid):
    with transaccion(uid) as db:
        fila = db.execute('''SELECT u.nombre,u.apellidos,u.telefono,u.email,u.zona_horaria,
            o.nombre AS organizacion,o.id AS org_id,o.plan FROM broquer.usuarios u
            JOIN broquer.organizacion_miembros m ON m.usuario_id=u.id AND m.activo
            JOIN broquer.organizaciones o ON o.id=m.org_id WHERE u.id=%s AND u.activo''', (uid,)).fetchone()
    return {'perfil_completo': bool(fila), **(fila or {})}


def completar_desde_proveedor(uid, datos):
    # Names/phone metadata may initialize a profile, never permissions or plan.
    if respuesta_perfil(uid)['perfil_completo']:
        return
    meta = datos.get('user', {}).get('user_metadata', {})
    try:
        perfil = Perfil(nombre=meta.get('nombre',''),apellidos=meta.get('apellidos',''),telefono=meta.get('telefono',''))
    except ValueError:
        return
    with transaccion(uid) as db:
        db.execute('SELECT broquer.crear_cuenta_personal(%s,%s,%s)', (perfil.nombre,perfil.apellidos,perfil.telefono))


@router.get('/estado')
def estado():
    cfg = configuracion()
    return {'acceso_disponible': cfg.disponible,
            'registro_disponible': cfg.disponible and cfg.registro_habilitado,
            'google_disponible': cfg.disponible and cfg.google_habilitado}


@router.post('/auth/registrar')
def registrar(datos: Registro, request: Request):
    if not configuracion().registro_habilitado:
        raise ErrorProducto(503, 'registro_pendiente', 'El registro todavía no está habilitado.')
    limitar_acceso(request, str(datos.email))
    r = solicitar('signup', {'email': str(datos.email), 'password': datos.contrasena,
                           'data': datos.model_dump(exclude={'email','contrasena'})})
    if r.status_code >= 500:
        raise ErrorProducto(503, 'acceso_no_disponible', 'No pudimos conectar. Intenta de nuevo.')
    if r.status_code == 429:
        raise ErrorProducto(429, 'demasiados_intentos', 'Espera unos minutos antes de volver a intentar.')
    return {'mensaje_usuario': 'Revisa tu correo para continuar. Si ya tienes cuenta, inicia sesión o recupera tu contraseña.'}


@router.post('/auth/ingresar')
def ingresar(datos: Ingreso, request: Request, response: Response):
    limitar_acceso(request, str(datos.email))
    r = solicitar('token?grant_type=password', {'email': str(datos.email), 'password': datos.contrasena})
    if r.status_code != 200:
        raise ErrorProducto(401, 'acceso_invalido', 'No pudimos iniciar sesión. Revisa tus datos y confirma tu correo.')
    datos_sesion = r.json()
    uid = UUID(verificar_token(datos_sesion['access_token'])['sub'])
    completar_desde_proveedor(uid, datos_sesion)
    revocar_actual(request)
    crear_sesion(datos_sesion, response)
    return respuesta_perfil(uid)


@router.post('/auth/confirmar')
def confirmar(datos: Confirmacion, request: Request, response: Response):
    limitar_acceso(request)
    r = solicitar('verify', {'token_hash': datos.token_hash, 'type': datos.tipo})
    if r.status_code != 200:
        raise ErrorProducto(400, 'enlace_invalido', 'El enlace venció o ya se utilizó. Solicita uno nuevo.')
    d = r.json()
    uid = UUID(verificar_token(d['access_token'])['sub'])
    if datos.tipo == 'email':
        completar_desde_proveedor(uid, d)
    revocar_actual(request)
    crear_sesion(d, response, 'recuperacion' if datos.tipo == 'recovery' else 'normal')
    return {'recuperacion': datos.tipo == 'recovery', **respuesta_perfil(uid)}


@router.post('/auth/recuperar')
def recuperar(datos: Correo, request: Request):
    limitar_acceso(request, str(datos.email))
    r = solicitar('recover', {'email': str(datos.email)})
    if r.status_code >= 500:
        raise ErrorProducto(503, 'acceso_no_disponible', 'No pudimos conectar. Intenta de nuevo.')
    return {'mensaje_usuario': 'Si el correo corresponde a una cuenta, recibirás instrucciones para recuperar el acceso.'}


@router.post('/auth/contrasena')
def contrasena(datos: Contrasena, request: Request, response: Response):
    limitar_acceso(request)
    sesion = leer_sesion(request, permitir_recuperacion=True)
    uid = sesion['usuario_id']
    token = sesion['credenciales']['access_token']
    if sesion['proposito'] == 'normal':
        if not datos.actual:
            raise ErrorProducto(422, 'contrasena_actual_requerida', 'Escribe tu contraseña actual.')
        with transaccion(uid) as db:
            usuario = db.execute('SELECT email FROM broquer.usuarios WHERE id=%s', (uid,)).fetchone()
        if not usuario:
            raise ErrorProducto(409, 'perfil_incompleto', 'Completa tu perfil primero.')
        r = solicitar('token?grant_type=password', {'email': usuario['email'], 'password': datos.actual})
        if r.status_code != 200 or UUID(verificar_token(r.json()['access_token'])['sub']) != uid:
            raise ErrorProducto(401, 'acceso_invalido', 'La contraseña actual no es correcta.')
        token = r.json()['access_token']
    r = solicitar('user', {'password': datos.nueva}, metodo='PUT', token=token)
    if r.status_code != 200:
        raise ErrorProducto(400, 'contrasena_rechazada', 'No se pudo cambiar la contraseña. Usa una contraseña distinta y segura.')
    revocar_todas(uid)
    limpiar_cookie(response)
    return {'mensaje_usuario': 'Contraseña actualizada. Inicia sesión con tu nueva contraseña.'}


@router.post('/auth/salir')
def salir(request: Request, response: Response):
    revocar_actual(request)
    limpiar_cookie(response)
    return {'sesion_cerrada': True}


@router.post('/auth/salir-todas')
def salir_todas(request: Request, response: Response):
    uid = leer_sesion(request)['usuario_id']
    revocar_todas(uid)
    limpiar_cookie(response)
    return {'mensaje_usuario': 'Se cerraron tus sesiones en todos los dispositivos.'}


@router.get('/auth/sesion')
def sesion(request: Request):
    s = leer_sesion(request, permitir_recuperacion=True)
    return {'recuperacion': s['proposito'] == 'recuperacion', **respuesta_perfil(s['usuario_id'])}


@router.post('/auth/completar-perfil')
def completar_perfil(datos: Perfil, request: Request):
    s = leer_sesion(request)
    uid = s['usuario_id']
    with transaccion(uid) as db:
        db.execute('SELECT broquer.crear_cuenta_personal(%s,%s,%s)', (datos.nombre,datos.apellidos,datos.telefono))
        db.execute('UPDATE broquer.usuarios SET zona_horaria=%s,actualizado_en=now() WHERE id=%s', (datos.zona_horaria,uid))
    return respuesta_perfil(uid)


@router.get('/me')
def me(ctx=Depends(contexto)):
    return {**respuesta_perfil(ctx.usuario_id), 'permisos': ctx.permisos}


@router.patch('/me')
def editar_perfil(datos: Perfil, ctx=Depends(contexto)):
    with transaccion(ctx.usuario_id) as db:
        db.execute('''UPDATE broquer.usuarios SET nombre=%s,apellidos=%s,telefono=%s,zona_horaria=%s,actualizado_en=now() WHERE id=%s''',
                   (datos.nombre,datos.apellidos,datos.telefono,datos.zona_horaria,ctx.usuario_id))
        db.execute("INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(%s,%s,'perfil_editado',%s)", (ctx.org_id,ctx.usuario_id,ctx.usuario_id))
    return respuesta_perfil(ctx.usuario_id)
