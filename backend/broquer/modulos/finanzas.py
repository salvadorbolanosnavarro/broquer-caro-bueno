from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID
import hashlib
import json
from fastapi import APIRouter,Depends,Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel,ConfigDict,Field,AwareDatetime,model_validator
from psycopg.errors import UniqueViolation
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.errores import ErrorProducto
from ..core.permisos import exigir
router=APIRouter(prefix='/v1/finanzas')
def seguro(valor):
    return jsonable_encoder(valor,custom_encoder={Decimal:str})

SEMILLAS=json.loads((Path(__file__).resolve().parents[3]/'shared/categorias-finanzas.json').read_text())
class Cuenta(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    nombre:str=Field(min_length=1,max_length=100)
    tipo:Literal['efectivo','banco','tarjeta','otra']='banco'
    moneda:Literal['MXN','USD']='MXN'
    saldo_inicial:Decimal=Field(default=Decimal('0'),max_digits=16,decimal_places=2)
class EstadoCuenta(BaseModel):
    model_config=ConfigDict(extra='forbid')
    activa:bool=Field(strict=True)
    actualizado_en:AwareDatetime
class Categoria(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    nombre:str=Field(min_length=1,max_length=100)
    tipo:Literal['ingreso','gasto']
class Movimiento(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    tipo:Literal['ingreso','gasto','transferencia']
    monto:Decimal=Field(gt=0,max_digits=16,decimal_places=2)
    fecha:date
    concepto:str=Field(min_length=1,max_length=200)
    notas:str=Field(default='',max_length=4000)
    cuenta_id:UUID
    cuenta_destino_id:UUID|None=None
    categoria_id:UUID|None=None
    propiedad_id:UUID|None=None
    contacto_id:UUID|None=None
    idempotencia:UUID
    @model_validator(mode='after')
    def relaciones(self):
        if not 2000<=self.fecha.year<=2100:raise ValueError('Fecha fuera de rango')
        if self.tipo=='transferencia':
            if not self.cuenta_destino_id or self.cuenta_destino_id==self.cuenta_id or self.categoria_id:raise ValueError('Transferencia inválida')
        elif self.cuenta_destino_id or not self.categoria_id:raise ValueError('Selecciona categoría y cuenta')
        return self
class Anulacion(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    motivo:str=Field(min_length=1,max_length=1000)
    actualizado_en:AwareDatetime

def auditar(db,ctx,accion,identificador):
    db.execute('INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(%s,%s,%s,%s)',(ctx.org_id,ctx.usuario_id,accion,identificador))

def cuentas_db(db,ctx):
    return db.execute('''SELECT c.*,c.saldo_inicial+COALESCE((SELECT sum(
      CASE WHEN m.tipo='ingreso' OR m.cuenta_destino_id=c.id THEN m.monto ELSE -m.monto END)
      FROM broquer.fin_movimientos m WHERE m.org_id=c.org_id AND m.anulada_en IS NULL AND (m.cuenta_id=c.id OR m.cuenta_destino_id=c.id)),0) AS saldo
      FROM broquer.fin_cuentas c WHERE c.org_id=%s ORDER BY c.activa DESC,c.nombre,c.id''',(ctx.org_id,)).fetchall()

@router.get('/cuentas')
def cuentas(ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    with transaccion(ctx.usuario_id) as db:return seguro({'cuentas':cuentas_db(db,ctx)})

@router.post('/cuentas',status_code=201)
def crear_cuenta(datos:Cuenta,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    try:
        with transaccion(ctx.usuario_id) as db:
            fila=db.execute('INSERT INTO broquer.fin_cuentas(org_id,creado_por,nombre,tipo,moneda,saldo_inicial) VALUES(%s,%s,%s,%s,%s,%s) RETURNING *',(ctx.org_id,ctx.usuario_id,datos.nombre,datos.tipo,datos.moneda,datos.saldo_inicial)).fetchone()
            auditar(db,ctx,'cuenta_financiera_creada',fila['id']);return seguro({**fila,'saldo':fila['saldo_inicial']})
    except UniqueViolation:raise ErrorProducto(409,'nombre_duplicado','Ya tienes una cuenta con ese nombre.')

@router.patch('/cuentas/{identificador}')
def estado_cuenta(identificador:UUID,datos:EstadoCuenta,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    with transaccion(ctx.usuario_id) as db:
        fila=db.execute('SELECT * FROM broquer.fin_cuentas WHERE id=%s AND org_id=%s FOR UPDATE',(identificador,ctx.org_id)).fetchone()
        if not fila:raise ErrorProducto(404,'cuenta_no_encontrada','No encontramos esa cuenta.')
        if fila['actualizado_en']!=datos.actualizado_en:raise ErrorProducto(409,'cuenta_modificada','Actualiza las cuentas antes de guardar.')
        fila=db.execute('UPDATE broquer.fin_cuentas SET activa=%s,actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(datos.activa,identificador)).fetchone()
        auditar(db,ctx,'cuenta_activada' if datos.activa else 'cuenta_desactivada',identificador);return seguro(fila)

@router.get('/categorias')
def categorias(ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    with transaccion(ctx.usuario_id) as db:return {'categorias':db.execute('SELECT id,nombre,tipo FROM broquer.fin_categorias WHERE org_id=%s ORDER BY tipo,nombre,id',(ctx.org_id,)).fetchall()}

@router.post('/categorias/inicializar')
def inicializar(ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    with transaccion(ctx.usuario_id) as db:
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(str(ctx.org_id)+':finanzas:'+str(ctx.usuario_id),))
        for c in SEMILLAS:
            db.execute('INSERT INTO broquer.fin_categorias(org_id,creado_por,nombre,tipo,clave) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(ctx.org_id,ctx.usuario_id,c['nombre'],c['tipo'],c['clave']))
    return categorias(ctx)

@router.post('/categorias',status_code=201)
def crear_categoria(datos:Categoria,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    try:
        with transaccion(ctx.usuario_id) as db:return db.execute('INSERT INTO broquer.fin_categorias(org_id,creado_por,nombre,tipo) VALUES(%s,%s,%s,%s) RETURNING id,nombre,tipo',(ctx.org_id,ctx.usuario_id,datos.nombre,datos.tipo)).fetchone()
    except UniqueViolation:raise ErrorProducto(409,'categoria_duplicada','Ya existe esa categoría para este tipo de movimiento.')

@router.post('/movimientos',status_code=201)
def crear_movimiento(datos:Movimiento,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    huella=hashlib.sha256(json.dumps(datos.model_dump(mode='json',exclude={'idempotencia'}),sort_keys=True).encode()).hexdigest()
    with transaccion(ctx.usuario_id) as db:
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(str(ctx.org_id)+':fin:'+str(ctx.usuario_id)+':'+str(datos.idempotencia),))
        previo=db.execute('SELECT * FROM broquer.fin_movimientos WHERE org_id=%s AND creado_por=%s AND idempotencia=%s',(ctx.org_id,ctx.usuario_id,datos.idempotencia)).fetchone()
        if previo:
            if previo['huella']!=huella:raise ErrorProducto(409,'solicitud_distinta','El intento anterior tenía otros datos. Revisa los movimientos antes de iniciar otro registro.')
            return seguro({k:v for k,v in previo.items() if k not in ('huella','idempotencia')})
        ids=[datos.cuenta_id]+([datos.cuenta_destino_id] if datos.cuenta_destino_id else [])
        cs=db.execute('SELECT * FROM broquer.fin_cuentas WHERE org_id=%s AND id=ANY(%s) ORDER BY id FOR SHARE',(ctx.org_id,ids)).fetchall()
        if len(cs)!=len(ids) or any(not c['activa'] for c in cs):raise ErrorProducto(422,'cuenta_invalida','Selecciona cuentas activas de tu espacio.')
        monedas={c['moneda'] for c in cs}
        if len(monedas)!=1:raise ErrorProducto(422,'moneda_distinta','La transferencia requiere cuentas de la misma moneda.')
        moneda=cs[0]['moneda']
        if datos.categoria_id and not db.execute('SELECT id FROM broquer.fin_categorias WHERE org_id=%s AND id=%s AND tipo=%s',(ctx.org_id,datos.categoria_id,datos.tipo)).fetchone():
            raise ErrorProducto(422,'categoria_invalida','Selecciona una categoría del tipo de movimiento.')
        for tabla,identificador,modulo in [('propiedades',datos.propiedad_id,'inmuebles'),('contactos',datos.contacto_id,'directorio')]:
            if identificador:
                exigir(ctx,modulo)
                if not db.execute('SELECT id FROM broquer.'+tabla+' WHERE id=%s AND org_id=%s AND archivado_en IS NULL',(identificador,ctx.org_id)).fetchone():
                    raise ErrorProducto(404,'vinculo_no_encontrado','No encontramos el registro que deseas vincular.')
        fila=db.execute('''INSERT INTO broquer.fin_movimientos(org_id,creado_por,tipo,monto,moneda,fecha,concepto,notas,cuenta_id,cuenta_destino_id,categoria_id,propiedad_id,contacto_id,idempotencia,huella)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(ctx.org_id,ctx.usuario_id,datos.tipo,datos.monto,moneda,datos.fecha,datos.concepto,datos.notas,datos.cuenta_id,datos.cuenta_destino_id,datos.categoria_id,datos.propiedad_id,datos.contacto_id,datos.idempotencia,huella)).fetchone()
        auditar(db,ctx,'movimiento_registrado',fila['id'])
        return seguro({k:v for k,v in fila.items() if k not in ('huella','idempotencia')})

@router.patch('/movimientos/{identificador}/anular')
def anular(identificador:UUID,datos:Anulacion,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    with transaccion(ctx.usuario_id) as db:
        fila=db.execute('SELECT * FROM broquer.fin_movimientos WHERE id=%s AND org_id=%s FOR UPDATE',(identificador,ctx.org_id)).fetchone()
        if not fila:raise ErrorProducto(404,'movimiento_no_encontrado','No encontramos ese movimiento.')
        if fila['anulada_en']:return {'anulado':True}
        if fila['actualizado_en']!=datos.actualizado_en:raise ErrorProducto(409,'movimiento_modificado','Actualiza los movimientos antes de anular.')
        db.execute('UPDATE broquer.fin_movimientos SET anulada_en=clock_timestamp(),motivo_anulacion=%s,actualizado_en=clock_timestamp() WHERE id=%s',(datos.motivo,identificador))
        auditar(db,ctx,'movimiento_anulado',identificador);return {'anulado':True}

@router.get('/movimientos')
def movimientos(desde:date,hasta:date,cuenta_id:UUID|None=None,offset:int=Query(default=0,ge=0,le=100000),limite:int=Query(default=50,ge=1,le=100),ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    if hasta<desde or (hasta-desde).days>3660:raise ErrorProducto(422,'periodo_invalido','Elige un periodo válido de hasta diez años.')
    where='m.org_id=%s AND m.fecha BETWEEN %s AND %s AND (%s::uuid IS NULL OR m.cuenta_id=%s OR m.cuenta_destino_id=%s)'
    params=(ctx.org_id,desde,hasta,cuenta_id,cuenta_id,cuenta_id)
    with transaccion(ctx.usuario_id) as db:
        resumen=db.execute('''SELECT m.moneda,COALESCE(sum(m.monto) FILTER(WHERE m.tipo='ingreso'),0) AS ingresos,
         COALESCE(sum(m.monto) FILTER(WHERE m.tipo='gasto'),0) AS gastos FROM broquer.fin_movimientos m WHERE '''+where+' AND m.anulada_en IS NULL GROUP BY m.moneda',params).fetchall()
        filas=db.execute('''SELECT m.id,m.tipo,m.monto,m.moneda,m.fecha,m.concepto,m.notas,m.cuenta_id,m.cuenta_destino_id,m.categoria_id,m.propiedad_id,m.contacto_id,
         m.anulada_en,m.motivo_anulacion,m.actualizado_en,c.nombre AS cuenta_nombre,d.nombre AS destino_nombre,k.nombre AS categoria_nombre,ct.nombre AS contacto_nombre
         FROM broquer.fin_movimientos m JOIN broquer.fin_cuentas c ON c.id=m.cuenta_id AND c.org_id=m.org_id
         LEFT JOIN broquer.fin_cuentas d ON d.id=m.cuenta_destino_id AND d.org_id=m.org_id
         LEFT JOIN broquer.fin_categorias k ON k.id=m.categoria_id AND k.org_id=m.org_id LEFT JOIN broquer.contactos ct ON ct.id=m.contacto_id AND ct.org_id=m.org_id WHERE '''+where+' ORDER BY m.fecha DESC,m.creado_en DESC,m.id LIMIT %s OFFSET %s',(*params,limite+1,offset)).fetchall()
        return seguro({'movimientos':filas[:limite],'hay_mas':len(filas)>limite,'resumen':[{**r,'resultado':r['ingresos']-r['gastos']} for r in resumen]})


class NombreCategoria(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    nombre:str=Field(min_length=1,max_length=100)
    nombre_anterior:str=Field(min_length=1,max_length=100)

@router.patch('/categorias/{identificador}')
def renombrar_categoria(identificador:UUID,datos:NombreCategoria,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    try:
        with transaccion(ctx.usuario_id) as db:
            fila=db.execute('SELECT * FROM broquer.fin_categorias WHERE id=%s AND org_id=%s FOR UPDATE',(identificador,ctx.org_id)).fetchone()
            if not fila:raise ErrorProducto(404,'categoria_no_encontrada','No encontramos esa categoría.')
            if fila['nombre']!=datos.nombre_anterior:raise ErrorProducto(409,'categoria_modificada','Actualiza las categorías antes de guardar.')
            fila=db.execute('UPDATE broquer.fin_categorias SET nombre=%s WHERE id=%s RETURNING id,nombre,tipo',(datos.nombre,identificador)).fetchone()
            auditar(db,ctx,'categoria_renombrada',identificador);return fila
    except UniqueViolation:raise ErrorProducto(409,'categoria_duplicada','Ya existe esa categoría para este tipo de movimiento.')


def filtro_periodo(ctx,desde,hasta,cuenta_id):
    if hasta<desde or (hasta-desde).days>3660:
        raise ErrorProducto(422,'periodo_invalido','Elige un periodo válido de hasta diez años.')
    return ('m.org_id=%s AND m.fecha BETWEEN %s AND %s AND (%s::uuid IS NULL OR m.cuenta_id=%s OR m.cuenta_destino_id=%s)',
            (ctx.org_id,desde,hasta,cuenta_id,cuenta_id,cuenta_id))


@router.get('/reporte')
def reporte(desde:date,hasta:date,agrupacion:Literal['mes','categoria','inmueble']='mes',cuenta_id:UUID|None=None,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    where,params=filtro_periodo(ctx,desde,hasta,cuenta_id)
    # Expressions are from this fixed allowlist; no user input is interpolated into SQL.
    clave,nombre,union={
        'mes':("to_char(m.fecha,'YYYY-MM')","to_char(m.fecha,'YYYY-MM')",''),
        'categoria':("COALESCE(k.id::text,'sin_categoria')","COALESCE(k.nombre,'Sin categoría')",'LEFT JOIN broquer.fin_categorias k ON k.id=m.categoria_id AND k.org_id=m.org_id'),
        'inmueble':("COALESCE(p.id::text,'sin_inmueble')","COALESCE(p.titulo,'Sin inmueble visible')",'LEFT JOIN broquer.propiedades p ON p.id=m.propiedad_id AND p.org_id=m.org_id'),
    }[agrupacion]
    with transaccion(ctx.usuario_id) as db:
        filas=db.execute(f'''SELECT {clave} AS clave,{nombre} AS nombre,m.moneda,
          COALESCE(sum(m.monto) FILTER(WHERE m.tipo='ingreso'),0) AS ingresos,
          COALESCE(sum(m.monto) FILTER(WHERE m.tipo='gasto'),0) AS gastos,count(*) AS movimientos
          FROM broquer.fin_movimientos m {union} WHERE {where}
          AND m.anulada_en IS NULL AND m.tipo IN ('ingreso','gasto')
          GROUP BY 1,2,3 ORDER BY 1,3 LIMIT 5001''',params).fetchall()
        if len(filas)>5000:raise ErrorProducto(422,'reporte_extenso','Reduce el periodo o selecciona una cuenta para generar el reporte.')
        return seguro({'grupos':[{**r,'resultado':r['ingresos']-r['gastos']} for r in filas]})


def csv_periodo(filas):
    import csv
    import io
    salida=io.StringIO(newline='')
    escritor=csv.writer(salida)
    escritor.writerow(['Fecha','Tipo','Concepto','Monto','Moneda','Cuenta','Destino','Categoría','Estado'])
    def celda(valor):
        texto=str(valor or '')
        return "'"+texto if texto.lstrip().startswith(('=','+','-','@')) or texto.startswith(('\t','\r','\n')) else texto
    for m in filas:
        escritor.writerow([celda(x) for x in [m['fecha'],m['tipo'],m['concepto'],m['monto'],m['moneda'],m['cuenta_nombre'],m['destino_nombre'],m['categoria_nombre'],'Anulado' if m['anulada_en'] else 'Vigente']])
    return '\ufeff'+salida.getvalue()


@router.get('/exportacion')
def exportacion(desde:date,hasta:date,cuenta_id:UUID|None=None,ctx=Depends(contexto)):
    exigir(ctx,'finanzas')
    where,params=filtro_periodo(ctx,desde,hasta,cuenta_id)
    with transaccion(ctx.usuario_id) as db:
        filas=db.execute('''SELECT m.fecha,m.tipo,m.concepto,m.monto,m.moneda,m.anulada_en,
          c.nombre AS cuenta_nombre,d.nombre AS destino_nombre,k.nombre AS categoria_nombre
          FROM broquer.fin_movimientos m JOIN broquer.fin_cuentas c ON c.id=m.cuenta_id AND c.org_id=m.org_id
          LEFT JOIN broquer.fin_cuentas d ON d.id=m.cuenta_destino_id AND d.org_id=m.org_id
          LEFT JOIN broquer.fin_categorias k ON k.id=m.categoria_id AND k.org_id=m.org_id
          WHERE '''+where+' ORDER BY m.fecha DESC,m.creado_en DESC,m.id LIMIT 10001',params).fetchall()
        if len(filas)>10000:raise ErrorProducto(422,'exportacion_extensa','El periodo supera 10,000 movimientos. Reduce las fechas o selecciona una cuenta; no se exportaron datos parciales.')
        return {'csv':csv_periodo(filas),'cantidad':len(filas)}
