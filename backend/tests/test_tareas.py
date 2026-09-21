from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from broquer.modulos.tareas import NuevaTarea, EstadoTarea, convertir_hora
from broquer.core.errores import ErrorProducto

def test_hora_real_mexico():
    assert convertir_hora(datetime(2026,9,18,9,35),'America/Mexico_City')==datetime(2026,9,18,15,35,tzinfo=timezone.utc)

@pytest.mark.parametrize('fecha',[datetime(2026,3,8,2,30),datetime(2026,11,1,1,30)])
def test_rechaza_hora_inexistente_o_ambigua(fecha):
    with pytest.raises(ErrorProducto):convertir_hora(fecha,'America/Tijuana')

@pytest.mark.parametrize('cambio',[{'titulo':'   '},{'duracion_min':0},{'duracion_min':1441},{'duracion_min':True},{'inicio_local':'2026-09-18T09:35:00Z'},{'org_id':str(uuid4())},{'asignado_a':str(uuid4())},{'tipo':'inexistente'}])
def test_rechaza_datos_invalidos(cambio):
    with pytest.raises(ValidationError):NuevaTarea(**({'titulo':'Visita','inicio_local':'2026-09-18T09:35',**cambio}))

def test_estado_exige_version_con_zona():
    with pytest.raises(ValidationError):EstadoTarea(completada=True,actualizado_en='2026-09-18T09:35')
