from dataclasses import dataclass, field
from uuid import UUID
from .errores import ErrorProducto
BASE={'ver_telefonos':False,'ver_comisiones':False,'ver_inventario_completo':True,'ver_contactos_equipo':True,'exportar':True,'ver_estadisticas_equipo':False,'gestionar_integraciones':False,'eliminar_registros':False,'editar_registros_ajenos':False}
@dataclass(frozen=True)
class Contexto:
    usuario_id:UUID
    org_id:UUID
    rol_org:str
    plan:str='gratis'
    permisos:dict=field(default_factory=dict)
    modulos_desactivados:tuple=()
    zona_horaria:str='America/Mexico_City'
    es_staff:bool=False

def efectivos(rol:str,tipo:str,overrides:dict):
    if rol not in ('owner','admin','agente'): raise ErrorProducto(403,'rol_invalido','No tienes acceso a esta organización.')
    if rol in ('owner','admin'):return {p:True for p in BASE}
    permisos={**BASE,'eliminar_registros':tipo=='personal'}
    permisos.update({k:v for k,v in overrides.items() if k in BASE and type(v) is bool})
    return permisos

def exigir(ctx:Contexto,modulo:str,permiso:str|None=None):
    if modulo in ctx.modulos_desactivados:raise ErrorProducto(403,'modulo_desactivado','Esta herramienta no está habilitada para tu cuenta.')
    if permiso and not ctx.permisos.get(permiso,False):raise ErrorProducto(403,'sin_permiso','No tienes permiso para esta acción.')
