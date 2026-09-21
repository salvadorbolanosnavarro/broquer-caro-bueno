from uuid import UUID
from fastapi import APIRouter, Depends
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.errores import ErrorProducto

router = APIRouter(prefix='/v1/trabajos')

@router.get('/{trabajo_id}')
def consultar(trabajo_id: UUID, ctx=Depends(contexto)):
    with transaccion(ctx.usuario_id) as db:
        # Never serialize payload, raw provider results or internal failure details.
        fila = db.execute('''SELECT id,estado,creado_en FROM broquer.trabajos
            WHERE id=%s AND org_id=%s AND creado_por=%s''',
            (trabajo_id,ctx.org_id,ctx.usuario_id)).fetchone()
    if not fila:
        raise ErrorProducto(404,'trabajo_no_encontrado','No encontramos esa solicitud.')
    mensajes = {'pendiente':'Tu solicitud está en espera.', 'ejecutando':'Estamos procesando tu solicitud.',
                'completado':'Tu solicitud se completó.', 'fallido':'No pudimos completar tu solicitud.'}
    return {**fila,'mensaje_usuario':mensajes[fila['estado']]}
