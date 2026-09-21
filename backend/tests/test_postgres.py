"""Run against an isolated, migrated Supabase TEST database, never production."""
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import psycopg
import pytest
from broquer.core.config import configuracion
from broquer.core.base import transaccion
from broquer.core.cuotas import reservar_cuota
from broquer.core.permisos import Contexto
from broquer.core.errores import ErrorProducto
DSN=os.environ.get('BROQUER_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not DSN,reason='No disposable migrated Supabase PostgreSQL configured.')
@pytest.fixture
def tenants(monkeypatch):
    monkeypatch.setenv('DATABASE_WORKER_URL',DSN or '');monkeypatch.setenv('DATABASE_URL',DSN or '');configuracion.cache_clear()
    ids=[uuid4(),uuid4()];orgs=[]
    with psycopg.connect(DSN) as db:
        for uid in ids:db.execute('INSERT INTO auth.users(id,email,email_confirmed_at) VALUES(%s,%s,now())',(uid,str(uid)+'@example.test'))
    for uid in ids:
        with transaccion(uid) as db:
            orgs.append(db.execute("SELECT broquer.crear_cuenta_personal('Demo','Prueba','+524431234567') AS org").fetchone()['org'])
            db.execute("INSERT INTO broquer.trabajos(org_id,creado_por,tipo,clave) VALUES(%s,%s,'test','test')",(orgs[-1],uid))
            db.execute("INSERT INTO broquer.uso_cuotas(org_id,creado_por,modulo,accion,periodo,usado) VALUES(%s,%s,'test','test',current_date,1)",(orgs[-1],uid))
            db.execute("INSERT INTO broquer.uso_ia(org_id,creado_por,modulo,proveedor,modelo,exito) VALUES(%s,%s,'test','test','test',true)",(orgs[-1],uid))
    yield ids,orgs
    with psycopg.connect(DSN) as db:
        for t in ['fin_movimientos','fin_cuentas','fin_categorias','actividades','tareas','propiedad_operaciones','propiedades','historial_etapas','oportunidades','etapas','contactos','trabajos','auditoria','uso_ia','uso_cuotas','organizacion_miembros']:db.execute(f'DELETE FROM broquer.{t} WHERE org_id=ANY(%s)',(orgs,))
        db.execute('DELETE FROM broquer.organizaciones WHERE id=ANY(%s)',(orgs,));db.execute('DELETE FROM broquer.usuarios WHERE id=ANY(%s)',(ids,));db.execute('DELETE FROM auth.users WHERE id=ANY(%s)',(ids,))
    configuracion.cache_clear()
@pytest.mark.parametrize('tabla',['organizaciones','organizacion_miembros','auditoria','trabajos','uso_cuotas','uso_ia'])
def test_rls_otra_org(tabla,tenants):
    ids,orgs=tenants;campo='id' if tabla=='organizaciones' else 'org_id'
    with transaccion(ids[0]) as db:assert not db.execute(f'SELECT * FROM broquer.{tabla} WHERE {campo}=%s',(orgs[1],)).fetchall()
def test_otro_perfil_oculto(tenants):
    ids,_=tenants
    with transaccion(ids[0]) as db:assert not db.execute('SELECT * FROM broquer.usuarios WHERE id=%s',(ids[1],)).fetchall()
def test_registro_idempotente(tenants):
    ids,orgs=tenants
    with transaccion(ids[0]) as db:assert db.execute("SELECT broquer.crear_cuenta_personal('Demo','Prueba','+524431234567') AS org").fetchone()['org']==orgs[0]
def test_autoasignacion_admin_prohibida(tenants):
    ids,_=tenants
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaccion(ids[0]) as db:db.execute("UPDATE broquer.usuarios SET rol_interno='admin' WHERE id=%s",(ids[0],))
def test_no_insertar_otra_org(tenants):
    ids,orgs=tenants
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaccion(ids[0]) as db:db.execute("INSERT INTO broquer.trabajos(org_id,creado_por,tipo,clave) VALUES(%s,%s,'test','cross')",(orgs[1],ids[0]))
def test_cuota_concurrente(tenants):
    ids,orgs=tenants;plan='test_'+uuid4().hex
    with psycopg.connect(DSN) as db:
        db.execute('UPDATE broquer.organizaciones SET plan=%s WHERE id=%s',(plan,orgs[0]));db.execute("INSERT INTO broquer.plan_funciones(plan,modulo,accion,cuota_mensual) VALUES(%s,'test_concurrente','generar',3)",(plan,))
    ctx=Contexto(ids[0],orgs[0],'owner',plan=plan)
    def consumir(_):
        try:reservar_cuota(ctx,'test_concurrente','generar');return True
        except ErrorProducto as e:assert e.estado==429;return False
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:assert sum(pool.map(consumir,range(10)))==3
    finally:
        with psycopg.connect(DSN) as db:db.execute('DELETE FROM broquer.plan_funciones WHERE plan=%s',(plan,))


def test_encolar_concurrente_idempotente(tenants):
    from broquer.core.cola import encolar
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner')
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados=list(pool.map(lambda _:encolar(ctx,'verificar_cola','misma',{'valor':1}),range(12)))
    assert len(set(resultados))==1
    with pytest.raises(ErrorProducto) as error:encolar(ctx,'verificar_cola','misma',{'valor':2})
    assert error.value.estado==409


def test_worker_completa_e_idempotencia(tenants):
    from broquer.core.cola import encolar
    from broquer.worker import ejecutar_una
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner')
    trabajo=encolar(ctx,'verificar_cola','completar',{})
    for _ in range(10):
        if not ejecutar_una():break
    with psycopg.connect(DSN) as db:
        assert db.execute('SELECT estado FROM broquer.trabajos WHERE id=%s',(trabajo,)).fetchone()[0]=='completado'
        db.execute("UPDATE broquer.trabajos SET estado='ejecutando',bloqueado_hasta=now()-interval '1 minute' WHERE id=%s",(trabajo,))
    ejecutar_una()
    with psycopg.connect(DSN) as db:
        assert db.execute("SELECT count(*) FROM broquer.auditoria WHERE accion='cola_verificada' AND referencia=%s",(trabajo,)).fetchone()[0]==1


def test_trabajo_ajeno_no_consultable(tenants):
    from broquer.core.cola import encolar
    from broquer.modulos.trabajos import consultar
    ids,orgs=tenants
    trabajo=encolar(Contexto(ids[0],orgs[0],'owner'),'verificar_cola','privado',{'secreto':'nunca devolver'})
    with pytest.raises(ErrorProducto) as error:consultar(trabajo,Contexto(ids[1],orgs[1],'owner'))
    assert error.value.estado==404
    respuesta=consultar(trabajo,Contexto(ids[0],orgs[0],'owner'))
    assert set(respuesta)=={'id','estado','creado_en','mensaje_usuario'}


def test_pipeline_historial_y_conflicto(tenants):
    from broquer.modulos.oportunidades import inicializar,crear,mover,actividad,Nueva,Movimiento
    from broquer.modulos.contactos import crear as crear_contacto,Contacto
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner')
    c=crear_contacto(Contacto(nombre='Prueba',email='pipeline@example.test'),ctx)
    etapas=inicializar(ctx)['etapas']
    assert len(inicializar(ctx)['etapas'])==len(etapas)
    o=crear(Nueva(contacto_id=c['id'],etapa_id=etapas[0]['id'],titulo='Casa'),ctx)
    actualizado=mover(o['id'],Movimiento(etapa_id=etapas[1]['id'],actualizado_en=o['actualizado_en']),ctx)
    assert len(actividad(o['id'],ctx)['actividades'])==2
    with pytest.raises(ErrorProducto) as error:
        mover(o['id'],Movimiento(etapa_id=etapas[2]['id'],actualizado_en=o['actualizado_en']),ctx)
    assert error.value.estado==409
    with pytest.raises(ErrorProducto) as error:
        mover(o['id'],Movimiento(etapa_id=etapas[-1]['id'],actualizado_en=actualizado['actualizado_en']),ctx)
    assert error.value.estado==422
    assert len(actividad(o['id'],ctx)['actividades'])==2
    with pytest.raises(ErrorProducto) as error:actividad(o['id'],Contexto(ids[1],orgs[1],'owner'))
    assert error.value.estado==404


def test_tareas_hora_conflicto_estado_y_aislamiento(tenants):
    from broquer.modulos.tareas import crear,editar,estado,listar,NuevaTarea,EditarTarea,EstadoTarea
    from datetime import datetime, timezone
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner');otro=Contexto(ids[1],orgs[1],'owner')
    datos={'titulo':'Visita','inicio_local':'2026-09-18T09:35','tipo':'visita','duracion_min':45}
    t=crear(NuevaTarea(**datos),ctx)['tarea']
    assert t['inicio']==datetime(2026,9,18,15,35,tzinfo=timezone.utc)
    segunda=crear(NuevaTarea(**{**datos,'inicio_local':'2026-09-18T10:00'}),ctx)
    assert segunda['conflictos'][0]['id']==t['id']
    assert listar(200,otro)['tareas']==[]
    with pytest.raises(ErrorProducto) as error:estado(t['id'],EstadoTarea(completada=True,actualizado_en=t['actualizado_en']),otro)
    assert error.value.estado==404
    terminada=estado(t['id'],EstadoTarea(completada=True,actualizado_en=t['actualizado_en']),ctx)
    assert terminada['completada_en'] is not None
    with pytest.raises(ErrorProducto) as error:editar(t['id'],EditarTarea(**datos,actualizado_en=t['actualizado_en']),ctx)
    assert error.value.estado==409
    abierta=estado(t['id'],EstadoTarea(completada=False,actualizado_en=terminada['actualizado_en']),ctx)
    assert abierta['completada_en'] is None


def test_inventario_operaciones_historial_y_version(tenants):
    from broquer.modulos.inmuebles import crear,detalle,editar,estatus,archivo,duplicar,DatosInmueble,Edicion,CambioEstatus,Archivo,Version
    from decimal import Decimal
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner');otro=Contexto(ids[1],orgs[1],'owner')
    datos={'titulo':'Casa','tipo':'casa','colonia':'Altozano','municipio':'Morelia','estado':'Michoacán','clave_interna':'TEST-1','banos':'3.5','operaciones':[{'operacion':'venta','precio':'3850000','moneda':'MXN'},{'operacion':'renta','precio':'22000.50','moneda':'MXN'}]}
    p=crear(DatosInmueble(**datos),ctx)
    assert len(p['operaciones'])==2 and p['banos']==Decimal('3.5')
    with pytest.raises(ErrorProducto) as error:detalle(p['id'],otro)
    assert error.value.estado==404
    with pytest.raises(ErrorProducto) as error:crear(DatosInmueble(**datos),ctx)
    assert error.value.estado==409
    nueva=editar(p['id'],Edicion(**{**datos,'operaciones':[datos['operaciones'][1]],'actualizado_en':p['actualizado_en']}),ctx)
    assert len(nueva['operaciones'])==1 and nueva['operaciones'][0]['operacion']=='renta'
    with pytest.raises(ErrorProducto) as error:estatus(p['id'],CambioEstatus(estatus='rentada',actualizado_en=p['actualizado_en']),ctx)
    assert error.value.estado==409
    rentada=estatus(p['id'],CambioEstatus(estatus='rentada',actualizado_en=nueva['actualizado_en']),ctx)
    assert not rentada['disponible_para_ofrecer']
    copia=duplicar(p['id'],Version(actualizado_en=rentada['actualizado_en']),ctx)
    assert copia['estatus']=='disponible' and copia['clave_interna'] is None and copia['id']!=p['id']
    archivada=archivo(copia['id'],Archivo(archivar=True,actualizado_en=copia['actualizado_en']),ctx)
    assert archivada['archivado_en'] and not archivada['disponible_para_ofrecer']
    assert len(detalle(p['id'],ctx)['historial'])==3
    from broquer.modulos.tareas import crear as crear_tarea,estado as completar,NuevaTarea,EstadoTarea
    tarea=crear_tarea(NuevaTarea(titulo='Visitar inmueble',inicio_local='2026-09-20T10:35',propiedad_id=p['id']),ctx)['tarea']
    completar(tarea['id'],EstadoTarea(completada=True,actualizado_en=tarea['actualizado_en']),ctx)
    assert [e['tipo'] for e in detalle(p['id'],ctx)['historial'][:2]]==['tarea_completada','tarea_creada']


def test_etapas_configurables_no_pierden_historial(tenants):
    from broquer.modulos.oportunidades import inicializar,configurar_etapas,ConfigurarEtapas
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner')
    antes=inicializar(ctx)
    filas=[{k:e[k] for k in ('id','nombre','tipo')} for e in reversed(antes['etapas'])]
    filas[0]['nombre']='Descartado con motivo'
    filas.append({'nombre':'Visita','tipo':'abierta'})
    datos=ConfigurarEtapas(revision=antes['revision'],etapas=filas)
    despues=configurar_etapas(datos,ctx)
    assert len(despues['etapas'])==7
    assert despues['etapas'][0]['nombre']=='Descartado con motivo'
    assert {e['id'] for e in antes['etapas']} <= {e['id'] for e in despues['etapas']}
    with pytest.raises(ErrorProducto) as error:configurar_etapas(datos,ctx)
    assert error.value.estado==409
    with pytest.raises(ErrorProducto) as error:configurar_etapas(datos,Contexto(ids[0],orgs[0],'agente'))
    assert error.value.estado==403


def test_finanzas_transferencias_reintentos_y_anulacion(tenants):
    from broquer.modulos.finanzas import crear_cuenta,crear_movimiento,inicializar,cuentas,anular,Cuenta,Movimiento,Anulacion
    from decimal import Decimal
    ids,orgs=tenants;ctx=Contexto(ids[0],orgs[0],'owner');otro=Contexto(ids[1],orgs[1],'owner')
    a=crear_cuenta(Cuenta(nombre='Banco',saldo_inicial='500'),ctx)
    b=crear_cuenta(Cuenta(nombre='Caja',tipo='efectivo',saldo_inicial='100'),ctx)
    cats=inicializar(ctx)['categorias']
    assert len(inicializar(ctx)['categorias'])==len(cats)
    d=Movimiento(tipo='transferencia',monto='250.25',fecha='2026-09-18',concepto='Traslado',cuenta_id=a['id'],cuenta_destino_id=b['id'],idempotencia=uuid4())
    m=crear_movimiento(d,ctx)
    assert crear_movimiento(d,ctx)['id']==m['id']
    saldos={c['id']:Decimal(c['saldo']) for c in cuentas(ctx)['cuentas']}
    assert saldos[a['id']]==Decimal('249.75') and saldos[b['id']]==Decimal('350.25')
    assert cuentas(otro)['cuentas']==[]
    with pytest.raises(ErrorProducto) as error:crear_movimiento(d.model_copy(update={'monto':Decimal('200')}),ctx)
    assert error.value.estado==409
    anular(m['id'],Anulacion(motivo='Corrección',actualizado_en=m['actualizado_en']),ctx)
    assert {c['id']:Decimal(c['saldo']) for c in cuentas(ctx)['cuentas']}=={a['id']:Decimal('500'),b['id']:Decimal('100')}

    from datetime import date
    from broquer.modulos.finanzas import reporte,exportacion
    cat=next(c for c in cats if c['tipo']=='ingreso')
    crear_movimiento(Movimiento(tipo='ingreso',monto='100.25',fecha='2026-09-19',concepto='Comisión',cuenta_id=a['id'],categoria_id=cat['id'],idempotencia=uuid4()),ctx)
    for agrupacion in ['mes','categoria','inmueble']:
        grupos=reporte(date(2026,9,1),date(2026,9,30),agrupacion,None,ctx)['grupos']
        assert len(grupos)==1 and grupos[0]['resultado']=='100.25'
        assert grupos[0]['movimientos']==1
        assert reporte(date(2026,9,1),date(2026,9,30),agrupacion,None,otro)['grupos']==[]
    assert exportacion(date(2026,9,1),date(2026,9,30),None,ctx)['cantidad']==2
    assert exportacion(date(2026,9,1),date(2026,9,30),None,otro)['cantidad']==0
