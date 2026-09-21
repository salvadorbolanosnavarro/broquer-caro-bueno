import { PGlite } from '@electric-sql/pglite';
import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const db=await PGlite.create();
let aprobadas=0;
async function probar(nombre,fn){await fn();aprobadas++;console.log('PASS '+nombre)}
await db.exec('CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,email_confirmed_at timestamptz)');
const carpeta=new URL('../../migrations/',import.meta.url);
for(const archivo of (await readdir(carpeta)).filter(x=>x.endsWith('.sql')).sort())await db.exec(await readFile(new URL(archivo,carpeta),'utf8'));
const [u1,u2]=[randomUUID(),randomUUID()];
for(const u of [u1,u2])await db.query('INSERT INTO auth.users VALUES($1,$2,now())',[u,u+'@example.test']);
async function como(uid,fn,otros={}){
 return db.transaction(async tx=>{await tx.exec('SET LOCAL ROLE broquer_api');await tx.query("SELECT set_config('broquer.usuario_id',$1,true)",[uid||'']);
 for(const [k,v] of Object.entries(otros))await tx.query('SELECT set_config($1,$2,true)',['broquer.'+k,v]);return fn(tx);});
}
const crear=uid=>como(uid,async tx=>(await tx.query("SELECT broquer.crear_cuenta_personal('Ana','Prueba','+524431234567') AS org")).rows[0].org);
const o1=await crear(u1),o2=await crear(u2);
await probar('onboarding idempotente',async()=>assert.equal(await crear(u1),o1));
for(const [u,o] of [[u1,o1],[u2,o2]]){
 await db.query("INSERT INTO broquer.trabajos(org_id,creado_por,tipo,clave) VALUES($1,$2,'test','test')",[o,u]);
 await db.query("INSERT INTO broquer.uso_cuotas(org_id,creado_por,modulo,accion,periodo,usado) VALUES($1,$2,'test','test',current_date,1)",[o,u]);
 await db.query("INSERT INTO broquer.uso_ia(org_id,creado_por,modulo,proveedor,modelo,exito) VALUES($1,$2,'test','test','test',true)",[o,u]);
 await db.query("INSERT INTO broquer.archivos(org_id,creado_por,asignado_a,nombre,ruta,mime,tamano) VALUES($1,$2,$2,'test.pdf',$3,'application/pdf',100)",[o,u,o+'/test.pdf']);
}
for(const tabla of ['organizaciones','organizacion_miembros','auditoria','trabajos','uso_cuotas','uso_ia','archivos']){
 const campo=tabla==='organizaciones'?'id':'org_id';
 await probar('RLS '+tabla,async()=>{await como(u1,async tx=>{
   assert.equal((await tx.query(`SELECT * FROM broquer.${tabla} WHERE ${campo}=$1`,[o2])).rows.length,0);
   assert.ok((await tx.query(`SELECT * FROM broquer.${tabla} WHERE ${campo}=$1`,[o1])).rows.length>0);
 });});
}
await probar('perfil ajeno oculto',()=>como(u1,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.usuarios WHERE id=$1',[u2])).rows.length,0)));
await probar('sin sesión no hay organizaciones',()=>como(null,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.organizaciones')).rows.length,0)));
await probar('rol no editable',async()=>assert.rejects(()=>como(u1,tx=>tx.query("UPDATE broquer.usuarios SET rol_interno='admin' WHERE id=$1",[u1])),e=>e.code==='42501'));
await probar('no inserta en otra organización',async()=>assert.rejects(()=>como(u1,tx=>tx.query("INSERT INTO broquer.trabajos(org_id,creado_por,tipo,clave) VALUES($1,$2,'test','cross')",[o2,u1])),e=>e.code==='42501'));
await probar('auditoría inmutable',async()=>assert.rejects(()=>como(u1,tx=>tx.query('DELETE FROM broquer.auditoria WHERE org_id=$1',[o1])),e=>e.code==='42501'));
await probar('sesiones aisladas',async()=>{
 const h1='1'.repeat(64),h2='2'.repeat(64);
 await como(u1,tx=>tx.query("INSERT INTO broquer.sesiones(usuario_id,token_hash,credenciales_cifradas,expira_en) VALUES($1,$2,'encrypted',now()+interval '1 day')",[u1,h1]),{sesion_hash:h1});
 await como(u2,tx=>tx.query("INSERT INTO broquer.sesiones(usuario_id,token_hash,credenciales_cifradas,expira_en) VALUES($1,$2,'encrypted',now()+interval '1 day')",[u2,h2]),{sesion_hash:h2});
 await como(null,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.sesiones')).rows.length,0));
 await como(null,async tx=>{const s=(await tx.query('SELECT * FROM broquer.sesiones')).rows;assert.equal(s.length,1);assert.equal(s[0].usuario_id,u1)},{sesion_hash:h1});
 await como(u1,async tx=>assert.equal((await tx.query('UPDATE broquer.sesiones SET revocada_en=now() WHERE usuario_id=$1 RETURNING id',[u2])).rows.length,0));
});
await probar('límite persistente respeta máximo',async()=>{
 const h='a'.repeat(64);
 for(let i=1;i<=4;i++)await como(null,async tx=>{
  const r=await tx.query(`INSERT INTO broquer.limites_solicitudes(clave_hash,ventana,usadas,expira_en) VALUES($1,1,1,now()+interval '1 minute') ON CONFLICT(clave_hash,ventana) DO UPDATE SET usadas=broquer.limites_solicitudes.usadas+1 WHERE broquer.limites_solicitudes.usadas<3 RETURNING usadas`,[h]);
  assert.equal(r.rows.length,i<=3?1:0);
 },{limite_hash:h});
});
await probar('cuota de plan y tope',async()=>{
 await db.exec("INSERT INTO broquer.plan_funciones(plan,modulo,accion,cuota_mensual) VALUES('gratis','ia','generar',3),('otro','ia','generar',99)");
 await como(u1,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.plan_funciones')).rows.length,1));
 for(let i=1;i<=4;i++)await como(u1,async tx=>{
  const r=await tx.query(`INSERT INTO broquer.uso_cuotas(org_id,creado_por,modulo,accion,periodo,usado) VALUES($1,$2,'ia','generar',current_date,1) ON CONFLICT(org_id,creado_por,modulo,accion,periodo) DO UPDATE SET usado=broquer.uso_cuotas.usado+1 WHERE broquer.uso_cuotas.usado<3 RETURNING usado`,[o1,u1]);
  assert.equal(r.rows.length,i<=3?1:0);
 });
});
await probar('worker sin acceso a sesiones',async()=>assert.rejects(()=>db.transaction(async tx=>{
 await tx.exec('SET LOCAL ROLE broquer_worker');await tx.exec('SELECT * FROM broquer.sesiones');
}),e=>e.code==='42501'));
await probar('efecto de cola idempotente',async()=>{
 const trabajo=(await db.query('SELECT id FROM broquer.trabajos WHERE org_id=$1',[o1])).rows[0].id;
 for(let i=0;i<2;i++)await db.transaction(async tx=>{
  await tx.exec('SET LOCAL ROLE broquer_worker');
  await tx.query("INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES($1,$2,'cola_verificada',$3) ON CONFLICT DO NOTHING",[o1,u1,trabajo]);
 });
 assert.equal((await db.query("SELECT count(*)::int AS n FROM broquer.auditoria WHERE accion='cola_verificada' AND referencia=$1",[trabajo])).rows[0].n,1);
});
await probar('API no puede alterar estado de trabajo',async()=>assert.rejects(()=>como(u1,tx=>tx.exec("UPDATE broquer.trabajos SET estado='completado'")),e=>e.code==='42501'));
await probar('contactos aislados y duplicados normalizados',async()=>{
 await como(u1,tx=>tx.query("INSERT INTO broquer.contactos(org_id,creado_por,asignado_a,nombre,email) VALUES($1,$2,$2,'María','maria@example.test')",[o1,u1]));
 await como(u2,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.contactos WHERE org_id=$1',[o1])).rows.length,0));
 await assert.rejects(()=>como(u1,tx=>tx.query("INSERT INTO broquer.contactos(org_id,creado_por,asignado_a,nombre,email) VALUES($1,$2,$2,'Otra','MARIA@example.test')",[o1,u1])),e=>e.code==='23505');
 await assert.rejects(()=>como(u2,tx=>tx.query("INSERT INTO broquer.contactos(org_id,creado_por,asignado_a,nombre,email) VALUES($1,$2,$2,'Ajena','ajena@example.test')",[o1,u2])),e=>e.code==='42501');
});
await probar('editar contacto no cambia creador',async()=>assert.rejects(()=>como(u1,tx=>tx.query('UPDATE broquer.contactos SET creado_por=$1',[u2])),e=>e.code==='42501'));
await probar('pipeline aislado con referencias de organización',async()=>{
 const etapa=(await como(u1,tx=>tx.query("INSERT INTO broquer.etapas(org_id,nombre,orden,tipo) VALUES($1,'Nuevo',0,'abierta') RETURNING id",[o1]))).rows[0].id;
 const contacto=(await como(u1,tx=>tx.query('SELECT id FROM broquer.contactos WHERE org_id=$1',[o1]))).rows[0].id;
 const op=(await como(u1,tx=>tx.query("INSERT INTO broquer.oportunidades(org_id,creado_por,asignado_a,contacto_id,etapa_id,titulo,tipo) VALUES($1,$2,$2,$3,$4,'Casa','compra') RETURNING id",[o1,u1,contacto,etapa]))).rows[0].id;
 await como(u1,tx=>tx.query('INSERT INTO broquer.historial_etapas(org_id,oportunidad_id,creado_por,nueva_id) VALUES($1,$2,$3,$4)',[o1,op,u1,etapa]));
 await como(u1,tx=>tx.query("INSERT INTO broquer.actividades(org_id,oportunidad_id,creado_por,tipo,texto) VALUES($1,$2,$3,'sistema','Creada')",[o1,op,u1]));
 for(const tabla of ['etapas','oportunidades','historial_etapas','actividades'])await como(u2,async tx=>assert.equal((await tx.query(`SELECT * FROM broquer.${tabla} WHERE org_id=$1`,[o1])).rows.length,0));
 await assert.rejects(()=>como(u2,tx=>tx.query("INSERT INTO broquer.oportunidades(org_id,creado_por,asignado_a,contacto_id,etapa_id,titulo,tipo) VALUES($1,$2,$2,$3,$4,'Ajena','compra')",[o2,u2,contacto,etapa])),e=>e.code==='23503');
 await assert.rejects(()=>como(u1,tx=>tx.exec('DELETE FROM broquer.historial_etapas')),e=>e.code==='42501');
 await assert.rejects(()=>como(u1,tx=>tx.exec("UPDATE broquer.actividades SET texto='alterado'")),e=>e.code==='42501');
});
await probar('tareas aisladas, vínculos protegidos y autor inmutable',async()=>{
 const op=(await db.query('SELECT id FROM broquer.oportunidades WHERE org_id=$1',[o1])).rows[0].id;
 const tarea=(await como(u1,tx=>tx.query("INSERT INTO broquer.tareas(org_id,creado_por,asignado_a,oportunidad_id,titulo,tipo,inicio,duracion_min) VALUES($1,$2,$2,$3,'Visita','visita','2026-09-18T15:35Z',45) RETURNING id,inicio",[o1,u1,op]))).rows[0];
 assert.equal(new Date(tarea.inicio).toISOString(),'2026-09-18T15:35:00.000Z');
 await como(u2,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.tareas WHERE id=$1',[tarea.id])).rows.length,0));
 await assert.rejects(()=>como(u2,tx=>tx.query("INSERT INTO broquer.tareas(org_id,creado_por,asignado_a,oportunidad_id,titulo,tipo,inicio,duracion_min) VALUES($1,$2,$2,$3,'Ajena','visita',now(),30)",[o2,u2,op])),e=>e.code==='42501');
 await assert.rejects(()=>como(u1,tx=>tx.query('UPDATE broquer.tareas SET asignado_a=$1 WHERE id=$2',[u2,tarea.id])),e=>e.code==='42501');
 await como(u1,tx=>tx.query('UPDATE broquer.tareas SET completada_en=now() WHERE id=$1',[tarea.id]));
 await como(u1,tx=>tx.query("INSERT INTO broquer.actividades(org_id,oportunidad_id,tarea_id,creado_por,tipo,texto) VALUES($1,$2,$3,$4,'tarea_completada','Visita completada')",[o1,op,tarea.id,u1]));
 await como(u1,tx=>tx.query('UPDATE broquer.tareas SET completada_en=NULL WHERE id=$1',[tarea.id]));
});
await probar('inventario aislado, operaciones múltiples y bitácora inmutable',async()=>{
 const p=(await como(u1,tx=>tx.query("INSERT INTO broquer.propiedades(org_id,creado_por,asignado_a,titulo,tipo,colonia,municipio,estado,banos,m2_construccion,clave_interna) VALUES($1,$2,$2,'Casa','casa','Altozano','Morelia','Michoacán',3.5,245.75,'TEST-1') RETURNING id,banos,m2_construccion",[o1,u1]))).rows[0];
 assert.equal(Number(p.banos),3.5);assert.equal(Number(p.m2_construccion),245.75);
 await como(u1,tx=>tx.query("INSERT INTO broquer.propiedad_operaciones(org_id,propiedad_id,operacion,precio,moneda) VALUES($1,$2,'venta',3850000,'MXN'),($1,$2,'renta',22000.50,'MXN')",[o1,p.id]));
 await como(u1,tx=>tx.query("INSERT INTO broquer.actividades(org_id,propiedad_id,creado_por,tipo,texto) VALUES($1,$2,$3,'sistema','Alta')",[o1,p.id,u1]));
 for(const tabla of ['propiedades','propiedad_operaciones','actividades'])await como(u2,async tx=>assert.equal((await tx.query(`SELECT * FROM broquer.${tabla} WHERE org_id=$1`,[o1])).rows.length,0));
 await assert.rejects(()=>como(u2,tx=>tx.query("INSERT INTO broquer.propiedad_operaciones(org_id,propiedad_id,operacion,precio,moneda) VALUES($1,$2,'venta',1,'MXN')",[o2,p.id])),e=>e.code==='42501');
 await como(u1,tx=>tx.query("UPDATE broquer.propiedad_operaciones SET precio=22500.50 WHERE propiedad_id=$1 AND operacion='renta'",[p.id]));
 await como(u1,tx=>tx.query("UPDATE broquer.propiedades SET estatus='reservada',archivado_en=now() WHERE id=$1",[p.id]));
 await assert.rejects(()=>como(u1,tx=>tx.query('UPDATE broquer.propiedades SET creado_por=$1 WHERE id=$2',[u2,p.id])),e=>e.code==='42501');
 await assert.rejects(()=>como(u1,tx=>tx.exec("UPDATE broquer.actividades SET texto='cambiado'")),e=>e.code==='42501');
 await assert.rejects(()=>como(u1,tx=>tx.exec('DELETE FROM broquer.propiedades')),e=>e.code==='42501');
});
await probar('etapas ordenables conservan identidades y bloquean tipo',async()=>{
 const primera=(await db.query('SELECT id FROM broquer.etapas WHERE org_id=$1',[o1])).rows[0].id;
 await como(u1,tx=>tx.query("INSERT INTO broquer.etapas(org_id,nombre,tipo,orden) VALUES($1,'Cerrado','ganada',1),($1,'Descartado','perdida',2)",[o1]));
 await como(u1,async tx=>{
  await tx.query('UPDATE broquer.etapas SET orden=orden+10 WHERE org_id=$1',[o1]);
  await tx.query("UPDATE broquer.etapas SET orden=0,nombre='Primer contacto' WHERE id=$1",[primera]);
  assert.equal((await tx.query('SELECT nombre FROM broquer.etapas WHERE id=$1',[primera])).rows[0].nombre,'Primer contacto');
 });
 await assert.rejects(()=>como(u1,tx=>tx.query("UPDATE broquer.etapas SET tipo='perdida' WHERE id=$1",[primera])),e=>e.code==='42501');
 await como(u2,async tx=>assert.equal((await tx.query("UPDATE broquer.etapas SET nombre='Ajena' WHERE id=$1 RETURNING id",[primera])).rows.length,0));
});
await probar('finanzas: transferencias, moneda, aislamiento e inmutabilidad',async()=>{
 const cuenta=async(nombre,moneda,saldo)=>(await como(u1,tx=>tx.query("INSERT INTO broquer.fin_cuentas(org_id,creado_por,nombre,tipo,moneda,saldo_inicial) VALUES($1,$2,$3,'banco',$4,$5) RETURNING id",[o1,u1,nombre,moneda,saldo]))).rows[0].id;
 const a=await cuenta('Banco','MXN','500.00'),b=await cuenta('Caja','MXN','100.00'),usd=await cuenta('Dólares','USD','0');
 const llave=randomUUID();
 const m=(await como(u1,tx=>tx.query("INSERT INTO broquer.fin_movimientos(org_id,creado_por,tipo,monto,moneda,fecha,concepto,cuenta_id,cuenta_destino_id,idempotencia,huella) VALUES($1,$2,'transferencia',250.25,'MXN','2026-09-18','Traslado',$3,$4,$5,'test') RETURNING id",[o1,u1,a,b,llave]))).rows[0].id;
 const saldos=async()=>como(u1,async tx=>(await tx.query("SELECT c.id,c.saldo_inicial+coalesce((SELECT sum(CASE WHEN m.tipo='ingreso' OR m.cuenta_destino_id=c.id THEN monto ELSE -monto END) FROM broquer.fin_movimientos m WHERE m.anulada_en IS NULL AND (m.cuenta_id=c.id OR m.cuenta_destino_id=c.id)),0) AS saldo FROM broquer.fin_cuentas c WHERE c.id=ANY($1)",[[a,b]])).rows);
 assert.deepEqual((await saldos()).map(c=>Number(c.saldo)).sort((x,y)=>x-y),[249.75,350.25]);
 await assert.rejects(()=>como(u1,tx=>tx.query("INSERT INTO broquer.fin_movimientos(org_id,creado_por,tipo,monto,moneda,fecha,concepto,cuenta_id,cuenta_destino_id,idempotencia,huella) VALUES($1,$2,'transferencia',1,'MXN',current_date,'Moneda distinta',$3,$4,$5,'test')",[o1,u1,a,usd,randomUUID()])),e=>e.code==='42501');
 await como(u2,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.fin_movimientos')).rows.length,0));
 await assert.rejects(()=>como(u1,tx=>tx.query('UPDATE broquer.fin_movimientos SET monto=1 WHERE id=$1',[m])),e=>e.code==='42501');
 await assert.rejects(()=>como(u1,tx=>tx.query('UPDATE broquer.fin_cuentas SET saldo_inicial=0 WHERE id=$1',[a])),e=>e.code==='42501');
 await como(u1,tx=>tx.query("UPDATE broquer.fin_movimientos SET anulada_en=now(),motivo_anulacion='Corrección' WHERE id=$1",[m]));
 assert.deepEqual((await saldos()).map(c=>Number(c.saldo)).sort((x,y)=>x-y),[100,500]);
});
await probar('cuenta inactiva pierde acceso',async()=>{await db.query('UPDATE broquer.usuarios SET activo=false WHERE id=$1',[u1]);await como(u1,async tx=>assert.equal((await tx.query('SELECT * FROM broquer.organizaciones')).rows.length,0));});
console.log(`${aprobadas} verificaciones SQL aprobadas (PostgreSQL WASM; sin concurrencia ni servicios Supabase).`);
await db.close();
