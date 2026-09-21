from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError
from broquer.modulos.inmuebles import DatosInmueble,Edicion,Operacion,puede_editar
from broquer.core.permisos import Contexto
BASE={'titulo':'Casa de prueba','tipo':'casa','colonia':'Altozano','municipio':'Morelia','estado':'Michoacán','operaciones':[{'operacion':'venta','precio':'3850000','moneda':'MXN'}]}

def test_dos_operaciones_y_decimales():
    d=DatosInmueble(**{**BASE,'m2_construccion':'245.75','banos':'3.5','operaciones':BASE['operaciones']+[{'operacion':'renta','precio':'22500.50','moneda':'MXN'}]})
    assert d.m2_construccion==Decimal('245.75') and d.banos==Decimal('3.5')
    assert d.operaciones[1].precio==Decimal('22500.50')

@pytest.mark.parametrize('cambio',[{'titulo':'   '},{'colonia':''},{'municipio':''},{'estado':''},{'tipo':'penthouse'},{'cp':'abcde'},{'m2_terreno':'-1'},{'m2_construccion':'5.555'},{'banos':'3.55'},{'recamaras':True},{'recamaras':2.5},{'operaciones':[]},{'operaciones':BASE['operaciones']*2},{'org_id':str(uuid4())},{'asignado_a':str(uuid4())},{'estatus':'vendida'}])
def test_validacion(cambio):
    with pytest.raises(ValidationError):DatosInmueble(**{**BASE,**cambio})

@pytest.mark.parametrize('precio',['0','-1','NaN','Infinity','0.001','100000000000000'])
def test_precio_invalido(precio):
    with pytest.raises(ValidationError):Operacion(operacion='venta',precio=precio)

def test_edicion_requiere_version():
    with pytest.raises(ValidationError):Edicion(**BASE)

def test_permiso_edicion_ajena():
    uid,ajeno,org=uuid4(),uuid4(),uuid4();fila={'creado_por':ajeno,'asignado_a':ajeno}
    assert not puede_editar(fila,Contexto(uid,org,'agente'))
    assert puede_editar(fila,Contexto(uid,org,'agente',permisos={'editar_registros_ajenos':True}))
