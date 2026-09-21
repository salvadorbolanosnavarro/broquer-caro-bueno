"""Internal enqueue service; callers authorize business actions before enqueueing."""
import hashlib
import json
from psycopg.types.json import Jsonb
from .base import transaccion
from .errores import ErrorProducto


def encolar(ctx, tipo: str, clave: str, datos: dict):
    if not tipo or len(tipo) > 80 or not clave or len(clave) > 200:
        raise ValueError('Invalid job identity')
    contenido = json.dumps(datos, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    if len(contenido.encode()) > 32768:
        raise ValueError('Job payload exceeds 32 KiB')
    # Scope caller-provided idempotency keys to the authenticated user.
    llave = hashlib.sha256((str(ctx.usuario_id) + ':' + clave).encode()).hexdigest()
    with transaccion(ctx.usuario_id) as db:
        # Serialize identical submissions, including the empty-row case. Avoid UPDATE privileges.
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (str(ctx.org_id)+':'+tipo+':'+llave,))
        existente = db.execute('SELECT id,datos FROM broquer.trabajos WHERE org_id=%s AND tipo=%s AND clave=%s',
                               (ctx.org_id,tipo,llave)).fetchone()
        if existente:
            if json.dumps(existente['datos'],sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False) != contenido:
                raise ErrorProducto(409,'solicitud_distinta','Esta solicitud ya existe con otros datos. Inicia una nueva.')
            return existente['id']
        return db.execute('''INSERT INTO broquer.trabajos(org_id,creado_por,tipo,clave,datos)
            VALUES(%s,%s,%s,%s,%s) RETURNING id''',
            (ctx.org_id,ctx.usuario_id,tipo,llave,Jsonb(datos))).fetchone()['id']
