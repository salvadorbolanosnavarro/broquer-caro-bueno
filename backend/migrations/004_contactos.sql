CREATE TABLE broquer.contactos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id), asignado_a uuid NOT NULL REFERENCES broquer.usuarios(id),
 nombre text NOT NULL CHECK(length(nombre) BETWEEN 1 AND 160), empresa text NOT NULL DEFAULT '',
 telefono text, email text, fuente text NOT NULL DEFAULT 'manual',
 creado_en timestamptz NOT NULL DEFAULT now(), actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
 archivado_en timestamptz, CHECK(telefono IS NOT NULL OR email IS NOT NULL)
);
CREATE UNIQUE INDEX contacto_telefono_unico ON broquer.contactos(org_id,telefono) WHERE telefono IS NOT NULL AND archivado_en IS NULL;
CREATE UNIQUE INDEX contacto_email_unico ON broquer.contactos(org_id,lower(email)) WHERE email IS NOT NULL AND archivado_en IS NULL;
ALTER TABLE broquer.contactos ENABLE ROW LEVEL SECURITY;
CREATE POLICY contacto_leer ON broquer.contactos FOR SELECT TO broquer_api USING (
 broquer.es_miembro(org_id) AND (creado_por=broquer.usuario_actual() OR asignado_a=broquer.usuario_actual() OR
 EXISTS(SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=contactos.org_id AND m.usuario_id=broquer.usuario_actual() AND
 (m.rol_org IN ('owner','admin') OR coalesce((m.permisos->>'ver_contactos_equipo')::boolean,true)))));
CREATE POLICY contacto_crear ON broquer.contactos FOR INSERT TO broquer_api WITH CHECK (
 broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual() AND asignado_a=broquer.usuario_actual());
CREATE POLICY contacto_editar ON broquer.contactos FOR UPDATE TO broquer_api USING (
 broquer.es_miembro(org_id) AND (creado_por=broquer.usuario_actual() OR asignado_a=broquer.usuario_actual() OR
 EXISTS(SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=contactos.org_id AND m.usuario_id=broquer.usuario_actual() AND
 (m.rol_org IN ('owner','admin') OR coalesce((m.permisos->>'editar_registros_ajenos')::boolean,false)))))
 WITH CHECK(broquer.es_miembro(org_id));
GRANT SELECT,INSERT ON broquer.contactos TO broquer_api;
GRANT UPDATE(nombre,empresa,telefono,email,actualizado_en) ON broquer.contactos TO broquer_api;
