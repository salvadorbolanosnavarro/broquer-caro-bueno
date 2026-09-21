CREATE TABLE broquer.tareas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),
 asignado_a uuid NOT NULL REFERENCES broquer.usuarios(id),
 oportunidad_id uuid,
 titulo text NOT NULL CHECK(length(titulo) BETWEEN 1 AND 160),
 tipo text NOT NULL CHECK(tipo IN ('llamada','visita','cita','seguimiento','tramite','otro')),
 inicio timestamptz NOT NULL, duracion_min integer NOT NULL CHECK(duracion_min BETWEEN 5 AND 1440),
 descripcion text NOT NULL DEFAULT '' CHECK(length(descripcion)<=4000),
 ubicacion text NOT NULL DEFAULT '' CHECK(length(ubicacion)<=300),
 completada_en timestamptz, creado_en timestamptz NOT NULL DEFAULT now(),
 actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(org_id,id), FOREIGN KEY(org_id,oportunidad_id) REFERENCES broquer.oportunidades(org_id,id)
);
CREATE INDEX tareas_pendientes ON broquer.tareas(org_id,asignado_a,inicio) WHERE completada_en IS NULL;
ALTER TABLE broquer.tareas ENABLE ROW LEVEL SECURITY;
CREATE POLICY tarea_visible ON broquer.tareas FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND asignado_a=broquer.usuario_actual());
CREATE POLICY tarea_crear ON broquer.tareas FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual() AND asignado_a=broquer.usuario_actual() AND (oportunidad_id IS NULL OR EXISTS(SELECT 1 FROM broquer.oportunidades o WHERE o.id=tareas.oportunidad_id AND o.org_id=tareas.org_id)));
CREATE POLICY tarea_editar ON broquer.tareas FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND asignado_a=broquer.usuario_actual()) WITH CHECK(broquer.es_miembro(org_id) AND asignado_a=broquer.usuario_actual());
GRANT SELECT,INSERT ON broquer.tareas TO broquer_api;
GRANT UPDATE(titulo,tipo,inicio,duracion_min,descripcion,ubicacion,completada_en,actualizado_en) ON broquer.tareas TO broquer_api;
ALTER TABLE broquer.actividades DROP CONSTRAINT actividades_tipo_check;
ALTER TABLE broquer.actividades ADD CONSTRAINT actividades_tipo_check CHECK(tipo IN ('cambio_etapa','nota','sistema','tarea_creada','tarea_completada'));
ALTER TABLE broquer.actividades ADD COLUMN tarea_id uuid;
ALTER TABLE broquer.actividades ADD CONSTRAINT actividad_tarea_org FOREIGN KEY(org_id,tarea_id) REFERENCES broquer.tareas(org_id,id);
