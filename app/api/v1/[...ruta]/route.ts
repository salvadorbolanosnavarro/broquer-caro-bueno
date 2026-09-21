// Same-origin BFF: only the Python API owns business rules and provider credentials.
import { env } from 'cloudflare:workers';
const error = (status:number,codigo:string,mensaje_usuario:string) => Response.json({codigo,mensaje_usuario},{status,headers:{'Cache-Control':'no-store'}});
async function leerCuerpo(request:Request) {
 if(!request.body)return undefined;
 const reader=request.body.getReader(); const partes:Uint8Array[]=[]; let total=0;
 try {while(true){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>32768){await reader.cancel();throw new Error('limite')}partes.push(value)}}finally{reader.releaseLock()}
 const bytes=new Uint8Array(total);let offset=0;for(const p of partes){bytes.set(p,offset);offset+=p.length}return new TextDecoder().decode(bytes);
}
async function proxy(request:Request,{params}:{params:Promise<{ruta:string[]}>}) {
 const runtime=env as unknown as Record<string,string|undefined>;
 const base=runtime.BROQUER_API_URL,secret=runtime.BROQUER_PROXY_SECRET;
 if(!base||!secret)return error(503,'conexion_pendiente','El acceso a cuentas todavía no está conectado. Puedes recorrer la demo sin registrarte.');
 let baseUrl:URL;try{baseUrl=new URL(base)}catch{return error(503,'configuracion_invalida','El servicio no está disponible.')}
 if(baseUrl.protocol!=='https:'||baseUrl.username||baseUrl.password||baseUrl.search||baseUrl.hash)return error(503,'configuracion_invalida','El servicio no está disponible.');
 const {ruta}=await params;
 if(ruta.some(x=>!/^[-a-zA-Z0-9_]+$/.test(x)))return error(404,'no_encontrado','No se encontró esta función.');
 const lectura=['GET','HEAD'].includes(request.method),origen=new URL(request.url).origin;
 if(!lectura&&request.headers.get('origin')!==origen)return error(403,'origen_invalido','Vuelve a abrir Broquer e inténtalo otra vez.');
 if(!lectura&&!request.headers.get('content-type')?.startsWith('application/json'))return error(415,'formato_invalido','No se pudo leer la solicitud.');
 let body:string|undefined;
 try{body=lectura?undefined:await leerCuerpo(request)}catch{return error(413,'demasiado_grande','La solicitud es demasiado grande.')}
 try {
  const h=new Headers({'Content-Type':'application/json','Origin':origen,'X-Broquer-Proxy':secret,'X-Broquer-Client-IP':request.headers.get('cf-connecting-ip')||'desconocido'});
  const cookie=request.headers.get('cookie');if(cookie)h.set('Cookie',cookie.split(';').filter(x=>/^\s*broquer_(sesion|refresh|pkce)=/.test(x)).join(';'));
  const respuesta=await fetch(base.replace(/\/$/,'')+'/v1/'+ruta.join('/')+new URL(request.url).search,{method:request.method,headers:h,body,redirect:'manual',signal:AbortSignal.timeout(25000)});
  if(respuesta.status>=300&&respuesta.status<400)return error(502,'respuesta_invalida','No se pudo completar la solicitud.');
  const headers=new Headers({'Content-Type':'application/json','Cache-Control':'no-store','Referrer-Policy':'no-referrer'});
  for(const c of respuesta.headers.getSetCookie())if(/^broquer_(sesion|refresh|pkce)=/.test(c))headers.append('Set-Cookie',c);
  const retry=respuesta.headers.get('retry-after');if(retry)headers.set('Retry-After',retry);
  return new Response(respuesta.body,{status:respuesta.status,headers});
 } catch {return error(503,'servicio_no_disponible','La conexión se interrumpió. Revisa el estado de la operación antes de volver a intentar.')}
}
export const GET=proxy;export const POST=proxy;export const PATCH=proxy;
