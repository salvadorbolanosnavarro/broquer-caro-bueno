CREATE TABLE broquer.propiedades (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id), asignado_a uuid NOT NULL REFERENCES broquer.usuarios(id),
 titulo text NOT NULL CHECK(length(titulo) BETWEEN 1 AND 160), clave_interna text CHECK(length(clave_interna)<=40),
 tipo text NOT NULL CHECK(tipo IN ('casa','departamento','terreno','local','oficina','bodega','nave_industrial','edificio','rancho','otro')),
 subtipo text NOT NULL DEFAULT '' CHECK(length(subtipo)<=80),
 estatus text NOT NULL DEFAULT 'disponible' CHECK(estatus IN ('disponible','en_proceso','reservada','vendida','rentada','suspendida','no_activa','borrador_whatsapp')),
 estatus_cambiado_en timestamptz NOT NULL DEFAULT now(),
 colonia text NOT NULL CHECK(length(colonia) BETWEEN 1 AND 160), municipio text NOT NULL CHECK(length(municipio) BETWEEN 1 AND 160),
 estado text NOT NULL CHECK(length(estado) BETWEEN 1 AND 100), calle text NOT NULL DEFAULT '' CHECK(length(calle)<=240),
 cp text NOT NULL DEFAULT '' CHECK(cp='' OR cp ~ '^[0-9]{5}$'),
 m2_terreno numeric(14,2) CHECK(m2_terreno>=0),m2_construccion numeric(14,2) CHECK(m2_construccion>=0),
 recamaras integer CHECK(recamaras BETWEEN 0 AND 999),banos numeric(4,1) CHECK(banos BETWEEN 0 AND 999),
 estacionamientos integer CHECK(estacionamientos BETWEEN 0 AND 999),
 descripcion text NOT NULL DEFAULT '' CHECK(length(descripcion)<=10000),
 creado_en timestamptz NOT NULL DEFAULT now(),actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),archivado_en timestamptz,
 UNIQUE(org_id,id)
);
CREATE UNIQUE INDEX propiedad_clave_unica ON broquer.propiedades(org_id,lower(clave_interna)) WHERE clave_interna IS NOT NULL;
CREATE INDEX propiedad_catalogo ON broquer.propiedades(org_id,estatus,actualizado_en DESC);
CREATE TABLE broquer.propiedad_operaciones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL,propiedad_id uuid NOT NULL,
 operacion text NOT NULL CHECK(operacion IN ('venta','renta')),precio numeric(16,2) NOT NULL CHECK(precio>0),
 moneda text NOT NULL CHECK(moneda IN ('MXN','USD')),activa boolean NOT NULL DEFAULT true,
 FOREIGN KEY(org_id,propiedad_id) REFERENCES broquer.propiedades(org_id,id),UNIQUE(propiedad_id,operacion)
);
CREATE FUNCTION broquer.puede_editar_propiedad(propiedad uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM broquer.propiedades p WHERE p.id=propiedad AND broquer.es_miembro(p.org_id) AND
 (p.creado_por=broquer.usuario_actual() OR p.asignado_a=broquer.usuario_actual() OR EXISTS(
 SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=p.org_id AND m.usuario_id=broquer.usuario_actual() AND
 (m.rol_org IN ('owner','admin') OR coalesce((m.permisos->>'editar_registros_ajenos')::boolean,false)))))
$$;
ALTER TABLE broquer.propiedades ENABLE ROW LEVEL SECURITY;
CREATE POLICY propiedad_leer ON broquer.propiedades FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND
 (creado_por=broquer.usuario_actual() OR asignado_a=broquer.usuario_actual() OR EXISTS(
 SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=propiedades.org_id AND m.usuario_id=broquer.usuario_actual() AND
 (m.rol_org IN ('owner','admin') OR coalesce((m.permisos->>'ver_inventario_completo')::boolean,true)))));
CREATE POLICY propiedad_crear ON broquer.propiedades FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual() AND asignado_a=broquer.usuario_actual());
CREATE POLICY propiedad_editar ON broquer.propiedades FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND
 (creado_por=broquer.usuario_actual() OR asignado_a=broquer.usuario_actual() OR EXISTS(
 SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=propiedades.org_id AND m.usuario_id=broquer.usuario_actual() AND
 (m.rol_org IN ('owner','admin') OR coalesce((m.permisos->>'editar_registros_ajenos')::boolean,false))))) WITH CHECK(broquer.es_miembro(org_id));
