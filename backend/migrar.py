"""Versioned, atomic migrations. Requires a separate owner DSN, never runtime credentials."""
import os,hashlib
from pathlib import Path
import psycopg
with psycopg.connect(os.environ['MIGRATIONS_DATABASE_URL']) as db:
    db.execute('SELECT pg_advisory_xact_lock(162026001)')
    db.execute('CREATE TABLE IF NOT EXISTS public.broquer_migraciones(nombre text PRIMARY KEY,sha256 text NOT NULL,aplicada_en timestamptz NOT NULL DEFAULT now())')
    for archivo in sorted(Path(__file__).with_name('migrations').glob('*.sql')):
        contenido=archivo.read_text();sha=hashlib.sha256(contenido.encode()).hexdigest()
        previo=db.execute('SELECT sha256 FROM public.broquer_migraciones WHERE nombre=%s',(archivo.name,)).fetchone()
        if previo:
            if previo[0]!=sha:raise RuntimeError('Applied migration changed: '+archivo.name)
            continue
        db.execute(contenido)
        db.execute('INSERT INTO public.broquer_migraciones(nombre,sha256) VALUES(%s,%s)',(archivo.name,sha))
        print('Applied',archivo.name)
