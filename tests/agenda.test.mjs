import test from 'node:test';
import assert from 'node:assert/strict';
import {calendarioICS,convertirLocal,fechaLocal,seEmpalman} from '../lib/agenda.ts';
test('hora de México independiente del navegador',()=>{
 assert.equal(convertirLocal('2026-09-20T10:35','America/Mexico_City'),'2026-09-20T16:35:00.000Z');
 assert.equal(fechaLocal('2026-09-20T16:35:00Z','America/Mexico_City'),'2026-09-20T10:35');
});
test('citas contiguas no son conflicto',()=>{
 assert.equal(seEmpalman({inicio:'2026-09-20T16:00Z',duracion_min:30},{inicio:'2026-09-20T16:30Z',duracion_min:30}),false);
 assert.equal(seEmpalman({inicio:'2026-09-20T16:00Z',duracion_min:31},{inicio:'2026-09-20T16:30Z',duracion_min:30}),true);
});
test('ICS escapa saltos, conserva UTC y limita líneas UTF-8',()=>{
 const ics=calendarioICS({id:'prueba',titulo:'Visita\nBEGIN:VEVENT,'+'á'.repeat(100),inicio:'2026-09-20T16:35Z',duracion_min:45,descripcion:'A;B',ubicacion:'C,D',actualizado_en:'2026-09-18T12:00Z'});
 assert.ok(ics.includes('DTSTART:20260920T163500Z\r\nDTEND:20260920T172000Z'));
 assert.equal(ics.split('\r\n').filter(l=>l==='BEGIN:VEVENT').length,1);
 assert.ok(ics.includes('Visita\\nBEGIN:VEVENT\\,'));
 for(const l of ics.split('\r\n'))assert.ok(Buffer.byteLength(l)<=75);
});
