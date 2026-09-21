'use client';
import type {AnchorHTMLAttributes} from 'react';
// Web module entry uses a document navigation, independent of the SPA router.
// Capacitor keeps its bundled navigation so the native shell stays local.
export function EnlaceModulo({href,onClick,...props}:AnchorHTMLAttributes<HTMLAnchorElement>&{href:string}){
 return <a {...props} href={href} onClick={e=>{
  onClick?.(e);
  if(!e.defaultPrevented&&window.location.protocol==='capacitor:'&&href.startsWith('/')&&!href.startsWith('//')&&!e.metaKey&&!e.ctrlKey){
   e.preventDefault();window.history.pushState({},'',href);window.dispatchEvent(new Event('broquer:navigation'));window.scrollTo(0,0);
  }
 }}/>;
}
