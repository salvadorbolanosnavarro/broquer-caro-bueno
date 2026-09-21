from datetime import datetime
from uuid import UUID
import re
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from psycopg.errors import UniqueViolation
from ..core.auth import contexto
from ..core.base import transaccion
from ..core.errores import ErrorProducto
from ..core.permisos import exigir
router=APIRouter(prefix='/v1/contactos')


def telefono_normalizado(valor):
    if not valor:return None
    valor=re.sub(r'[\s().-]','',valor)
    if re.fullmatch(r'(?:\+?521)\d{10}',valor):valor='+52'+valor[-10:]
    elif re.fullmatch(r'\d{10}',valor):valor='+52'+valor
    if not re.fullmatch(r'\+[1-9]\d{7,14}',valor):raise ValueError('Teléfono inválido')
    return valor

class Contacto(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    nombre:str=Field(min_length=1,max_length=160)
    empresa:str=Field(default='',max_length=160)
    telefono:str|None=None
    email:EmailStr|None=None
    _telefono=field_validator('telefono',mode='before')(telefono_normalizado)
    @model_validator(mode='after')
    def canal(self):
        if not self.telefono and not self.email:raise ValueError('Se requiere teléfono o email')
        return self

class Cambio(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    actualizado_en:datetime
    nombre:str|None=Field(default=None,min_length=1,max_length=160)
    empresa:str|None=Field(default=None,max_length=160)
    telefono:str|None=None
    email:EmailStr|None=None
    _telefono=field_validator('telefono',mode='before')(telefono_normalizado)

def visible(fila,ctx):
    propia=fila['creado_por']==ctx.usuario_id or fila['asignado_a']==ctx.usuario_id
    editar=propia or ctx.permisos.get('editar_registros_ajenos',False)
    ver=propia or ctx.permisos.get('ver_telefonos',False)
    return {**fila,'telefono':fila['telefono'] if ver else ('••••'+fila['telefono'][-4:] if fila['telefono'] else None),'puede_editar':editar,'puede_ver_telefono':ver}

@router.get('')
def listar(q:str=Query(default='',max_length=160),limite:int=Query(default=50,ge=1,le=100),ctx=Depends(contexto)):
    exigir(ctx,'directorio')
    patron='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
    with transaccion(ctx.usuario_id) as db:
        # Never allow searching masked telephone values to infer private numbers.
        filas=db.execute('''SELECT * FROM broquer.contactos WHERE org_id=%s AND archivado_en IS NULL
          AND (nombre ILIKE %s OR empresa ILIKE %s OR email ILIKE %s OR
          ((creado_por=%s OR asignado_a=%s OR %s) AND telefono ILIKE %s))
          ORDER BY nombre,id LIMIT %s''',(ctx.org_id,patron,patron,patron,ctx.usuario_id,ctx.usuario_id,ctx.permisos.get('ver_telefonos',False),patron,limite+1)).fetchall()
    return {'contactos':[visible(f,ctx) for f in filas[:limite]],'hay_mas':len(filas)>limite}

@router.post('',status_code=201)
def crear(datos:Contacto,ctx=Depends(contexto)):
    exigir(ctx,'directorio')
    try:
        with transaccion(ctx.usuario_id) as db:
            fila=db.execute('''INSERT INTO broquer.contactos(org_id,creado_por,asignado_a,nombre,empresa,telefono,email)
             VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(ctx.org_id,ctx.usuario_id,ctx.usuario_id,datos.nombre,datos.empresa,datos.telefono,str(datos.email).lower() if datos.email else None)).fetchone()
            db.execute("INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(%s,%s,'contacto_creado',%s)",(ctx.org_id,ctx.usuario_id,fila['id']))
    except UniqueViolation:raise ErrorProducto(409,'contacto_duplicado','Ya existe un contacto con ese teléfono o correo en tu organización.')
    return visible(fila,ctx)

@router.patch('/{contacto_id}')
def editar(contacto_id:UUID,datos:Cambio,ctx=Depends(contexto)):
    exigir(ctx,'directorio')
    try:
        with transaccion(ctx.usuario_id) as db:
            fila=db.execute('SELECT * FROM broquer.contactos WHERE id=%s AND org_id=%s AND archivado_en IS NULL FOR UPDATE',(contacto_id,ctx.org_id)).fetchone()
            if not fila:raise ErrorProducto(404,'contacto_no_encontrado','No encontramos ese contacto.')
            if not visible(fila,ctx)['puede_editar']:raise ErrorProducto(403,'sin_permiso','No tienes permiso para editar este contacto.')
            if datos.actualizado_en!=fila['actualizado_en']:raise ErrorProducto(409,'contacto_modificado','El contacto cambió. Vuelve a cargarlo antes de guardar.')
            cambios=datos.model_dump(exclude_unset=True,exclude={'actualizado_en'})
            if not cambios:raise ErrorProducto(422,'sin_cambios','No hay cambios para guardar.')
            completo=Contacto(**{k:cambios.get(k,fila[k]) for k in ['nombre','empresa','telefono','email']})
            valores=completo.model_dump()
            if valores['email']:valores['email']=valores['email'].lower()
            fila=db.execute('UPDATE broquer.contactos SET '+','.join(k+'=%s' for k in cambios)+',actualizado_en=clock_timestamp() WHERE id=%s RETURNING *',(*[valores[k] for k in cambios],contacto_id)).fetchone()
            db.execute("INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(%s,%s,'contacto_editado',%s)",(ctx.org_id,ctx.usuario_id,contacto_id))
    except UniqueViolation:raise ErrorProducto(409,'contacto_duplicado','Ya existe un contacto con ese teléfono o correo en tu organización.')
    except ValueError:raise ErrorProducto(422,'datos_invalidos','Revisa los datos y conserva al menos un teléfono o correo.')
    return visible(fila,ctx)
