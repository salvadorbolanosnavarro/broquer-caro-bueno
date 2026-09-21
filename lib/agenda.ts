export type Tarea={id:string;titulo:string;tipo:string;inicio:string;duracion_min:number;descripcion:string;ubicacion:string;completada_en:string|null;actualizado_en:string;oportunidad_id:string|null;oportunidad_titulo?:string|null;propiedad_id?:string|null;propiedad_titulo?:string|null};
export const tiposTarea=[{id:'llamada',nombre:'Llamada'},{id:'visita',nombre:'Visita'},{id:'cita',nombre:'Cita'},{id:'seguimiento',nombre:'Seguimiento'},{id:'tramite',nombre:'Trámite'},{id:'otro',nombre:'Otro'}];
export function fechaLocal(fecha:string,zona:string){
 const partes=new Intl.DateTimeFormat('en-CA',{timeZone:zona,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(fecha));
 const p=Object.fromEntries(partes.map(x=>[x.type,x.value]));return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}
export function convertirLocal(local:string,zona:string){
 const objetivo=Date.parse(local+'Z');let fecha=objetivo;
 for(let i=0;i<4;i++){const vista=Date.parse(fechaLocal(new Date(fecha).toISOString(),zona)+'Z');fecha+=objetivo-vista;}
 if(fechaLocal(new Date(fecha).toISOString(),zona)!==local)throw new Error('Esa hora no existe por el cambio de horario. Elige otra.');
 return new Date(fecha).toISOString();
}
export function seEmpalman(a:Pick<Tarea,'inicio'|'duracion_min'>,b:Pick<Tarea,'inicio'|'duracion_min'>){return Date.parse(a.inicio)<Date.parse(b.inicio)+b.duracion_min*60000&&Date.parse(b.inicio)<Date.parse(a.inicio)+a.duracion_min*60000;}
export function calendarioICS(t:Tarea){
 const escapar=(s:string)=>s.replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/\r/g,'');
 const fecha=(s:string)=>new Date(s).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
 const lineas=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Broquer//Agenda//ES','CALSCALE:GREGORIAN','BEGIN:VEVENT',`UID:${t.id}@broquer`, `DTSTAMP:${fecha(t.actualizado_en)}`,`DTSTART:${fecha(t.inicio)}`,`DTEND:${fecha(new Date(Date.parse(t.inicio)+t.duracion_min*60000).toISOString())}`,`SUMMARY:${escapar(t.titulo)}`,`DESCRIPTION:${escapar(t.descripcion)}`,`LOCATION:${escapar(t.ubicacion)}`,'END:VEVENT','END:VCALENDAR'];
 // RFC 5545 folding counts UTF-8 octets, not JS characters.
 return lineas.map(linea=>{let salida='',col=0;for(const c of linea){const n=new TextEncoder().encode(c).length;if(col+n>75){salida+='\r\n ';col=1}salida+=c;col+=n}return salida}).join('\r\n')+'\r\n';
}
