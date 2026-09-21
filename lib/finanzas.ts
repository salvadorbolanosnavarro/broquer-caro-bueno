export type CuentaFin={id:string;nombre:string;tipo:string;moneda:string;saldo_inicial:string;saldo:string;activa:boolean;actualizado_en:string};
export type CategoriaFin={id:string;nombre:string;tipo:'ingreso'|'gasto'};
export type MovimientoFin={id:string;tipo:'ingreso'|'gasto'|'transferencia';monto:string;moneda:string;fecha:string;concepto:string;notas:string;cuenta_id:string;cuenta_destino_id:string|null;categoria_id:string|null;propiedad_id:string|null;contacto_id:string|null;anulada_en:string|null;motivo_anulacion:string|null;actualizado_en:string;cuenta_nombre?:string;destino_nombre?:string;categoria_nombre?:string;contacto_nombre?:string};
export type ResumenFin={moneda:string;ingresos:string;gastos:string;resultado:string};
export function centavos(valor:string){if(!/^-?\d+(\.\d{1,2})?$/.test(valor))throw new Error('Escribe un monto válido con hasta dos decimales.');const negativo=valor.startsWith('-'),[entero,decimal='']=valor.replace('-','').split('.');return (BigInt(entero)*BigInt(100)+BigInt(decimal.padEnd(2,'0')))*(negativo?BigInt(-1):BigInt(1))}
export function decimalMoneda(c:bigint){const neg=c<BigInt(0);if(neg)c=-c;return (neg?'-':'')+(c/BigInt(100)).toString()+'.'+(c%BigInt(100)).toString().padStart(2,'0')}
export function dinero(valor:string,moneda:string){const c=centavos(valor),abs=c<BigInt(0)?-c:c;return (c<BigInt(0)?'−':'')+'$'+new Intl.NumberFormat('es-MX').format(abs/BigInt(100))+'.'+(abs%BigInt(100)).toString().padStart(2,'0')+' '+moneda}
export function calcularSaldos(cuentas:CuentaFin[],movs:MovimientoFin[]){return cuentas.map(c=>({...c,saldo:decimalMoneda(movs.filter(m=>!m.anulada_en).reduce((s,m)=>s+(m.cuenta_id===c.id?(m.tipo==='ingreso'?centavos(m.monto):-centavos(m.monto)):m.cuenta_destino_id===c.id?centavos(m.monto):BigInt(0)),centavos(c.saldo_inicial)))}))}
export function resumir(movs:MovimientoFin[]):ResumenFin[]{return ['MXN','USD'].map(moneda=>{const xs=movs.filter(m=>m.moneda===moneda&&!m.anulada_en),suma=(tipo:string)=>xs.filter(m=>m.tipo===tipo).reduce((s,m)=>s+centavos(m.monto),BigInt(0)),ingresos=suma('ingreso'),gastos=suma('gasto');return {moneda,ingresos:decimalMoneda(ingresos),gastos:decimalMoneda(gastos),resultado:decimalMoneda(ingresos-gastos)}})}
export function llaveRegistro(){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;const h=Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`}
export function fechaHoy(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
export function csvMovimientos(ms:MovimientoFin[]){const celda=(s:string)=>'"'+(/^[\s]*[=+\-@]|^[\t\r\n]/.test(s)?"'"+s:s).replaceAll('"','""')+'"';const lineas=[['Fecha','Tipo','Concepto','Monto','Moneda','Cuenta','Destino','Categoría','Estado'],...ms.map(m=>[m.fecha,m.tipo,m.concepto,m.monto,m.moneda,m.cuenta_nombre||'',m.destino_nombre||'',m.categoria_nombre||'',m.anulada_en?'Anulado':'Vigente'])];return '\uFEFF'+lineas.map(l=>l.map(celda).join(',')).join('\r\n')}

export type AgrupacionFin='mes'|'categoria'|'inmueble';
export type GrupoFin=ResumenFin&{clave:string;nombre:string;movimientos:number};
export function agruparFinanzas(movs:MovimientoFin[],agrupacion:AgrupacionFin,propiedades:{id:string;nombre:string}[]=[]):GrupoFin[]{
 const grupos=new Map<string,{clave:string;nombre:string;moneda:string;ingresos:bigint;gastos:bigint;movimientos:number}>();
 for(const m of movs){
  if(m.anulada_en||m.tipo==='transferencia')continue;
  const propiedad=propiedades.find(p=>p.id===m.propiedad_id);
  const clave=agrupacion==='mes'?m.fecha.slice(0,7):agrupacion==='categoria'?m.categoria_id||'sin_categoria':propiedad?.id||'sin_inmueble';
  const nombre=agrupacion==='mes'?clave:agrupacion==='categoria'?m.categoria_nombre||'Sin categoría':propiedad?.nombre||'Sin inmueble visible';
  const id=JSON.stringify([clave,m.moneda]);
  const g=grupos.get(id)||{clave,nombre,moneda:m.moneda,ingresos:BigInt(0),gastos:BigInt(0),movimientos:0};
  g[m.tipo==='ingreso'?'ingresos':'gastos']+=centavos(m.monto);g.movimientos++;grupos.set(id,g);
 }
 return [...grupos.values()].sort((a,b)=>a.clave.localeCompare(b.clave)||a.moneda.localeCompare(b.moneda)).map(g=>({...g,ingresos:decimalMoneda(g.ingresos),gastos:decimalMoneda(g.gastos),resultado:decimalMoneda(g.ingresos-g.gastos)}));
}
export function periodoRapido(tipo:'mes'|'trimestre'|'ano',hoy=fechaHoy()){
 const [a,m]=hoy.split('-').map(Number);
 const mes=tipo==='ano'?1:tipo==='trimestre'?Math.floor((m-1)/3)*3+1:m;
 return {desde:`${a}-${String(mes).padStart(2,'0')}-01`,hasta:hoy};
}
