ALTER TABLE broquer.contactos ADD CONSTRAINT contacto_org_identidad UNIQUE(org_id,id);
CREATE TABLE broquer.etapas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 nombre text NOT NULL CHECK(length(nombre) BETWEEN 1 AND 80),orden integer NOT NULL CHECK(orden>=0),
 tipo text NOT NULL CHECK(tipo IN ('abierta','ganada','perdida')),
 UNIQUE(org_id,id),UNIQUE(org_id,orden)
);
CREATE TABLE broquer.oportunidades (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),asignado_a uuid NOT NULL REFERENCES broquer.usuarios(id),
 contacto_id uuid NOT NULL,etapa_id uuid NOT NULL,titulo text NOT NULL CHECK(length(titulo) BETWEEN 1 AND 160),
 tipo text NOT NULL CHECK(tipo IN ('compra','renta','venta','arrendamiento')),
 presupuesto numeric(16,2) CHECK(presupuesto>=0),moneda text NOT NULL DEFAULT 'MXN' CHECK(moneda IN ('MXN','USD')),
 zona text NOT NULL DEFAULT '',temperatura text NOT NULL DEFAULT 'nuevo' CHECK(temperatura IN ('nuevo','frio','tibio','caliente')),
 motivo_perdida text,creado_en timestamptz NOT NULL DEFAULT now(),actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(org_id,id),FOREIGN KEY(org_id,contacto_id) REFERENCES broquer.contactos(org_id,id),
 FOREIGN KEY(org_id,etapa_id) REFERENCES broquer.etapas(org_id,id)
);
CREATE TABLE broquer.historial_etapas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL, oportunidad_id uuid NOT NULL,
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),anterior_id uuid,nueva_id uuid NOT NULL,motivo text,
 creado_en timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,oportunidad_id) REFERENCES broquer.oportunidades(org_id,id),
 FOREIGN KEY(org_id,anterior_id) REFERENCES broquer.etapas(org_id,id),
 FOREIGN KEY(org_id,nueva_id) REFERENCES broquer.etapas(org_id,id)
);
CREATE TABLE broquer.actividades (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL,oportunidad_id uuid NOT NULL,
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),tipo text NOT NULL CHECK(tipo IN ('cambio_etapa','nota','sistema')),
 texto text NOT NULL CHECK(length(texto) BETWEEN 1 AND 4000),creado_en timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,oportunidad_id) REFERENCES broquer.oportunidades(org_id,id)
);
CREATE INDEX oportunidades_por_responsable ON broquer.oportunidades(org_id,asignado_a,etapa_id);
CREATE INDEX actividad_por_oportunidad ON broquer.actividades(oportunidad_id,creado_en DESC);
ALTER TABLE broquer.etapas ENABLE ROW LEVEL SECURITY;
CREATE POLICY etapa_visible ON broquer.etapas FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id));
CREATE POLICY etapa_crear ON broquer.etapas FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND EXISTS(
 SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=etapas.org_id AND m.usuario_id=broquer.usuario_actual() AND m.rol_org IN ('owner','admin')));
ALTER TABLE broquer.oportunidades ENABLE ROW LEVEL SECURITY;
CREATE POLICY oportunidad_propia ON broquer.oportunidades FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND (creado_por=broquer.usuario_actual() OR asignado_a=broquer.usuario_actual()));
CREATE POLICY oportunidad_crear ON broquer.oportunidades FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual() AND asignado_a=broquer.usuario_actual());
CREATE POLICY oportunidad_editar ON broquer.oportunidades FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND (creado_por=broquer.usuario_actual() OR asignado_a=broquer.usuario_actual())) WITH CHECK(broquer.es_miembro(org_id));
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['historial_etapas','actividades'] LOOP
 EXECUTE format('ALTER TABLE broquer.%I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY registro_visible ON broquer.%I FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND EXISTS(SELECT 1 FROM broquer.oportunidades o WHERE o.id=oportunidad_id AND o.org_id=org_id))',t);
 EXECUTE format('CREATE POLICY registro_crear ON broquer.%I FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual() AND EXISTS(SELECT 1 FROM broquer.oportunidades o WHERE o.id=oportunidad_id AND o.org_id=org_id))',t);
 END LOOP; END $$;
GRANT SELECT,INSERT ON broquer.etapas,broquer.oportunidades,broquer.historial_etapas,broquer.actividades TO broquer_api;
GRANT UPDATE(etapa_id,motivo_perdida,actualizado_en) ON broquer.oportunidades TO broquer_api;
