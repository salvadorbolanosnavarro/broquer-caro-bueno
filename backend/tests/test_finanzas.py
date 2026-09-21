from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError
from broquer.modulos.finanzas import Movimiento,Cuenta,seguro

def base():return {'tipo':'ingreso','monto':'10.25','fecha':'2026-09-18','concepto':'Comisión','cuenta_id':uuid4(),'categoria_id':uuid4(),'idempotencia':uuid4()}

@pytest.mark.parametrize('monto',['0','-1','0.001','NaN','Infinity','100000000000000.00'])
def test_monto_invalido(monto):
    with pytest.raises(ValidationError):Movimiento(**{**base(),'monto':monto})

@pytest.mark.parametrize('cambio',[{'concepto':'  '},{'fecha':'1999-12-31'},{'categoria_id':None},{'cuenta_destino_id':uuid4()},{'org_id':uuid4()},{'moneda':'USD'}])
def test_relaciones_y_autoridad(cambio):
    with pytest.raises(ValidationError):Movimiento(**{**base(),**cambio})

def test_transferencia_exige_destino_distinto_sin_categoria():
    datos={**base(),'tipo':'transferencia','categoria_id':None}
    with pytest.raises(ValidationError):Movimiento(**datos)
    with pytest.raises(ValidationError):Movimiento(**{**datos,'cuenta_destino_id':datos['cuenta_id']})
    assert Movimiento(**{**datos,'cuenta_destino_id':uuid4()}).tipo=='transferencia'

def test_precision_hasta_el_json():
    assert seguro({'saldo':Decimal('99999999999999.99'),'lista':[Decimal('0.10')]})=={'saldo':'99999999999999.99','lista':['0.10']}
    assert Cuenta(nombre='Tarjeta',tipo='tarjeta',saldo_inicial='-12500.50').saldo_inicial==Decimal('-12500.50')


def test_exportacion_conserva_precision_y_neutraliza_formulas():
    import csv,io
    from broquer.modulos.finanzas import csv_periodo
    fila={'fecha':'2026-09-19','tipo':'ingreso','concepto':'  =HYPERLINK("x")\nsalto','monto':Decimal('99999999999999.99'),'moneda':'MXN','cuenta_nombre':'Banco','destino_nombre':None,'categoria_nombre':'Comisión','anulada_en':None}
    texto=csv_periodo([fila]);assert texto.startswith('\ufeff')
    fila_csv=list(csv.reader(io.StringIO(texto.removeprefix('\ufeff'))))[1]
    assert fila_csv[2]=="'"+fila['concepto']
    assert fila_csv[3]=='99999999999999.99'
    assert fila_csv[8]=='Vigente'


def test_periodo_rechaza_rango_invertido_y_excesivo():
    from datetime import date
    from types import SimpleNamespace
    from broquer.modulos.finanzas import filtro_periodo
    from broquer.core.errores import ErrorProducto
    ctx=SimpleNamespace(org_id=uuid4())
    for inicio,fin in [(date(2026,9,19),date(2026,9,1)),(date(2000,1,1),date(2026,1,1))]:
        with pytest.raises(ErrorProducto):filtro_periodo(ctx,inicio,fin,None)


def test_exportacion_rechaza_truncado(monkeypatch):
    from contextlib import contextmanager
    from datetime import date
    from types import SimpleNamespace
    import broquer.modulos.finanzas as fin
    from broquer.core.errores import ErrorProducto
    @contextmanager
    def db_falso(_):
        yield SimpleNamespace(execute=lambda *_:SimpleNamespace(fetchall=lambda:[{}]*10001))
    monkeypatch.setattr(fin,'transaccion',db_falso)
    monkeypatch.setattr(fin,'exigir',lambda *_:None)
    with pytest.raises(ErrorProducto) as error:
        fin.exportacion(date(2026,9,1),date(2026,9,30),None,SimpleNamespace(org_id=uuid4(),usuario_id=uuid4()))
    assert error.value.estado==422
