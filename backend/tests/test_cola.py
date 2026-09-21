from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4
import pytest
from broquer.core import cola
from broquer.core.errores import ErrorProducto
from broquer.modulos import trabajos

@pytest.fixture
def ctx():
    return SimpleNamespace(usuario_id=uuid4(),org_id=uuid4())

@contextmanager
def falso_db(fila):
    class DB:
        def execute(self,*args):return self
        def fetchone(self):return fila
    yield DB()


def test_reintento_devuelve_mismo_trabajo(monkeypatch,ctx):
    identificador=uuid4()
    monkeypatch.setattr(cola,'transaccion',lambda _:falso_db({'id':identificador,'datos':{'a':1}}))
    assert cola.encolar(ctx,'prueba','clave',{'a':1})==identificador


@pytest.mark.parametrize('nuevo',[2,True])
def test_reintento_con_datos_distintos_no_se_acepta(monkeypatch,ctx,nuevo):
    monkeypatch.setattr(cola,'transaccion',lambda _:falso_db({'id':uuid4(),'datos':{'a':1}}))
    with pytest.raises(ErrorProducto) as error:cola.encolar(ctx,'prueba','clave',{'a':nuevo})
    assert error.value.estado==409

@pytest.mark.parametrize('datos',[{'dato':'x'*32769},{'numero':float('nan')}])
def test_carga_invalida_no_abre_base(monkeypatch,ctx,datos):
    monkeypatch.setattr(cola,'transaccion',lambda _:pytest.fail('Invalid payload reached database'))
    with pytest.raises(ValueError):cola.encolar(ctx,'prueba','clave',datos)


def test_consulta_no_devuelve_datos_privados(monkeypatch,ctx):
    fila={'id':uuid4(),'estado':'pendiente','creado_en':'2026-09-16'}
    monkeypatch.setattr(trabajos,'transaccion',lambda _:falso_db(fila))
    assert set(trabajos.consultar(fila['id'],ctx))=={'id','estado','creado_en','mensaje_usuario'}


def test_consulta_ajena_o_inexistente_mismo_error(monkeypatch,ctx):
    monkeypatch.setattr(trabajos,'transaccion',lambda _:falso_db(None))
    with pytest.raises(ErrorProducto) as error:trabajos.consultar(uuid4(),ctx)
    assert error.value.estado==404
