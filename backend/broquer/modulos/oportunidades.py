from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID
import json
import hashlib
from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,ConfigDict,Field,model_validator
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.errores import ErrorProducto
from ..core.permisos import exigir
router=APIRouter(prefix='/v1/crm')
ETAPAS=json.loads((Path(__file__).resolve().parents[3]/'shared/etapas.json').read_text())
class Nueva(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    contacto_id:UUID
    etapa_id:UUID
    titulo:str=Field(min_length=1,max_length=160)
    tipo:Literal['compra','renta','venta','arrendamiento']='compra'
    presupuesto:Decimal|None=Field(default=None,ge=0,max_digits=16,decimal_places=2)
    moneda:Literal['MXN','USD']='MXN'
    zona:str=Field(default='',max_length=160)
    temperatura:Literal['nuevo','frio','tibio','caliente']='nuevo'
class Movimiento(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    etapa_id:UUID
    actualizado_en:datetime
    motivo:str|None=Field(default=None,max_length=1000)

def revision_etapas(filas):
    return hashlib.sha256(json.dumps([{k:str(e[k]) for k in ('id','nombre','tipo','orden')} for e in filas],sort_keys=True,ensure_ascii=False).encode()).hexdigest()

@router.get('/etapas')
def etapas(ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    with transaccion(ctx.usuario_id) as db:
        filas=db.execute('SELECT id,nombre,tipo,orden FROM broquer.etapas WHERE org_id=%s ORDER BY orden',(ctx.org_id,)).fetchall()
        return {'etapas':filas,'revision':revision_etapas(filas),'puede_configurar':ctx.rol_org in ('owner','admin')}

class EtapaConfigurada(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    id:UUID|None=None
    nombre:str=Field(min_length=1,max_length=80)
    tipo:Literal['abierta','ganada','perdida']='abierta'
class ConfigurarEtapas(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    etapas:list[EtapaConfigurada]=Field(min_length=3,max_length=50)
    @model_validator(mode='after')
    def validar(self):
        if len({e.nombre.casefold() for e in self.etapas})!=len(self.etapas):raise ValueError('Nombres repetidos')
        ids=[e.id for e in self.etapas if e.id]
        if len(set(ids))!=len(ids):raise ValueError('Etapas repetidas')
        if {e.tipo for e in self.etapas}!={'abierta','ganada','perdida'}:raise ValueError('Conserva los tres tipos')
        return self

@router.patch('/etapas')
def configurar_etapas(datos:ConfigurarEtapas,ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    if ctx.rol_org not in ('owner','admin'):raise ErrorProducto(403,'sin_permiso','Solo el administrador puede configurar las etapas.')
    with transaccion(ctx.usuario_id) as db:
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(str(ctx.org_id)+':etapas',))
        actuales=db.execute('SELECT id,nombre,tipo,orden FROM broquer.etapas WHERE org_id=%s ORDER BY orden FOR UPDATE',(ctx.org_id,)).fetchall()
        if revision_etapas(actuales)!=datos.revision:raise ErrorProducto(409,'etapas_modificadas','Las etapas cambiaron. Vuelve a abrir la configuración.')
        por_id={e['id']:e for e in actuales}
        if {e.id for e in datos.etapas if e.id}!=set(por_id):raise ErrorProducto(422,'etapas_invalidas','Conserva todas las etapas existentes para mantener su historial.')
        if any(e.id and e.tipo!=por_id[e.id]['tipo'] for e in datos.etapas):raise ErrorProducto(422,'tipo_inmutable','El tipo de una etapa existente no se puede cambiar.')
        # Move current rows above the occupied range before assigning final order.
        salto=max([e['orden'] for e in actuales]+[0])+len(datos.etapas)+1
        db.execute('UPDATE broquer.etapas SET orden=orden+%s WHERE org_id=%s',(salto,ctx.org_id))
        for orden,e in enumerate(datos.etapas):
            if e.id:db.execute('UPDATE broquer.etapas SET nombre=%s,orden=%s WHERE id=%s AND org_id=%s',(e.nombre,orden,e.id,ctx.org_id))
            else:db.execute('INSERT INTO broquer.etapas(org_id,nombre,tipo,orden) VALUES(%s,%s,%s,%s)',(ctx.org_id,e.nombre,e.tipo,orden))
        db.execute("INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(%s,%s,'etapas_configuradas',%s)",(ctx.org_id,ctx.usuario_id,ctx.org_id))
    return etapas(ctx)

@router.post('/etapas/inicializar')
def inicializar(ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    if ctx.rol_org not in ('owner','admin'):raise ErrorProducto(403,'sin_permiso','Pide al administrador que configure las etapas.')
    with transaccion(ctx.usuario_id) as db:
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(str(ctx.org_id)+':etapas',))
        if not db.execute('SELECT id FROM broquer.etapas WHERE org_id=%s LIMIT 1',(ctx.org_id,)).fetchone():
            for orden,e in enumerate(ETAPAS):db.execute('INSERT INTO broquer.etapas(org_id,nombre,tipo,orden) VALUES(%s,%s,%s,%s)',(ctx.org_id,e['nombre'],e['tipo'],orden))
    return etapas(ctx)

@router.get('/oportunidades')
def listar(limite:int=Query(default=100,ge=1,le=200),ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    with transaccion(ctx.usuario_id) as db:
        filas=db.execute('''SELECT o.*,c.nombre AS contacto_nombre,e.nombre AS etapa_nombre,e.tipo AS etapa_tipo
          FROM broquer.oportunidades o JOIN broquer.contactos c ON c.id=o.contacto_id AND c.org_id=o.org_id
          JOIN broquer.etapas e ON e.id=o.etapa_id AND e.org_id=o.org_id WHERE o.org_id=%s ORDER BY o.actualizado_en DESC,o.id LIMIT %s''',(ctx.org_id,limite+1)).fetchall()
    return {'oportunidades':filas[:limite],'hay_mas':len(filas)>limite}

@router.post('/oportunidades',status_code=201)
def crear(datos:Nueva,ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    with transaccion(ctx.usuario_id) as db:
        c=db.execute('SELECT id FROM broquer.contactos WHERE id=%s AND org_id=%s AND archivado_en IS NULL',(datos.contacto_id,ctx.org_id)).fetchone()
        e=db.execute('SELECT id,nombre,tipo FROM broquer.etapas WHERE id=%s AND org_id=%s',(datos.etapa_id,ctx.org_id)).fetchone()
        if not c or not e:raise ErrorProducto(404,'relacion_no_encontrada','Selecciona un contacto y una etapa de tu organización.')
        if e['tipo']!='abierta':raise ErrorProducto(422,'etapa_cerrada','Crea la oportunidad en una etapa abierta.')
        fila=db.execute('''INSERT INTO broquer.oportunidades(org_id,creado_por,asignado_a,contacto_id,etapa_id,titulo,tipo,presupuesto,moneda,zona,temperatura)
         VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(ctx.org_id,ctx.usuario_id,ctx.usuario_id,datos.contacto_id,datos.etapa_id,datos.titulo,datos.tipo,datos.presupuesto,datos.moneda,datos.zona,datos.temperatura)).fetchone()
        db.execute('INSERT INTO broquer.historial_etapas(org_id,oportunidad_id,creado_por,nueva_id) VALUES(%s,%s,%s,%s)',(ctx.org_id,fila['id'],ctx.usuario_id,e['id']))
        db.execute("INSERT INTO broquer.actividades(org_id,oportunidad_id,creado_por,tipo,texto) VALUES(%s,%s,%s,'sistema',%s)",(ctx.org_id,fila['id'],ctx.usuario_id,'Oportunidad creada · '+e['nombre']))
    return fila

@router.patch('/oportunidades/{identificador}/etapa')
def mover(identificador:UUID,datos:Movimiento,ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    with transaccion(ctx.usuario_id) as db:
        o=db.execute('SELECT * FROM broquer.oportunidades WHERE id=%s AND org_id=%s FOR UPDATE',(identificador,ctx.org_id)).fetchone()
        if not o:raise ErrorProducto(404,'oportunidad_no_encontrada','No encontramos esa oportunidad.')
        if o['actualizado_en']!=datos.actualizado_en:raise ErrorProducto(409,'oportunidad_modificada','La oportunidad cambió. Actualiza el tablero antes de guardar.')
        e=db.execute('SELECT * FROM broquer.etapas WHERE id=%s AND org_id=%s',(datos.etapa_id,ctx.org_id)).fetchone()
        if not e:raise ErrorProducto(404,'etapa_no_encontrada','No encontramos esa etapa.')
        if e['tipo']=='perdida' and not datos.motivo:raise ErrorProducto(422,'motivo_requerido','Indica por qué se perdió la oportunidad.')
        if e['id']==o['etapa_id']:return o
        anterior=db.execute('SELECT nombre FROM broquer.etapas WHERE id=%s',(o['etapa_id'],)).fetchone()['nombre']
        motivo=datos.motivo if e['tipo']=='perdida' else None
        fila=db.execute('UPDATE broquer.oportunidades SET etapa_id=%s,motivo_perdida=%s,actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(e['id'],motivo,identificador)).fetchone()
        db.execute('INSERT INTO broquer.historial_etapas(org_id,oportunidad_id,creado_por,anterior_id,nueva_id,motivo) VALUES(%s,%s,%s,%s,%s,%s)',(ctx.org_id,identificador,ctx.usuario_id,o['etapa_id'],e['id'],motivo))
        db.execute("INSERT INTO broquer.actividades(org_id,oportunidad_id,creado_por,tipo,texto) VALUES(%s,%s,%s,'cambio_etapa',%s)",(ctx.org_id,identificador,ctx.usuario_id,'Etapa: '+anterior+' → '+e['nombre']))
    return fila

@router.get('/oportunidades/{identificador}/actividad')
def actividad(identificador:UUID,ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    with transaccion(ctx.usuario_id) as db:
        if not db.execute('SELECT id FROM broquer.oportunidades WHERE id=%s AND org_id=%s',(identificador,ctx.org_id)).fetchone():raise ErrorProducto(404,'oportunidad_no_encontrada','No encontramos esa oportunidad.')
        return {'actividades':db.execute('SELECT id,tipo,texto,creado_en FROM broquer.actividades WHERE oportunidad_id=%s AND org_id=%s ORDER BY creado_en DESC,id LIMIT 100',(identificador,ctx.org_id)).fetchall()}


class Nota(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    texto:str=Field(min_length=1,max_length=4000)

@router.post('/oportunidades/{identificador}/actividad',status_code=201)
def agregar_nota(identificador:UUID,datos:Nota,ctx=Depends(contexto)):
    exigir(ctx,'clientes')
    with transaccion(ctx.usuario_id) as db:
        if not db.execute('SELECT id FROM broquer.oportunidades WHERE id=%s AND org_id=%s',(identificador,ctx.org_id)).fetchone():
            raise ErrorProducto(404,'oportunidad_no_encontrada','No encontramos esa oportunidad.')
        return db.execute("INSERT INTO broquer.actividades(org_id,oportunidad_id,creado_por,tipo,texto) VALUES(%s,%s,%s,'nota',%s) RETURNING id,tipo,texto,creado_en",(ctx.org_id,identificador,ctx.usuario_id,datos.texto)).fetchone()
