'use client';
import {useSyncExternalStore,type SetStateAction} from 'react';
export type ContactoDemo={id:string;nombre:string;empresa:string;telefono:string|null;email:string|null;actualizado_en:string;puede_editar:boolean;puede_ver_telefono:boolean};
const iniciales:ContactoDemo[]=[{id:'demo-1',nombre:'Mariana Torres',empresa:'',telefono:'+524430000001',email:'mariana@example.test',actualizado_en:'',puede_editar:true,puede_ver_telefono:true},{id:'demo-2',nombre:'Daniel Mendoza',empresa:'Inversionista',telefono:null,email:'daniel@example.test',actualizado_en:'',puede_editar:true,puede_ver_telefono:true}];
let contactos=iniciales;
const listeners=new Set<()=>void>();
function subscribe(fn:()=>void){listeners.add(fn);return()=>{listeners.delete(fn)}}
function actualizar(cambio:SetStateAction<ContactoDemo[]>){contactos=typeof cambio==='function'?cambio(contactos):cambio;listeners.forEach(fn=>fn())}
// Memory only: no business data in browser storage. Reload restores fictitious examples.
export function useContactosDemo(){return [useSyncExternalStore(subscribe,()=>contactos,()=>iniciales),actualizar] as const}
