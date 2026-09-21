from decimal import Decimal
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from psycopg.errors import UniqueViolation
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.errores import ErrorProducto
from ..core.permisos import exigir

router=APIRouter(prefix='/v1/inmuebles')
Tipo=Literal['casa','departamento','terreno','local','oficina','bodega','nave_industrial','edificio','rancho','otro']
Estatus=Literal['disponible','en_proceso','reservada','vendida','rentada','suspendida','no_activa','borrador_whatsapp']
class Operacion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operacion:Literal['venta','renta']
    precio:Decimal=Field(gt=0,max_digits=16,decimal_places=2)
    moneda:Literal['MXN','USD']='MXN'
class DatosInmueble(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    titulo:str=Field(min_length=1,max_length=160)
    clave_interna:str|None=Field(default=None,min_length=1,max_length=40)
    tipo:Tipo
    subtipo:str=Field(default='',max_length=80)
    colonia:str=Field(min_length=1,max_length=160)
    municipio:str=Field(min_length=1,max_length=160)
    estado:str=Field(min_length=1,max_length=100)
    calle:str=Field(default='',max_length=240)
    cp:str=Field(default='',pattern=r'^(?:[0-9]{5})?$')
    m2_terreno:Decimal|None=Field(default=None,ge=0,max_digits=14,decimal_places=2)
    m2_construccion:Decimal|None=Field(default=None,ge=0,max_digits=14,decimal_places=2)
    recamaras:int|None=Field(default=None,ge=0,le=999,strict=True)
    banos:Decimal|None=Field(default=None,ge=0,le=999,max_digits=4,decimal_places=1)
    estacionamientos:int|None=Field(default=None,ge=0,le=999,strict=True)
    descripcion:str=Field(default='',max_length=10000)
    operaciones:list[Operacion]=Field(min_length=1,max_length=2)
    @model_validator(mode='after')
    def operaciones_unicas(self):
        if len({o.operacion for o in self.operaciones})!=len(self.operaciones):raise ValueError('Una operación por tipo.')
        return self
class Edicion(DatosInmueble):
    actualizado_en:AwareDatetime
class Version(BaseModel):
    model_config=ConfigDict(extra='forbid')
    actualizado_en:AwareDatetime
class CambioEstatus(Version):
    estatus:Estatus
class Archivo(Version):
    archivar:bool=Field(strict=True)
class Nota(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    texto:str=Field(min_length=1,max_length=4000)


def puede_editar(fila,ctx):
    return fila['creado_por']==ctx.usuario_id or fila['asignado_a']==ctx.usuario_id or ctx.rol_org in ('owner','admin') or ctx.permisos.get('editar_registros_ajenos',False)
def obtener(db,ctx,identificador,escritura=False):
    fila=db.execute('SELECT * FROM broquer.propiedades WHERE id=%s AND org_id=%s'+(' FOR UPDATE' if escritura else ''),(identificador,ctx.org_id)).fetchone()
    if not fila:raise ErrorProducto(404,'inmueble_no_encontrado','No encontramos ese inmueble.')
    if escritura and not puede_editar(fila,ctx):raise ErrorProducto(403,'sin_permiso','No tienes permiso para editar este inmueble.')
    return fila
def comprobar(fila,datos):
    if fila['actualizado_en']!=datos.actualizado_en:raise ErrorProducto(409,'inmueble_modificado','El inmueble cambió. Vuelve a cargarlo antes de guardar.')
def evento(db,ctx,identificador,tipo,texto):
    canonico='cambio_estatus' if tipo=='estatus' else 'nota' if tipo=='nota' else 'sistema'
    db.execute('INSERT INTO broquer.actividades(org_id,propiedad_id,creado_por,tipo,texto) VALUES(%s,%s,%s,%s,%s)',(ctx.org_id,identificador,ctx.usuario_id,canonico,texto))
def salida(db,ctx,fila):
    ops=db.execute('SELECT operacion,precio,moneda FROM broquer.propiedad_operaciones WHERE propiedad_id=%s AND org_id=%s AND activa ORDER BY operacion DESC',(fila['id'],ctx.org_id)).fetchall()
    return {**fila,'operaciones':ops,'puede_editar':puede_editar(fila,ctx),'disponible_para_ofrecer':fila['estatus']=='disponible' and fila['archivado_en'] is None}
def operaciones(db,ctx,identificador,datos):
    db.execute('UPDATE broquer.propiedad_operaciones SET activa=false WHERE propiedad_id=%s AND org_id=%s',(identificador,ctx.org_id))
    for o in datos:
        db.execute('''INSERT INTO broquer.propiedad_operaciones(org_id,propiedad_id,operacion,precio,moneda) VALUES(%s,%s,%s,%s,%s)
          ON CONFLICT(propiedad_id,operacion) DO UPDATE SET precio=EXCLUDED.precio,moneda=EXCLUDED.moneda,activa=true''',(ctx.org_id,identificador,o.operacion,o.precio,o.moneda))
def insertar(db,ctx,datos):
    campos=datos.model_dump(exclude={'operaciones'})
    # Column names only come from the validated schema, never from request keys.
    fila=db.execute('INSERT INTO broquer.propiedades(org_id,creado_por,asignado_a,'+','.join(campos)+') VALUES('+','.join(['%s']*(len(campos)+3))+') RETURNING *',(ctx.org_id,ctx.usuario_id,ctx.usuario_id,*campos.values())).fetchone()
    operaciones(db,ctx,fila['id'],datos.operaciones)
    return fila

def duplicado():return ErrorProducto(409,'clave_duplicada','Ya existe un inmueble con esa clave interna en tu organización.')

@router.get('')
def listar(q:str=Query(default='',max_length=160),estatus:Estatus|None=None,tipo:Tipo|None=None,operacion:Literal['venta','renta']|None=None,archivados:bool=False,offset:int=Query(default=0,ge=0,le=100000),limite:int=Query(default=30,ge=1,le=100),ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    patron='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
    with transaccion(ctx.usuario_id) as db:
        filas=db.execute('''SELECT p.* FROM broquer.propiedades p WHERE org_id=%s AND (archivado_en IS NOT NULL)=%s
         AND (titulo ILIKE %s OR colonia ILIKE %s OR municipio ILIKE %s OR clave_interna ILIKE %s)
         AND (%s::text IS NULL OR estatus=%s) AND (%s::text IS NULL OR tipo=%s)
         AND (%s::text IS NULL OR EXISTS(SELECT 1 FROM broquer.propiedad_operaciones o WHERE o.propiedad_id=p.id AND o.org_id=p.org_id AND o.activa AND o.operacion=%s))
         ORDER BY actualizado_en DESC,id LIMIT %s OFFSET %s''',(ctx.org_id,archivados,patron,patron,patron,patron,estatus,estatus,tipo,tipo,operacion,operacion,limite+1,offset)).fetchall()
        return {'inmuebles':[salida(db,ctx,f) for f in filas[:limite]],'hay_mas':len(filas)>limite}

@router.post('',status_code=201)
def crear(datos:DatosInmueble,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    try:
        with transaccion(ctx.usuario_id) as db:
            fila=insertar(db,ctx,datos);evento(db,ctx,fila['id'],'alta','Inmueble registrado.');return salida(db,ctx,fila)
    except UniqueViolation:raise duplicado()

@router.get('/{identificador}')
def detalle(identificador:UUID,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    with transaccion(ctx.usuario_id) as db:
        fila=salida(db,ctx,obtener(db,ctx,identificador))
        return {**fila,'historial':db.execute('SELECT id,tipo,texto,creado_en FROM broquer.actividades WHERE propiedad_id=%s AND org_id=%s ORDER BY creado_en DESC,id LIMIT 100',(identificador,ctx.org_id)).fetchall()}

@router.patch('/{identificador}')
def editar(identificador:UUID,datos:Edicion,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    try:
        with transaccion(ctx.usuario_id) as db:
            fila=obtener(db,ctx,identificador,True);comprobar(fila,datos)
            if fila['archivado_en']:raise ErrorProducto(409,'inmueble_archivado','Restaura el inmueble antes de editarlo.')
            campos=datos.model_dump(exclude={'operaciones','actualizado_en'})
            fila=db.execute('UPDATE broquer.propiedades SET '+','.join(k+'=%s' for k in campos)+',actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(*campos.values(),identificador)).fetchone()
            operaciones(db,ctx,identificador,datos.operaciones);evento(db,ctx,identificador,'edicion','Datos del inmueble actualizados.')
            return salida(db,ctx,fila)
    except UniqueViolation:raise duplicado()

@router.patch('/{identificador}/estatus')
def estatus(identificador:UUID,datos:CambioEstatus,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    with transaccion(ctx.usuario_id) as db:
        fila=obtener(db,ctx,identificador,True);comprobar(fila,datos)
        if fila['archivado_en']:raise ErrorProducto(409,'inmueble_archivado','Restaura el inmueble antes de cambiar su estatus.')
        if fila['estatus']!=datos.estatus:
            anterior=fila['estatus']
            fila=db.execute('UPDATE broquer.propiedades SET estatus=%s,estatus_cambiado_en=clock_timestamp(),actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(datos.estatus,identificador)).fetchone()
            evento(db,ctx,identificador,'estatus','Estatus: '+anterior+' → '+datos.estatus)
        return salida(db,ctx,fila)

@router.patch('/{identificador}/archivo')
def archivo(identificador:UUID,datos:Archivo,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    with transaccion(ctx.usuario_id) as db:
        fila=obtener(db,ctx,identificador,True);comprobar(fila,datos)
        if bool(fila['archivado_en'])!=datos.archivar:
            fila=db.execute('UPDATE broquer.propiedades SET archivado_en=CASE WHEN %s THEN clock_timestamp() ELSE NULL END,actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(datos.archivar,identificador)).fetchone()
            evento(db,ctx,identificador,'archivo','Inmueble archivado.' if datos.archivar else 'Inmueble restaurado.')
        return salida(db,ctx,fila)

@router.post('/{identificador}/duplicar',status_code=201)
def duplicar(identificador:UUID,datos:Version,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    with transaccion(ctx.usuario_id) as db:
        original=obtener(db,ctx,identificador,True);comprobar(original,datos)
        origen=salida(db,ctx,original)
        datos_nuevos=DatosInmueble(**{**{k:origen[k] for k in DatosInmueble.model_fields},'clave_interna':None,'titulo':origen['titulo'][:152]+' (copia)'})
        copia=insertar(db,ctx,datos_nuevos);evento(db,ctx,copia['id'],'duplicado','Copia creada de '+original['titulo'])
        return salida(db,ctx,copia)

@router.post('/{identificador}/notas',status_code=201)
def nota(identificador:UUID,datos:Nota,ctx=Depends(contexto)):
    exigir(ctx,'inmuebles')
    with transaccion(ctx.usuario_id) as db:
        obtener(db,ctx,identificador,True);evento(db,ctx,identificador,'nota',datos.texto)
    return {'guardada':True}
