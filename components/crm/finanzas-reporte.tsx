'use client';
import {useEffect,useState} from 'react';
import {Button} from '@/components/ui/button';
import {SelectorInventario as Elegir} from './inmueble-formulario';
import {api} from '@/lib/broquer-api';
import {agruparFinanzas,centavos,dinero,type AgrupacionFin,type GrupoFin,type MovimientoFin} from '@/lib/finanzas';
export function FinanzasReporte({demo,movs,propiedades,desde,hasta,cuenta,moneda,revision}:{demo:boolean;movs:MovimientoFin[];propiedades:{id:string;nombre:string}[];desde:string;hasta:string;cuenta:string;moneda:string;revision:number}){
 const [agrupacion,setAgrupacion]=useState<AgrupacionFin>('mes'),[grupos,setGrupos]=useState<GrupoFin[]>([]),[cargando,setCargando]=useState(!demo),[error,setError]=useState(''),[reintento,setReintento]=useState(0);
 const valido=!!desde&&!!hasta&&desde<=hasta;
 useEffect(()=>{
  if(demo||!valido){setGrupos([]);setCargando(false);return}
  let activo=true;setCargando(true);setError('');
  const params=new URLSearchParams({desde,hasta,agrupacion});if(cuenta!=='todas')params.set('cuenta_id',cuenta);
  void api<{grupos:GrupoFin[]}>('finanzas/reporte?'+params).then(r=>{if(activo)setGrupos(r.grupos)}).catch(e=>{if(activo){setGrupos([]);setError(e instanceof Error?e.message:'No pudimos generar el reporte.')}}).finally(()=>{if(activo)setCargando(false)});
  return()=>{activo=false};
 },[demo,valido,desde,hasta,cuenta,agrupacion,revision,reintento]);
 const filas=(valido?(demo?agruparFinanzas(movs,agrupacion,propiedades):grupos):[]).filter(g=>g.moneda===moneda);
 const max=filas.reduce((v,g)=>[centavos(g.ingresos),centavos(g.gastos)].reduce((a,b)=>a>b?a:b,v),BigInt(1));
 const porcentaje=(v:string)=>Number(centavos(v)*BigInt(10000)/max)/100;
 return <section className="fin-reporte" aria-label="Reporte financiero"><div className="seccion-titulo"><h2>Detalle del periodo</h2><Elegir label="Agrupar por" value={agrupacion} onChange={v=>setAgrupacion(v as AgrupacionFin)} items={[{id:'mes',nombre:'Mes'},{id:'categoria',nombre:'Categoría'},{id:'inmueble',nombre:'Inmueble'}]}/></div><p className="fin-aclaracion">Incluye todo el periodo seleccionado. El resultado considera únicamente los ingresos y gastos registrados; no es una estimación del valor del inmueble.</p>{cargando?<p role="status">Generando reporte…</p>:error?<div role="alert" className="mensaje-form es-error">{error}<Button variant="ghost" onClick={()=>setReintento(v=>v+1)}>Reintentar</Button></div>:!filas.length?<p className="estado">Sin ingresos ni gastos para este periodo y moneda.</p>:<><div className="fin-leyenda"><span><i className="ingreso"/>Ingresos</span><span><i className="gasto"/>Gastos</span></div><div className="fin-reporte-filas">{filas.map(g=><article className="fin-reporte-fila" key={g.clave}><div className="fin-reporte-nombre"><h3>{agrupacion==='mes'?new Intl.DateTimeFormat('es-MX',{month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(g.clave+'-01T12:00:00Z')):g.nombre}</h3><span>{g.movimientos} {g.movimientos===1?'movimiento':'movimientos'}</span></div><dl><div><dt>Ingresos</dt><dd>{dinero(g.ingresos,moneda)}</dd></div><div><dt>Gastos</dt><dd>{dinero(g.gastos,moneda)}</dd></div><div className="fin-reporte-resultado"><dt>Resultado</dt><dd>{dinero(g.resultado,moneda)}</dd></div></dl><div className="fin-barras" aria-hidden="true"><i className="ingreso" style={{width:porcentaje(g.ingresos)+'%'}}/><i className="gasto" style={{width:porcentaje(g.gastos)+'%'}}/></div></article>)}</div></>}</section>
}
