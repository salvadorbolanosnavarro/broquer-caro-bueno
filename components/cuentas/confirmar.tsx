'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';
import {ArrowRight,MailCheck,LoaderCircle,KeyRound} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {api,type PerfilBroquer} from '@/lib/broquer-api';
import {CampoContrasena} from './acceso';
export function Confirmar(){
 const router=useRouter();const [listo,setListo]=useState(false),[recuperacion,setRecuperacion]=useState(false),[ocupado,setOcupado]=useState(false),[mensaje,setMensaje]=useState(''),[error,setError]=useState(false);
 const [tipo,setTipo]=useState('');const entrada=useRef<{token_hash?:string;codigo?:string;tipo?:string}>({});const [valido,setValido]=useState<boolean|null>(null);
 useEffect(()=>{const p=new URLSearchParams(window.location.search);const codigo=p.get('code'),token=p.get('token_hash'),t=p.get('type');entrada.current=codigo?{codigo}:token&&['email','recovery'].includes(t||'')?{token_hash:token,tipo:t!}:{};setTipo(t||'');setValido(!!(entrada.current.codigo||entrada.current.token_hash));window.history.replaceState({},'',window.location.pathname);},[]);
 async function confirmar(){setOcupado(true);setMensaje('');setError(false);try{const e=entrada.current;const d=await api<PerfilBroquer>(e.codigo?'auth/google/confirmar':'auth/confirmar',e);setValido(false);entrada.current={};if(d.recuperacion){setRecuperacion(true);setListo(true)}else router.replace(d.perfil_completo?'/mi-espacio':'/perfil');}catch(e){setError(true);setMensaje(e instanceof Error?e.message:'No pudimos confirmar tu cuenta.')}finally{setOcupado(false)}}
 async function cambiar(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);if(f.get('nueva')!==f.get('confirmacion')){setError(true);setMensaje('Las contraseñas no coinciden.');return}setOcupado(true);setMensaje('');try{const d=await api<{mensaje_usuario:string}>('auth/contrasena',{nueva:f.get('nueva')});setMensaje(d.mensaje_usuario);setRecuperacion(false);setListo(true);setError(false)}catch(e){setError(true);setMensaje(e instanceof Error?e.message:'No se pudo cambiar la contraseña.')}finally{setOcupado(false)}}
 return <main className="cuenta-centrada"><Link href="/" className="marca">broquer<span className="marca-punto"/></Link><section className="acceso-formulario"><span className="icono-confirmar">{tipo==='recovery'?<KeyRound size={28}/>:<MailCheck size={28}/>}</span><h1>{recuperacion?'Tu nueva contraseña':listo?'Ya puedes volver a entrar':tipo==='recovery'?'Recupera tu cuenta':'Confirma tu acceso'}</h1><p>{recuperacion?'Elige una contraseña de al menos 12 caracteres.':valido?'Continúa para verificar el enlace que recibiste.':!listo?'Abre el enlace de tu correo. Si venció o ya se utilizó, solicita uno nuevo.':''}</p>
 {valido&&<Button className="boton principal" onClick={()=>void confirmar()} disabled={ocupado}>{ocupado?<LoaderCircle className="girar" size={18}/>:null}Continuar<ArrowRight size={18}/></Button>}
 {recuperacion&&<form onSubmit={cambiar}><fieldset disabled={ocupado}><CampoContrasena id="nueva" label="Nueva contraseña" confirmar/><CampoContrasena id="confirmacion" label="Confirma tu contraseña" confirmar/><Button type="submit" className="boton principal" disabled={ocupado}>{ocupado?'Actualizando…':'Guardar contraseña'}</Button></fieldset></form>}
 {mensaje&&<p className={`mensaje-form ${error?'es-error':''}`} role={error?'alert':'status'}>{mensaje}</p>}
 <Link className="volver" href="/acceso">Volver al acceso</Link></section></main>
}
