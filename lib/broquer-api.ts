export class ErrorBroquer extends Error {
 constructor(public codigo:string,mensaje:string,public estado:number){super(mensaje)}
}
export async function api<T>(ruta:string,datos?:unknown,metodo?:'POST'|'PATCH',signal?:AbortSignal):Promise<T>{
 if(typeof window!=='undefined'&&window.location.protocol==='capacitor:'){
  if(ruta==='estado')return {acceso_disponible:false,registro_disponible:false,google_disponible:false} as T;
  throw new ErrorBroquer('movil_pendiente','El acceso a cuentas todavía no está habilitado en esta versión.',503);
 }
 let respuesta:Response;
 try{respuesta=await fetch('/api/v1/'+ruta,{method:metodo||(datos===undefined?'GET':'POST'),headers:datos===undefined?undefined:{'Content-Type':'application/json'},body:datos===undefined?undefined:JSON.stringify(datos),credentials:'same-origin',cache:'no-store',signal})}
 catch(error){if(signal?.aborted)throw error;throw new ErrorBroquer('sin_conexion','No pudimos conectar. Revisa tu conexión e intenta de nuevo.',0)}
 let contenido:unknown;try{contenido=await respuesta.json()}catch{throw new ErrorBroquer('respuesta_invalida','No pudimos leer la respuesta. Intenta de nuevo.',respuesta.status)}
 if(!respuesta.ok){const d=contenido as {codigo?:string;mensaje_usuario?:string};throw new ErrorBroquer(d.codigo||'error',d.mensaje_usuario||'No pudimos completar la solicitud.',respuesta.status)}
 return contenido as T;
}
export type PerfilBroquer={perfil_completo:boolean;recuperacion?:boolean;nombre:string;apellidos:string;email:string;telefono:string;zona_horaria:string;organizacion:string;org_id:string;plan:string;permisos?:Record<string,boolean>};
export type EstadoConexion={acceso_disponible:boolean;registro_disponible:boolean;google_disponible:boolean};
