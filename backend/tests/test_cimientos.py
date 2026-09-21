from uuid import uuid4
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from broquer.main import app
from broquer.core.config import configuracion
from broquer.core.permisos import Contexto,efectivos,exigir
from broquer.core.errores import ErrorProducto
from broquer.core import cuotas,ia,jwt as auth
from broquer.modulos.cuentas import Registro
from broquer.core.sesiones import limpiar_cookie
@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv('PROXY_SECRET','x'*40)
    monkeypatch.setenv('ORIGENES_PERMITIDOS','["https://broquer.test"]')
    monkeypatch.setenv('DATABASE_URL','');monkeypatch.setenv('SUPABASE_URL','');configuracion.cache_clear()
    yield TestClient(app,headers={'X-Broquer-Proxy':'x'*40})
    configuracion.cache_clear()
@pytest.fixture
def ctx():return Contexto(uuid4(),uuid4(),'agente',permisos=efectivos('agente','empresa',{}))
@pytest.mark.parametrize('ruta',['/v1/me','/v1/me/modulos'])
def test_sin_sesion_niega_datos(cliente,ruta):assert cliente.get(ruta).status_code==401
def test_sin_config_no_finge_conexion(cliente):assert not cliente.get('/v1/estado').json()['acceso_disponible']
@pytest.mark.parametrize('origen',[None,'https://evil.example'])
def test_csrf(cliente,origen):assert cliente.post('/v1/auth/salir',headers={'Origin':origen} if origen else {}).status_code==403
def test_cierre_cookies(cliente):
    r=cliente.post('/v1/auth/salir',headers={'Origin':'https://broquer.test'});assert r.status_code==200
    assert len(r.headers.get_list('set-cookie'))==2
    assert all('Max-Age=0' in c and 'Secure' in c and 'HttpOnly' in c for c in r.headers.get_list('set-cookie'))
def test_registro_cerrado(cliente):
    r=cliente.post('/v1/auth/registrar',headers={'Origin':'https://broquer.test'},json={'email':'a@example.com','contrasena':'Una-clave-segura','nombre':'Ana','apellidos':'Pérez','telefono':'4431234567'})
    assert r.status_code==503
@pytest.mark.parametrize('telefono',['4431234567','+524431234567','443 123 4567'])
def test_telefono(telefono):
    r=Registro(email='a@example.com',contrasena='Una-clave-segura',nombre=' Ana ',apellidos='Pérez',telefono=telefono)
    assert r.telefono=='+524431234567' and r.nombre=='Ana'
def test_sin_autoasignacion_admin():
    with pytest.raises(ValidationError):Registro(email='a@example.com',contrasena='Una-clave-segura',nombre='Ana',apellidos='Pérez',telefono='4431234567',rol_interno='admin')
def test_override_booleano():
    p=efectivos('agente','empresa',{'ver_comisiones':'true','exportar':False,'inventado':True})
    assert p['ver_comisiones'] is False and not p['exportar'] and 'inventado' not in p
def test_sin_edicion_ajena(ctx):
    with pytest.raises(ErrorProducto) as e:exigir(ctx,'inmuebles','editar_registros_ajenos')
    assert e.value.estado==403
def test_admin_respeta_modulo_desactivado(ctx):
    c=replace(ctx,rol_org='admin',permisos=efectivos('admin','empresa',{}),modulos_desactivados=('isr',))
    with pytest.raises(ErrorProducto) as e:exigir(c,'isr')
    assert e.value.estado==403
def test_cookies_seguras():
    r=Mock();limpiar_cookie(r)
    assert all(c.kwargs['httponly'] and c.kwargs['secure'] for c in r.delete_cookie.call_args_list)
@pytest.mark.parametrize('respuestas,estado',[([None],402),([{'cuota_mensual':10},None],429)])
def test_limites(ctx,monkeypatch,respuestas,estado):
    db=Mock();db.execute.return_value.fetchone.side_effect=respuestas
    @contextmanager
    def tx(uid):yield db
    monkeypatch.setattr(cuotas,'transaccion',tx)
    with pytest.raises(ErrorProducto) as e:cuotas.reservar_cuota(ctx,'contratos','generar')
    assert e.value.estado==estado
def test_cuota_antes_de_llamar_ia(ctx,monkeypatch):
    monkeypatch.setattr(ia,'configuracion',lambda:SimpleNamespace(anthropic_api_key='test',ia_modelo_default='test'))
    monkeypatch.setattr(ia,'reservar_cuota',Mock(side_effect=ErrorProducto(429,'cuota_agotada','Límite')))
    db=Mock();db.execute.return_value.fetchone.return_value={'entrada_millon_usd':1,'salida_millon_usd':1}
    @contextmanager
    def tx(uid):yield db
    monkeypatch.setattr(ia,'transaccion',tx)
    proveedor=Mock();monkeypatch.setattr(ia.httpx,'Client',proveedor)
    with pytest.raises(ErrorProducto):ia.generar(ctx,'contratos','texto')
    proveedor.assert_not_called()
def test_jwt_no_verificado_rechazado(monkeypatch):
    import jwt
    monkeypatch.setattr(auth,'configuracion',lambda:SimpleNamespace(disponible=True,supabase_url='https://test.supabase.co'))
    jwks=Mock();jwks.get_signing_key_from_jwt.side_effect=jwt.PyJWKClientError('invalid')
    monkeypatch.setattr(auth,'cliente_jwks',lambda url:jwks)
    with pytest.raises(ErrorProducto) as e:auth.verificar_token('falso')
    assert e.value.estado==401
