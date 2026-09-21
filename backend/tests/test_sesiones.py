from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import Mock
from uuid import uuid4
import pytest
import jwt as pyjwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Response
from broquer.core import sesiones, cifrado, jwt, limites
from broquer.core.errores import ErrorProducto
from broquer.modulos import cuentas, archivos

@pytest.fixture
def datos():
    return {'sub':str(uuid4()),'exp':int(datetime.now(timezone.utc).timestamp())+3600,'iat':int(datetime.now(timezone.utc).timestamp()),'aud':'authenticated','iss':'https://example.supabase.co/auth/v1','role':'authenticated'}
@pytest.fixture
def firma(monkeypatch):
    privada=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    monkeypatch.setattr(jwt,'configuracion',lambda:NS(disponible=True,supabase_url='https://example.supabase.co'))
    monkeypatch.setattr(jwt,'cliente_jwks',lambda url:NS(get_signing_key_from_jwt=lambda token:NS(key=privada.public_key())))
    return lambda d:pyjwt.encode(d,privada,algorithm='RS256')
def tx_falso(db):
    @contextmanager
    def tx(*a,**kw):yield db
    return tx
def test_jwt_valido(datos,firma):assert jwt.verificar_token(firma(datos))['sub']==datos['sub']
@pytest.mark.parametrize('campo,valor',[('aud','otra-app'),('iss','https://otro.example/auth/v1'),('exp',1),('role','service_role'),('sub','no-uuid')])
def test_jwt_rechaza_claims(datos,firma,campo,valor):
    datos[campo]=valor
    with pytest.raises(ErrorProducto) as e:jwt.verificar_token(firma(datos))
    assert e.value.estado==401
def test_cifrado_y_rotacion(monkeypatch):
    antigua,nueva=Fernet.generate_key().decode(),Fernet.generate_key().decode()
    monkeypatch.setattr(cifrado,'configuracion',lambda:NS(sesiones_claves=[antigua]))
    protegido=cifrado.cifrar({'access_token':'privado','refresh_token':'privado'});assert 'privado' not in protegido
    monkeypatch.setattr(cifrado,'configuracion',lambda:NS(sesiones_claves=[nueva,antigua]))
    assert cifrado.descifrar(protegido)['access_token']=='privado'
    with pytest.raises(ErrorProducto):cifrado.descifrar('manipulado')
def test_cookie_opaca(monkeypatch,datos):
    db=Mock();db.execute.return_value.fetchone.return_value=None
    monkeypatch.setattr(sesiones,'transaccion',tx_falso(db));monkeypatch.setattr(sesiones,'verificar_token',lambda token:datos);monkeypatch.setattr(sesiones,'cifrar',lambda d:'encrypted')
    r=Response();sesiones.crear_sesion({'access_token':'JWT-SECRET','refresh_token':'REFRESH-SECRET'},r)
    headers=r.headers.getlist('set-cookie');assert all('JWT-SECRET' not in c and 'REFRESH-SECRET' not in c for c in headers)
    nueva=[c for c in headers if 'Max-Age=2592000' in c][0];assert 'HttpOnly' in nueva and 'Secure' in nueva
@pytest.mark.parametrize('sesion',[None,{'proposito':'recuperacion'}])
def test_sesion_no_permitida(monkeypatch,sesion):
    db=Mock();db.execute.return_value.fetchone.return_value=sesion;monkeypatch.setattr(sesiones,'transaccion',tx_falso(db))
    with pytest.raises(ErrorProducto) as e:sesiones.leer_sesion(NS(cookies={'broquer_sesion':'a'*64}))
    assert e.value.estado in (401,403)
def test_sesion_uid_inconsistente(monkeypatch,datos):
    db=Mock();db.execute.return_value.fetchone.return_value={'proposito':'normal','credenciales_cifradas':'encrypted','usuario_id':uuid4(),'id':uuid4()}
    monkeypatch.setattr(sesiones,'transaccion',tx_falso(db));monkeypatch.setattr(sesiones,'descifrar',lambda _: {'exp':datos['exp'],'access_token':'jwt'});monkeypatch.setattr(sesiones,'verificar_token',lambda _:datos)
    with pytest.raises(ErrorProducto) as e:sesiones.leer_sesion(NS(cookies={'broquer_sesion':'a'*64}))
    assert e.value.estado==401
def test_perfil_incompleto_inicia_sesion(monkeypatch,datos):
    monkeypatch.setattr(cuentas,'limitar_acceso',lambda *a:None);monkeypatch.setattr(cuentas,'solicitar',lambda *a,**kw:NS(status_code=200,json=lambda:{'access_token':'jwt','refresh_token':'refresh','user':{'user_metadata':{}}}));monkeypatch.setattr(cuentas,'verificar_token',lambda _:datos);monkeypatch.setattr(cuentas,'completar_desde_proveedor',lambda *a:None)
    crear=Mock();monkeypatch.setattr(cuentas,'crear_sesion',crear);monkeypatch.setattr(cuentas,'revocar_actual',lambda *a:None);monkeypatch.setattr(cuentas,'respuesta_perfil',lambda _: {'perfil_completo':False})
    assert not cuentas.ingresar(cuentas.Ingreso(email='a@example.com',contrasena='abc'),Mock(),Response())['perfil_completo'];crear.assert_called_once()
def test_contrasena_actual_obligatoria(monkeypatch):
    monkeypatch.setattr(cuentas,'limitar_acceso',lambda *a:None);monkeypatch.setattr(cuentas,'leer_sesion',lambda *a,**kw:{'usuario_id':uuid4(),'proposito':'normal','credenciales':{'access_token':'jwt'}})
    proveedor=Mock();monkeypatch.setattr(cuentas,'solicitar',proveedor)
    with pytest.raises(ErrorProducto) as e:cuentas.contrasena(cuentas.Contrasena(nueva='nueva-clave-segura'),Mock(),Response())
    assert e.value.estado==422;proveedor.assert_not_called()
@pytest.mark.parametrize('ruta',['../x','otra-org/file.pdf','%2e%2e/file','foo\\bar','https://evil.example/file'])
def test_storage_rutas_invalidas(ruta):
    with pytest.raises(ErrorProducto):archivos.validar_ruta(ruta,uuid4())
def test_storage_ajeno_no_llama_proveedor(monkeypatch):
    db=Mock();db.execute.return_value.fetchone.return_value=None;monkeypatch.setattr(archivos,'transaccion',tx_falso(db));cliente=Mock();monkeypatch.setattr(archivos.httpx,'Client',cliente)
    with pytest.raises(ErrorProducto) as e:archivos.descargar(uuid4(),NS(usuario_id=uuid4(),org_id=uuid4()))
    assert e.value.estado==404;cliente.assert_not_called()
def test_rate_limit_sin_correo_en_claro(monkeypatch):
    db=Mock();db.execute.return_value.fetchone.return_value={'usadas':1};monkeypatch.setattr(limites,'transaccion',tx_falso(db));monkeypatch.setattr(limites,'configuracion',lambda:NS(rate_limit_secret='s'*40))
    limites.limitar('acceso:correo:privado@example.com',10);parametros=db.execute.call_args[0][1];assert len(parametros[0])==64 and 'privado' not in str(parametros)

def test_costo_ia_decimal():
    from decimal import Decimal
    from broquer.core.ia import calcular_costo
    assert calcular_costo(1000000,500000,{'entrada_millon_usd':Decimal('3.00'),'salida_millon_usd':Decimal('15.00')})==Decimal('10.50000000')
