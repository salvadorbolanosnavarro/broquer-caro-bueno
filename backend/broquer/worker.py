"""Persistent, leased queue. External side effects require their own idempotent handler."""
from contextlib import contextmanager
import time
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from .core.config import configuracion

class Reintentar(Exception):
    pass

@contextmanager
def conexion_worker():
    dsn = configuracion().database_worker_url
    if not dsn:
        raise RuntimeError('DATABASE_WORKER_URL is required')
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as db:
        db.execute('SET LOCAL ROLE broquer_worker')
        yield db

def verificar_cola(db, trabajo):
    # Atomic DB-only check. The unique key makes the effect idempotent after a lease recovery.
    db.execute("""INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia)
        VALUES(%s,%s,'cola_verificada',%s) ON CONFLICT DO NOTHING""",
        (trabajo['org_id'],trabajo['creado_por'],trabajo['id']))
    return {'verificado': True}

MANEJADORES = {'verificar_cola': verificar_cola}

def ejecutar_una():
    intento = uuid4()
    with conexion_worker() as db:
        db.execute("""UPDATE broquer.trabajos SET estado='fallido',error_codigo='intentos_agotados',bloqueado_hasta=NULL
            WHERE estado='ejecutando' AND bloqueado_hasta<now() AND intentos>=max_intentos""")
        trabajo = db.execute("""WITH candidato AS (
            SELECT id FROM broquer.trabajos WHERE intentos<max_intentos AND
            ((estado='pendiente' AND ejecutar_en<=now()) OR (estado='ejecutando' AND bloqueado_hasta<now()))
            ORDER BY ejecutar_en FOR UPDATE SKIP LOCKED LIMIT 1)
            UPDATE broquer.trabajos t SET estado='ejecutando',intentos=intentos+1,
            bloqueado_hasta=now()+interval '2 minutes',intento_id=%s
            FROM candidato c WHERE t.id=c.id RETURNING t.*""", (intento,)).fetchone()
    if not trabajo:
        return False
    manejador = MANEJADORES.get(trabajo['tipo'])
    try:
        with conexion_worker() as db:
            vigente = db.execute("SELECT id FROM broquer.trabajos WHERE id=%s AND intento_id=%s AND estado='ejecutando' FOR UPDATE", (trabajo['id'],intento)).fetchone()
            if not vigente:
                return True
            if not manejador:
                db.execute("UPDATE broquer.trabajos SET estado='fallido',error_codigo='tipo_no_soportado',bloqueado_hasta=NULL WHERE id=%s AND intento_id=%s", (trabajo['id'],intento))
                return True
            resultado = manejador(db, trabajo)
            db.execute("UPDATE broquer.trabajos SET estado='completado',resultado=%s,error_codigo=NULL,bloqueado_hasta=NULL WHERE id=%s AND intento_id=%s", (Jsonb(resultado),trabajo['id'],intento))
    except Exception as exc:
        reintentar = isinstance(exc,(Reintentar,psycopg.OperationalError)) and trabajo['intentos'] < trabajo['max_intentos']
        with conexion_worker() as db:
            db.execute("""UPDATE broquer.trabajos SET estado=%s,error_codigo=%s,bloqueado_hasta=NULL,
                ejecutar_en=now()+make_interval(secs=>%s) WHERE id=%s AND intento_id=%s""",
                ('pendiente' if reintentar else 'fallido','error_temporal' if reintentar else 'error_manejador',min(300,2**trabajo['intentos']),trabajo['id'],intento))
    return True

if __name__ == '__main__':
    while True:
        try:
            if not ejecutar_una():
                time.sleep(2)
        except psycopg.OperationalError:
            time.sleep(5)
