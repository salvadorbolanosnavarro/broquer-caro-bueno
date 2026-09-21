'use client';
import {useEffect,useId,useState} from 'react';
import {ChevronsUpDown,Check} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Label} from '@/components/ui/label';
import {Popover,PopoverContent,PopoverTrigger} from '@/components/ui/popover';
import {Command,CommandInput,CommandList,CommandItem} from '@/components/ui/command';
import {useContactosDemo} from '@/lib/crm-demo';
import {api} from '@/lib/broquer-api';
export type ContactoElegible={id:string;nombre:string;empresa?:string;email?:string|null};
export function SelectorContacto({demo=false,valor,onChange,label='Contacto',disabled=false,opcional=false}:{demo?:boolean;valor:ContactoElegible|null;onChange:(c:ContactoElegible|null)=>void;label?:string;disabled?:boolean;opcional?:boolean}){
 const id=useId(),[abierto,setAbierto]=useState(false),[busqueda,setBusqueda]=useState(''),[filas,setFilas]=useState<ContactoElegible[]>([]),[cargando,setCargando]=useState(false),[error,setError]=useState(''),[mas,setMas]=useState(false),[intento,setIntento]=useState(0);
 const [locales]=useContactosDemo();
 useEffect(()=>{
  if(!abierto)return;
  let vigente=true;const controller=new AbortController();setError('');setFilas([]);setMas(false);setCargando(true);
  const timer=setTimeout(()=>{
   if(demo){const q=busqueda.trim().toLocaleLowerCase('es');const xs=locales.filter(c=>[c.nombre,c.empresa,c.email].some(v=>v?.toLocaleLowerCase('es').includes(q)));setFilas(xs.slice(0,30));setMas(xs.length>30);setCargando(false);return}
   void api<{contactos:ContactoElegible[];hay_mas:boolean}>('contactos?'+new URLSearchParams({q:busqueda.trim(),limite:'30'}),undefined,undefined,controller.signal).then(r=>{if(vigente){setFilas(r.contactos);setMas(r.hay_mas)}}).catch(e=>{if(vigente&&!controller.signal.aborted)setError(e instanceof Error?e.message:'No pudimos buscar contactos.')}).finally(()=>{if(vigente)setCargando(false)});
  },demo?0:250);
  return()=>{vigente=false;clearTimeout(timer);controller.abort()};
 },[abierto,busqueda,demo,locales,intento]);
 function elegir(c:ContactoElegible|null){onChange(c);setAbierto(false);setBusqueda('')}
 return <div className="selector-contacto"><Label htmlFor={id}>{label}</Label><Popover open={abierto} onOpenChange={setAbierto}><PopoverTrigger asChild><Button id={id} type="button" variant="outline" role="combobox" aria-expanded={abierto} aria-label={label} disabled={disabled} className="selector-contacto-boton"><span>{valor?.nombre||(opcional?'Sin contacto relacionado':'Buscar contacto')}</span><ChevronsUpDown size={16}/></Button></PopoverTrigger><PopoverContent className="selector-contacto-panel" align="start"><Command shouldFilter={false}><CommandInput aria-label="Buscar en el directorio" placeholder="Nombre, empresa o correo…" value={busqueda} onValueChange={setBusqueda} maxLength={160}/><CommandList aria-label="Contactos del directorio">{opcional&&<CommandItem value="sin-contacto" onSelect={()=>elegir(null)}>Sin contacto relacionado</CommandItem>}{cargando?<p role="status" className="selector-contacto-aviso">Buscando contactos…</p>:error?<div role="alert" className="selector-contacto-aviso">{error}<Button type="button" variant="ghost" onClick={()=>setIntento(v=>v+1)}>Reintentar</Button></div>:!filas.length?<p className="selector-contacto-aviso">No encontramos contactos. Prueba otro nombre o agrégalo al Directorio.</p>:filas.map(c=><CommandItem key={c.id} value={c.id} onSelect={()=>elegir(c)}><div><strong>{c.nombre}</strong>{(c.empresa||c.email)&&<small>{[c.empresa,c.email].filter(Boolean).join(' · ')}</small>}</div>{valor?.id===c.id&&<Check size={16}/>}</CommandItem>)}</CommandList>{mas&&<p className="selector-contacto-aviso">Hay más resultados. Escribe un nombre más específico.</p>}</Command></PopoverContent></Popover></div>
}
