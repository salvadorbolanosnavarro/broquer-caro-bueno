from fastapi import Request
from .sesiones import leer_sesion
from .base import transaccion
from .errores import ErrorProducto
from .permisos import Contexto, efectivos

def contexto(request: Request):
    uid = leer_sesion(request)['usuario_id']
    with transaccion(uid) as db:
        fila = db.execute('''SELECT u.activo,u.rol_interno,u.modulos_desactivados,m.org_id,m.rol_org,m.permisos,o.plan,o.tipo,o.zona_horaria
            FROM broquer.usuarios u JOIN broquer.organizacion_miembros m ON m.usuario_id=u.id AND m.activo
            JOIN broquer.organizaciones o ON o.id=m.org_id AND o.activa WHERE u.id=%s''', (uid,)).fetchone()
    if not fila:
        raise ErrorProducto(409, 'perfil_incompleto', 'Completa tu perfil para continuar.')
    return Contexto(uid, fila['org_id'], fila['rol_org'], fila['plan'], efectivos(fila['rol_org'], fila['tipo'], fila['permisos']),
                    tuple(fila['modulos_desactivados']), fila['zona_horaria'], fila['rol_interno'] in ('equipo','admin'))
