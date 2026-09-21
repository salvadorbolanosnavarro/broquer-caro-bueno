import json
from pathlib import Path
from fastapi import APIRouter,Depends
from ..core.auth import contexto
router=APIRouter(prefix='/v1')
CATALOGO=json.loads((Path(__file__).resolve().parents[3]/'shared/modulos.json').read_text())
@router.get('/me/modulos')
def modulos(ctx=Depends(contexto)):
    return {'modulos':[{'clave':m['clave'],'nombre':m['nombre'],'grupo':m['grupo'],'descripcion':m['descripcion'],'estado':'desactivado_por_admin' if m['clave'] in ctx.modulos_desactivados else 'disponible' if m['clave'] in ('agenda','clientes','directorio','inmuebles','finanzas') else 'proximamente'} for m in CATALOGO]}
