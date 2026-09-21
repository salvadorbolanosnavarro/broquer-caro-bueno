'use client';
import {useEffect,useState,type FormEvent} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';
import {ArrowLeft,ArrowRight,ShieldCheck,Info,LoaderCircle,Eye,EyeOff} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {api,type EstadoConexion,type PerfilBroquer} from '@/lib/broquer-api';

type Modo='login'|'registro'|'recuperar';
export function CampoContrasena({id,label,confirmar=false}:{id:string;label:string;confirmar?:boolean}){
 const [visible,setVisible]=useState(false);
 return <div><Label htmlFor={id}>{label}</Label><div className="contrasena-campo"><Input id={id} name={id} type={visible?'text':'password'} required minLength={confirmar?12:1} maxLength={128} autoComplete={confirmar?'new-password':'current-password'}/><button type="button" aria-label={visible?'Ocultar contraseña':'Mostrar contraseña'} aria-pressed={visible} onClick={()=>setVisible(!visible)}>{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div></div>
}
export function Acceso(){
 const router=useRouter();const [modo,setModo]=useState<Modo>('login'),[ocupado,setOcupado]=useState(false),[mensaje,setMensaje]=useState(''),[error,setError]=useState(false),[conexion,setConexion]=useState<EstadoConexion|null>(null),[cargando,setCargando]=useState(true);
 async function revisar(){setCargando(true);try{setConexion(await api<EstadoConexion>('estado'))}catch{setConexion({acceso_disponible:false,registro_disponible:false,google_disponible:false})}finally{setCargando(false)}}
 useEffect(()=>{void revisar();},[]);
 function cambiar(m:Modo){setModo(m);setMensaje('');setError(false)}
 const habilitado=conexion?.acceso_disponible&&(modo!=='registro'||conexion.registro_disponible);
 async function enviar(e:FormEvent<HTMLFormElement>){e.preventDefault();setMensaje('');setError(false);setOcupado(true);const f=new FormData(e.currentTarget);const datos=Object.fromEntries(f.entries());
 try{const d=await api<PerfilBroquer&{mensaje_usuario?:string}>(`auth/${modo==='login'?'ingresar':modo==='registro'?'registrar':'recuperar'}`,datos);if(modo==='login')router.push(d.perfil_completo?'/mi-espacio':'/perfil');else setMensaje(d.mensaje_usuario||'Revisa tu correo para continuar.')}catch(e){setError(true);setMensaje(e instanceof Error?e.message:'No pudimos completar la solicitud.')}finally{setOcupado(false)}}
 async function google(){setOcupado(true);setMensaje('');try{const d=await api<{url:string}>('auth/google/iniciar',{});window.location.assign(d.url)}catch(e){setError(true);setMensaje(e instanceof Error?e.message:'No pudimos conectar.');setOcupado(false)}}
 return <div className="acceso-layout"><section className="acceso-presentacion"><span className="sobrelinea">Tu espacio de trabajo</span><h1>Todo empieza<br/>con una buena<br/><span>conexión.</span></h1><p>Tus clientes, tus propiedades y tu siguiente oportunidad. Un solo lugar para hacer que las cosas sucedan.</p><div className="acceso-sello"><ShieldCheck size={22}/><span>Un espacio propio para cada asesor.</span></div></section><section className="acceso-formulario"><Link href="/" className="volver"><ArrowLeft size={16}/>Volver a la demo</Link><h2>{modo==='registro'?'Crea tu cuenta':modo==='recuperar'?'Recupera tu acceso':'Qué bueno verte.'}</h2><p>{modo==='registro'?'Comienza con tu espacio personal.':modo==='recuperar'?'Te enviaremos instrucciones a tu correo.':'Entra a tu espacio de Broquer.'}</p>
 {cargando?<div className="acceso-alerta" role="status"><LoaderCircle className="girar" size={19}/>Comprobando acceso…</div>:!habilitado&&<div className="acceso-alerta"><Info size={19}/><div><p>{conexion?.acceso_disponible?'El alta de nuevas cuentas todavía no está habilitada. Puedes iniciar sesión si ya tienes una cuenta.':'El acceso a cuentas aún no está habilitado. Puedes explorar la demo sin compartir tus datos.'}</p><button type="button" className="texto-boton" onClick={()=>void revisar()}>Volver a comprobar</button></div></div>}
 <form onSubmit={enviar}><fieldset disabled={ocupado||!habilitado||cargando}>{modo==='registro'&&<><div className="form-dos"><div><Label htmlFor="nombre">Nombre</Label><Input id="nombre" name="nombre" required maxLength={80} autoComplete="given-name"/></div><div><Label htmlFor="apellidos">Apellidos</Label><Input id="apellidos" name="apellidos" required maxLength={120} autoComplete="family-name"/></div></div><Label htmlFor="telefono">Celular mexicano (10 dígitos)</Label><Input id="telefono" name="telefono" type="tel" inputMode="numeric" pattern="[0-9]{10}" required autoComplete="tel-national"/></>}
 <Label htmlFor="email">Correo electrónico</Label><Input id="email" name="email" type="email" placeholder="tu@correo.com" required autoComplete="email"/>{modo!=='recuperar'&&<CampoContrasena id="contrasena" label="Contraseña" confirmar={modo==='registro'}/>} {modo==='registro'&&<small>Utiliza al menos 12 caracteres.</small>}
 <Button type="submit" className="boton principal" disabled={ocupado||!habilitado||cargando}>{ocupado?<LoaderCircle className="girar" size={18}/>:null}{modo==='login'?'Entrar a Broquer':modo==='registro'?'Crear mi cuenta':'Enviar instrucciones'}<ArrowRight size={18}/></Button></fieldset></form>
 {conexion?.google_disponible&&modo==='login'&&<Button className="boton secundario" disabled={ocupado} onClick={()=>void google()}>Continuar con Google</Button>}
 {mensaje&&<p className={`mensaje-form ${error?'es-error':''}`} role={error?'alert':'status'}>{mensaje}</p>}
 <div className="alternar-acceso">{modo==='login'?<><button onClick={()=>cambiar('recuperar')}>Olvidé mi contraseña</button><p>¿Primera vez aquí? <button onClick={()=>cambiar('registro')}>Crear cuenta</button></p></>:<button onClick={()=>cambiar('login')}>Ya tengo cuenta. Iniciar sesión</button>}</div>
 </section></div>
}