ALTER TABLE broquer.propiedad_operaciones ENABLE ROW LEVEL SECURITY;
CREATE POLICY operacion_propiedad_leer ON broquer.propiedad_operaciones FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND EXISTS(SELECT 1 FROM broquer.propiedades p WHERE p.id=propiedad_operaciones.propiedad_id AND p.org_id=propiedad_operaciones.org_id));
CREATE POLICY operacion_propiedad_crear ON broquer.propiedad_operaciones FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND broquer.puede_editar_propiedad(propiedad_id));
CREATE POLICY operacion_propiedad_editar ON broquer.propiedad_operaciones FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND broquer.puede_editar_propiedad(propiedad_id)) WITH CHECK(broquer.es_miembro(org_id) AND broquer.puede_editar_propiedad(propiedad_id));
GRANT SELECT,INSERT ON broquer.propiedades,broquer.propiedad_operaciones TO broquer_api;
GRANT UPDATE(titulo,clave_interna,tipo,subtipo,estatus,estatus_cambiado_en,colonia,municipio,estado,calle,cp,m2_terreno,m2_construccion,recamaras,banos,estacionamientos,descripcion,actualizado_en,archivado_en) ON broquer.propiedades TO broquer_api;
GRANT UPDATE(precio,moneda,activa) ON broquer.propiedad_operaciones TO broquer_api;

-- Extend the common immutable activity log instead of creating a second bitácora.
ALTER TABLE broquer.actividades ALTER COLUMN oportunidad_id DROP NOT NULL;
ALTER TABLE broquer.actividades ADD COLUMN propiedad_id uuid;
ALTER TABLE broquer.actividades ADD CONSTRAINT actividad_propiedad_org FOREIGN KEY(org_id,propiedad_id) REFERENCES broquer.propiedades(org_id,id);
ALTER TABLE broquer.actividades ADD CONSTRAINT actividad_vinculada CHECK(oportunidad_id IS NOT NULL OR propiedad_id IS NOT NULL);
ALTER TABLE broquer.actividades DROP CONSTRAINT actividades_tipo_check;
ALTER TABLE broquer.actividades ADD CONSTRAINT actividades_tipo_check CHECK(tipo IN ('cambio_etapa','cambio_estatus','nota','sistema','tarea_creada','tarea_completada'));
CREATE INDEX actividad_por_propiedad ON broquer.actividades(propiedad_id,creado_en DESC);
DROP POLICY registro_visible ON broquer.actividades;
DROP POLICY registro_crear ON broquer.actividades;
CREATE POLICY registro_visible ON broquer.actividades FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id)
 AND (oportunidad_id IS NULL OR EXISTS(SELECT 1 FROM broquer.oportunidades o WHERE o.id=actividades.oportunidad_id AND o.org_id=actividades.org_id))
 AND (propiedad_id IS NULL OR EXISTS(SELECT 1 FROM broquer.propiedades p WHERE p.id=actividades.propiedad_id AND p.org_id=actividades.org_id)));
CREATE POLICY registro_crear ON broquer.actividades FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual()
 AND (oportunidad_id IS NULL OR EXISTS(SELECT 1 FROM broquer.oportunidades o WHERE o.id=actividades.oportunidad_id AND o.org_id=actividades.org_id))
 AND (propiedad_id IS NULL OR broquer.puede_editar_propiedad(propiedad_id)));

ALTER TABLE broquer.tareas ADD COLUMN propiedad_id uuid;
ALTER TABLE broquer.tareas ADD CONSTRAINT tarea_propiedad_org FOREIGN KEY(org_id,propiedad_id) REFERENCES broquer.propiedades(org_id,id);
DROP POLICY tarea_crear ON broquer.tareas;
CREATE POLICY tarea_crear ON broquer.tareas FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id)
 AND creado_por=broquer.usuario_actual() AND asignado_a=broquer.usuario_actual()
 AND (oportunidad_id IS NULL OR EXISTS(SELECT 1 FROM broquer.oportunidades o WHERE o.id=tareas.oportunidad_id AND o.org_id=tareas.org_id))
 AND (propiedad_id IS NULL OR broquer.puede_editar_propiedad(propiedad_id)));
