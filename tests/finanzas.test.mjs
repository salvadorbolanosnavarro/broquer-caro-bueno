import test from 'node:test';
import assert from 'node:assert/strict';
import {centavos,decimalMoneda,calcularSaldos,resumir,csvMovimientos} from '../lib/finanzas.ts';
test('aritmética exacta de centavos y valores grandes',()=>{
 assert.equal(decimalMoneda(centavos('0.10')+centavos('0.20')),'0.30');
 assert.equal(decimalMoneda(centavos('99999999999999.99')),'99999999999999.99');
 assert.throws(()=>centavos('1.005'));
});
test('transferencia conserva el total y anulación revierte ambos lados',()=>{
 const cuentas=[{id:'a',saldo_inicial:'500.00'},{id:'b',saldo_inicial:'100.00'}];
 const transferencia={tipo:'transferencia',monto:'250.25',moneda:'MXN',cuenta_id:'a',cuenta_destino_id:'b',anulada_en:null};
 assert.deepEqual(calcularSaldos(cuentas,[transferencia]).map(c=>c.saldo),['249.75','350.25']);
 assert.equal(resumir([transferencia])[0].resultado,'0.00');
 assert.deepEqual(calcularSaldos(cuentas,[{...transferencia,anulada_en:'2026-09-18'}]).map(c=>c.saldo),['500.00','100.00']);
});
test('monedas separadas y anulados fuera del resultado',()=>{
 const r=resumir([{tipo:'ingreso',monto:'100.20',moneda:'MXN'},{tipo:'gasto',monto:'0.10',moneda:'MXN'},{tipo:'ingreso',monto:'2.50',moneda:'USD'},{tipo:'gasto',monto:'1000',moneda:'USD',anulada_en:'2026-09-18'}]);
 assert.equal(r[0].resultado,'100.10');assert.equal(r[1].resultado,'2.50');
});
test('CSV neutraliza fórmulas y conserva conceptos multilínea',()=>{
 const csv=csvMovimientos([{fecha:'2026-09-18',tipo:'ingreso',concepto:' =HYPERLINK("x")\nprueba',monto:'10.25',moneda:'MXN',cuenta_nombre:'Banco'}]);
 assert.ok(csv.startsWith('\uFEFF'));assert.ok(csv.includes('"\' =HYPERLINK(""x"")\nprueba"'));
});

test('reportes conservan totales, separan monedas y excluyen anulados y transferencias',async()=>{
 const {agruparFinanzas}=await import('../lib/finanzas.ts');
 const base={fecha:'2026-09-18',moneda:'MXN',categoria_id:'c',categoria_nombre:'Comisión',propiedad_id:'p'};
 const ms=[{...base,tipo:'ingreso',monto:'100.10'},{...base,tipo:'gasto',monto:'0.20'},{...base,tipo:'transferencia',monto:'9000'},{...base,tipo:'ingreso',monto:'5000',anulada_en:'2026-09-19'},{...base,tipo:'ingreso',moneda:'USD',monto:'10.50'},{...base,fecha:'2026-10-01',tipo:'gasto',monto:'5.00'}];
 const meses=agruparFinanzas(ms,'mes');assert.equal(meses.length,3);assert.equal(meses[0].resultado,'99.90');assert.equal(meses[0].movimientos,2);
 for(const modo of ['categoria','inmueble']){const gs=agruparFinanzas(ms,modo,[{id:'p',nombre:'Casa'}]);assert.equal(gs[0].resultado,'94.90');assert.equal(gs[1].resultado,'10.50');}
 const sin=agruparFinanzas(ms,'inmueble',[]);assert.equal(sin[0].nombre,'Sin inmueble visible');
});
test('periodos rápidos conservan el día local y el trimestre correcto',async()=>{
 const {periodoRapido}=await import('../lib/finanzas.ts');
 assert.deepEqual(periodoRapido('trimestre','2026-01-01'),{desde:'2026-01-01',hasta:'2026-01-01'});
 assert.deepEqual(periodoRapido('trimestre','2026-12-31'),{desde:'2026-10-01',hasta:'2026-12-31'});
 assert.equal(periodoRapido('ano','2026-09-19').desde,'2026-01-01');
});
