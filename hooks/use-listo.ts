'use client';
import {useEffect,useState} from 'react';
// Do not present interactive actions as available before their handlers mount.
export function useListo(){const [listo,setListo]=useState(false);useEffect(()=>setListo(true),[]);return listo}
