import {useSyncExternalStore,type AnchorHTMLAttributes} from 'react';
const cambio=()=>window.dispatchEvent(new Event('broquer:navigation'));
export function navegar(url:string,replace=false){if(!url.startsWith('/')||url.startsWith('//'))return;window.history[replace?'replaceState':'pushState']({},'',url);cambio();window.scrollTo(0,0)}
export function useRuta(){return useSyncExternalStore(fn=>{window.addEventListener('popstate',fn);window.addEventListener('broquer:navigation',fn);return()=>{window.removeEventListener('popstate',fn);window.removeEventListener('broquer:navigation',fn)}},()=>window.location.pathname,()=>'/')}
export function useRouter(){return {push:(url:string)=>navegar(url),replace:(url:string)=>navegar(url,true)}}
export default function Link({href,onClick,...props}:AnchorHTMLAttributes<HTMLAnchorElement> & {href:string}){return <a {...props} href={href} onClick={e=>{onClick?.(e);if(!e.defaultPrevented&&href.startsWith('/')&&!href.startsWith('//')&&!e.metaKey&&!e.ctrlKey){e.preventDefault();navegar(href)}}}/>}
