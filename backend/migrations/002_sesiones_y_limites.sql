-- Durable opaque sessions. Provider tokens never leave the server.
ALTER TABLE broquer.usuarios ADD COLUMN actualizado_en timestamptz NOT NULL DEFAULT now();
CREATE TABLE broquer.sesiones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), usuario_id uuid NOT NULL REFERENCES auth.users(id),
 token_hash text NOT NULL UNIQUE CHECK(length(token_hash)=64), credenciales_cifradas text NOT NULL,
 proposito text NOT NULL DEFAULT 'normal' CHECK(proposito IN ('normal','recuperacion')),
 expira_en timestamptz NOT NULL, revocada_en timestamptz, creado_en timestamptz NOT NULL DEFAULT now(), ultimo_uso timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sesiones_por_usuario ON broquer.sesiones(usuario_id) WHERE revocada_en IS NULL;
CREATE TABLE broquer.limites_solicitudes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), clave_hash text NOT NULL CHECK(length(clave_hash)=64),
 ventana bigint NOT NULL, usadas integer NOT NULL CHECK(usadas>0), expira_en timestamptz NOT NULL,
 UNIQUE(clave_hash,ventana)
);
ALTER TABLE broquer.sesiones ENABLE ROW LEVEL SECURITY;
ALTER TABLE broquer.limites_solicitudes ENABLE ROW LEVEL SECURITY;
CREATE POLICY sesion_leer ON broquer.sesiones FOR SELECT TO broquer_api USING(
 token_hash=nullif(current_setting('broquer.sesion_hash',true),'') OR usuario_id=broquer.usuario_actual());
CREATE POLICY sesion_crear ON broquer.sesiones FOR INSERT TO broquer_api WITH CHECK(
 usuario_id=broquer.usuario_actual() AND token_hash=nullif(current_setting('broquer.sesion_hash',true),''));
CREATE POLICY sesion_editar ON broquer.sesiones FOR UPDATE TO broquer_api USING(
 token_hash=nullif(current_setting('broquer.sesion_hash',true),'') OR usuario_id=broquer.usuario_actual()) WITH CHECK(
 token_hash=nullif(current_setting('broquer.sesion_hash',true),'') OR usuario_id=broquer.usuario_actual());
CREATE POLICY limite_propio ON broquer.limites_solicitudes FOR ALL TO broquer_api USING(
 clave_hash=nullif(current_setting('broquer.limite_hash',true),'')) WITH CHECK(
 clave_hash=nullif(current_setting('broquer.limite_hash',true),''));
GRANT SELECT,INSERT ON broquer.sesiones,broquer.limites_solicitudes TO broquer_api;
GRANT UPDATE(credenciales_cifradas,ultimo_uso,revocada_en,proposito) ON broquer.sesiones TO broquer_api;
GRANT UPDATE(usadas) ON broquer.limites_solicitudes TO broquer_api;
GRANT UPDATE(actualizado_en) ON broquer.usuarios TO broquer_api;
ALTER TABLE broquer.trabajos ADD COLUMN resultado jsonb;
ALTER TABLE broquer.trabajos ADD COLUMN error_codigo text;
ALTER TABLE broquer.trabajos ADD COLUMN max_intentos integer NOT NULL DEFAULT 5 CHECK(max_intentos BETWEEN 1 AND 20);
CREATE TABLE broquer.archivos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id), asignado_a uuid NOT NULL REFERENCES broquer.usuarios(id),
 nombre text NOT NULL, ruta text NOT NULL UNIQUE, mime text NOT NULL, tamano bigint NOT NULL CHECK(tamano BETWEEN 1 AND 10485760),
 creado_en timestamptz NOT NULL DEFAULT now(), actualizado_en timestamptz NOT NULL DEFAULT now(), archivado_en timestamptz
);
ALTER TABLE broquer.archivos ENABLE ROW LEVEL SECURITY;
CREATE POLICY archivo_visible ON broquer.archivos FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual() AND archivado_en IS NULL);
-- Uploads are not enabled before validation + private storage provisioning.
GRANT SELECT ON broquer.archivos TO broquer_api;
