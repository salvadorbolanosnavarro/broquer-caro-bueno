from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import ValidationError
from broquer.modulos.contactos import Contacto,telefono_normalizado,visible

@pytest.mark.parametrize('entrada,salida',[('443 123 4567','+524431234567'),('+5214431234567','+524431234567'),('5214431234567','+524431234567'),('+14155552671','+14155552671')])
def test_normalizar_internacional(entrada,salida):assert telefono_normalizado(entrada)==salida

def test_alta_solo_email_conserva_nombre():
    c=Contacto(nombre='María de la Luz',email='maria@example.com')
    assert c.telefono is None and c.nombre=='María de la Luz'

def test_alta_sin_canal_rechazada():
    with pytest.raises(ValidationError):Contacto(nombre='Ana')

def test_mascara_y_edicion_ajena():
    propio,otro=uuid4(),uuid4()
    c={'creado_por':otro,'asignado_a':otro,'telefono':'+524431234567'}
    r=visible(c,SimpleNamespace(usuario_id=propio,permisos={}))
    assert r['telefono']=='••••4567' and not r['puede_editar']
    assert c['telefono']=='+524431234567'
