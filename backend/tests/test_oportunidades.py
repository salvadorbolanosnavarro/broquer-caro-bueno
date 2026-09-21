from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError
from broquer.modulos.oportunidades import Nueva,Movimiento

@pytest.mark.parametrize('valor',['-1','1.001','100000000000000.00','NaN','Infinity'])
def test_presupuesto_invalido(valor):
    with pytest.raises(ValidationError):Nueva(contacto_id=uuid4(),etapa_id=uuid4(),titulo='Casa',presupuesto=valor)

def test_presupuesto_decimal():
    n=Nueva(contacto_id=uuid4(),etapa_id=uuid4(),titulo='Casa',presupuesto='3000000.25')
    assert n.presupuesto==Decimal('3000000.25')

def test_no_inyectar_organizacion():
    with pytest.raises(ValidationError):Nueva(contacto_id=uuid4(),etapa_id=uuid4(),titulo='Casa',org_id=uuid4())

def test_movimiento_exige_version():
    with pytest.raises(ValidationError):Movimiento(etapa_id=uuid4())


@pytest.mark.parametrize('texto',['','   ','x'*4001])
def test_nota_rechaza_texto_vacio_o_excesivo(texto):
    from broquer.modulos.oportunidades import Nota
    with pytest.raises(ValidationError):Nota(texto=texto)

@pytest.mark.parametrize('campo',['org_id','creado_por','tipo'])
def test_nota_no_admite_suplantar_contexto(campo):
    from broquer.modulos.oportunidades import Nota
    with pytest.raises(ValidationError):Nota(**{'texto':'Acuerdo de visita',campo:'sistema'})


def test_configuracion_etapas_preserva_tipos_y_nombres_unicos():
    from broquer.modulos.oportunidades import ConfigurarEtapas
    buenas=[{'nombre':'Nuevo','tipo':'abierta'},{'nombre':'Cerrado','tipo':'ganada'},{'nombre':'Descartado','tipo':'perdida'}]
    assert len(ConfigurarEtapas(revision='a'*64,etapas=buenas).etapas)==3
    with pytest.raises(ValidationError):ConfigurarEtapas(revision='a'*64,etapas=[buenas[0],buenas[0],buenas[2]])
    with pytest.raises(ValidationError):ConfigurarEtapas(revision='a'*64,etapas=[{**e,'tipo':'abierta'} for e in buenas])
