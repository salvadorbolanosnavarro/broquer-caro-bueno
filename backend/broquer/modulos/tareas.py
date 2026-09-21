from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, AwareDatetime
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.errores import ErrorProducto
from ..core.permisos import exigir

router=APIRouter(prefix='/v1/tareas')

class DatosTarea(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    titulo:str=Field(min_length=1,max_length=160)
    tipo:Literal['llamada','visita','cita','seguimiento','tramite','otro']='seguimiento'
    inicio_local:datetime
    duracion_min:int=Field(default=30,ge=5,le=1440,strict=True)
    descripcion:str=Field(default='',max_length=4000)
    ubicacion:str=Field(default='',max_length=300)

    @field_validator('inicio_local')
    @classmethod
    def hora_local(cls,v):
        if v.tzinfo is not None:raise ValueError('Usa la hora local de la organización.')
        if not 2000<=v.year<=2100:raise ValueError('Fecha fuera de rango.')
        return v

class NuevaTarea(DatosTarea):
    oportunidad_id:UUID|None=None
    propiedad_id:UUID|None=None

class EditarTarea(DatosTarea):
    actualizado_en:AwareDatetime

class EstadoTarea(BaseModel):
    model_config=ConfigDict(extra='forbid')
    completada:bool=Field(strict=True)
    actualizado_en:AwareDatetime


def convertir_hora(local:datetime,zona:str):
    tz=ZoneInfo(zona)
    candidatos=set()
    for fold in (0,1):
        utc=local.replace(tzinfo=tz,fold=fold).astimezone(timezone.utc)
        if utc.astimezone(tz).replace(tzinfo=None)==local:candidatos.add(utc)
    if len(candidatos)!=1:
        raise ErrorProducto(422,'hora_no_valida','Esa hora coincide con un cambio de horario. Elige otra hora.')
    return candidatos.pop()


def zona_org(db,ctx):
    return db.execute('SELECT zona_horaria FROM broquer.organizaciones WHERE id=%s',(ctx.org_id,)).fetchone()['zona_horaria']


def obtener(db,ctx,identificador):
    fila=db.execute('SELECT * FROM broquer.tareas WHERE id=%s AND org_id=%s FOR UPDATE',(identificador,ctx.org_id)).fetchone()
    if not fila:raise ErrorProducto(404,'tarea_no_encontrada','No encontramos esa tarea.')
    return fila


def version(fila,esperada):
    if fila['actualizado_en']!=esperada:raise ErrorProducto(409,'tarea_modificada','La tarea cambió. Actualiza la agenda antes de guardar.')


def evento(db,ctx,tarea,tipo,texto):
    if tarea['oportunidad_id'] or tarea['propiedad_id']:
        db.execute('INSERT INTO broquer.actividades(org_id,oportunidad_id,propiedad_id,tarea_id,creado_por,tipo,texto) VALUES(%s,%s,%s,%s,%s,%s,%s)',(ctx.org_id,tarea['oportunidad_id'],tarea['propiedad_id'],tarea['id'],ctx.usuario_id,tipo,texto))
    db.execute('INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(%s,%s,%s,%s)',(ctx.org_id,ctx.usuario_id,tipo,tarea['id']))


def conflictos(db,ctx,inicio,duracion,identificador=None):
    return db.execute('''SELECT id,titulo,inicio FROM broquer.tareas WHERE org_id=%s AND asignado_a=%s
      AND completada_en IS NULL AND (%s::uuid IS NULL OR id<>%s::uuid)
      AND inicio < %s AND inicio + duracion_min * interval '1 minute' > %s ORDER BY inicio LIMIT 10''',
      (ctx.org_id,ctx.usuario_id,identificador,identificador,inicio+timedelta(minutes=duracion),inicio)).fetchall()

@router.get('')
def listar(limite:int=Query(default=200,ge=1,le=500),ctx=Depends(contexto)):
    exigir(ctx,'agenda')
    with transaccion(ctx.usuario_id) as db:
        zona=zona_org(db,ctx)
        filas=db.execute('''SELECT t.*,o.titulo AS oportunidad_titulo,p.titulo AS propiedad_titulo FROM broquer.tareas t
          LEFT JOIN broquer.oportunidades o ON o.id=t.oportunidad_id AND o.org_id=t.org_id
          LEFT JOIN broquer.propiedades p ON p.id=t.propiedad_id AND p.org_id=t.org_id
          WHERE t.org_id=%s ORDER BY (t.completada_en IS NOT NULL),t.inicio,t.id LIMIT %s''',(ctx.org_id,limite+1)).fetchall()
    return {'tareas':filas[:limite],'hay_mas':len(filas)>limite,'zona_horaria':zona}

@router.post('',status_code=201)
def crear(datos:NuevaTarea,ctx=Depends(contexto)):
    exigir(ctx,'agenda')
    with transaccion(ctx.usuario_id) as db:
        if datos.oportunidad_id:
            exigir(ctx,'clientes')
            if not db.execute('SELECT id FROM broquer.oportunidades WHERE id=%s AND org_id=%s',(datos.oportunidad_id,ctx.org_id)).fetchone():
                raise ErrorProducto(404,'oportunidad_no_encontrada','No encontramos esa oportunidad.')
        if datos.propiedad_id:
            exigir(ctx,'inmuebles')
            if not db.execute('SELECT id FROM broquer.propiedades WHERE id=%s AND org_id=%s AND archivado_en IS NULL AND broquer.puede_editar_propiedad(id)',(datos.propiedad_id,ctx.org_id)).fetchone():
                raise ErrorProducto(404,'inmueble_no_encontrado','Elige un inmueble activo que puedas editar.')
        inicio=convertir_hora(datos.inicio_local,zona_org(db,ctx))
        choques=conflictos(db,ctx,inicio,datos.duracion_min)
        fila=db.execute('''INSERT INTO broquer.tareas(org_id,creado_por,asignado_a,oportunidad_id,propiedad_id,titulo,tipo,inicio,duracion_min,descripcion,ubicacion)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(ctx.org_id,ctx.usuario_id,ctx.usuario_id,datos.oportunidad_id,datos.propiedad_id,datos.titulo,datos.tipo,inicio,datos.duracion_min,datos.descripcion,datos.ubicacion)).fetchone()
        evento(db,ctx,fila,'tarea_creada','Tarea creada: '+fila['titulo'])
    return {'tarea':fila,'conflictos':choques}

@router.patch('/{identificador}')
def editar(identificador:UUID,datos:EditarTarea,ctx=Depends(contexto)):
    exigir(ctx,'agenda')
    with transaccion(ctx.usuario_id) as db:
        fila=obtener(db,ctx,identificador);version(fila,datos.actualizado_en)
        inicio=convertir_hora(datos.inicio_local,zona_org(db,ctx))
        choques=conflictos(db,ctx,inicio,datos.duracion_min,identificador)
        fila=db.execute('''UPDATE broquer.tareas SET titulo=%s,tipo=%s,inicio=%s,duracion_min=%s,descripcion=%s,ubicacion=%s,actualizado_en=clock_timestamp()
          WHERE id=%s RETURNING *''',(datos.titulo,datos.tipo,inicio,datos.duracion_min,datos.descripcion,datos.ubicacion,identificador)).fetchone()
        evento(db,ctx,fila,'sistema','Tarea actualizada: '+fila['titulo'])
    return {'tarea':fila,'conflictos':choques}

@router.patch('/{identificador}/estado')
def estado(identificador:UUID,datos:EstadoTarea,ctx=Depends(contexto)):
    exigir(ctx,'agenda')
    with transaccion(ctx.usuario_id) as db:
        fila=obtener(db,ctx,identificador);version(fila,datos.actualizado_en)
        if bool(fila['completada_en'])==datos.completada:return fila
        fila=db.execute('UPDATE broquer.tareas SET completada_en=CASE WHEN %s THEN clock_timestamp() ELSE NULL END,actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(datos.completada,identificador)).fetchone()
        evento(db,ctx,fila,'tarea_completada' if datos.completada else 'sistema',('Tarea completada: ' if datos.completada else 'Tarea reabierta: ')+fila['titulo'])
    return fila
