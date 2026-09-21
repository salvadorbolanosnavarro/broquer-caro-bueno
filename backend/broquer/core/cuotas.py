from .base import transaccion
from .errores import ErrorProducto
from .permisos import exigir

def reservar_cuota(ctx,modulo,accion):
    exigir(ctx,modulo)
    with transaccion(ctx.usuario_id) as db:
        funcion=db.execute('SELECT cuota_mensual FROM broquer.plan_funciones WHERE plan=%s AND modulo=%s AND accion=%s',(ctx.plan,modulo,accion)).fetchone()
        if not funcion:raise ErrorProducto(402,'requiere_plan','Tu plan no incluye esta función.')
        limite=funcion['cuota_mensual']
        if limite<=0:raise ErrorProducto(429,'cuota_agotada','Alcanzaste el límite de uso de esta función.')
        # Atomic bounded increment; period follows the organization's timezone.
        fila=db.execute('''INSERT INTO broquer.uso_cuotas(org_id,creado_por,modulo,accion,periodo,usado)
          VALUES(%s,%s,%s,%s,date_trunc('month',now() AT TIME ZONE %s)::date,1)
          ON CONFLICT(org_id,creado_por,modulo,accion,periodo) DO UPDATE SET usado=broquer.uso_cuotas.usado+1
          WHERE broquer.uso_cuotas.usado<%s RETURNING usado''',(ctx.org_id,ctx.usuario_id,modulo,accion,ctx.zona_horaria,limite)).fetchone()
        if not fila:raise ErrorProducto(429,'cuota_agotada','Alcanzaste el límite de uso de esta función.')
        return fila['usado']
