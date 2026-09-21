-- Apply with the Supabase migration owner. Runtime roles never own tables.
CREATE SCHEMA IF NOT EXISTS broquer;
DO $$ BEGIN CREATE ROLE broquer_api NOLOGIN NOBYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE broquer_worker NOLOGIN NOBYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
CREATE TABLE broquer.usuarios (
 id uuid PRIMARY KEY REFERENCES auth.users(id), nombre text NOT NULL, apellidos text NOT NULL,
 telefono text NOT NULL CHECK(telefono ~ '^\+52[0-9]{10}$'), email text NOT NULL,
 activo boolean NOT NULL DEFAULT true, rol_interno text NOT NULL DEFAULT 'agente' CHECK(rol_interno IN ('agente','equipo','admin')),
 prueba_usada boolean NOT NULL DEFAULT false, modulos_desactivados text[] NOT NULL DEFAULT '{}',
 zona_horaria text NOT NULL DEFAULT 'America/Mexico_City', creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE broquer.organizaciones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), nombre text NOT NULL, tipo text NOT NULL DEFAULT 'personal' CHECK(tipo IN ('personal','empresa')),
 owner_id uuid NOT NULL REFERENCES broquer.usuarios(id), activa boolean NOT NULL DEFAULT true,
 plan text NOT NULL DEFAULT 'gratis', asientos_max integer NOT NULL DEFAULT 1 CHECK(asientos_max>0),
 zona_horaria text NOT NULL DEFAULT 'America/Mexico_City', creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE broquer.organizacion_miembros (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 usuario_id uuid NOT NULL REFERENCES broquer.usuarios(id), rol_org text NOT NULL CHECK(rol_org IN ('owner','admin','agente')),
 permisos jsonb NOT NULL DEFAULT '{}', activo boolean NOT NULL DEFAULT true,
 UNIQUE(org_id,usuario_id)
);
CREATE UNIQUE INDEX un_miembro_activo ON broquer.organizacion_miembros(usuario_id) WHERE activo;
CREATE TABLE broquer.plan_funciones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),plan text NOT NULL,modulo text NOT NULL,accion text NOT NULL,
 cuota_mensual integer NOT NULL CHECK(cuota_mensual>=0),UNIQUE(plan,modulo,accion)
);
CREATE TABLE broquer.uso_cuotas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),modulo text NOT NULL,accion text NOT NULL,
 periodo date NOT NULL,usado integer NOT NULL CHECK(usado>=0),UNIQUE(org_id,creado_por,modulo,accion,periodo)
);
CREATE TABLE broquer.uso_ia (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),
 modulo text NOT NULL,proveedor text NOT NULL,modelo text NOT NULL,tokens_entrada integer NOT NULL DEFAULT 0,tokens_salida integer NOT NULL DEFAULT 0,
 exito boolean NOT NULL,creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE broquer.auditoria (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),
 accion text NOT NULL,referencia uuid,creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE broquer.trabajos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),
 tipo text NOT NULL,clave text NOT NULL,datos jsonb NOT NULL DEFAULT '{}',estado text NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente','ejecutando','completado','fallido')),
 intentos integer NOT NULL DEFAULT 0,ejecutar_en timestamptz NOT NULL DEFAULT now(),bloqueado_hasta timestamptz,intento_id uuid,
 creado_en timestamptz NOT NULL DEFAULT now(),UNIQUE(org_id,tipo,clave)
);
CREATE INDEX trabajos_pendientes ON broquer.trabajos(ejecutar_en) WHERE estado IN ('pendiente','ejecutando');
CREATE FUNCTION broquer.usuario_actual() RETURNS uuid LANGUAGE sql STABLE AS $$
 SELECT nullif(current_setting('broquer.usuario_id',true),'')::uuid
$$;
CREATE FUNCTION broquer.es_miembro(organizacion uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
 SELECT EXISTS(SELECT 1 FROM broquer.organizacion_miembros m JOIN broquer.usuarios u ON u.id=m.usuario_id
 JOIN broquer.organizaciones o ON o.id=m.org_id WHERE m.org_id=organizacion AND m.usuario_id=broquer.usuario_actual() AND m.activo AND u.activo AND o.activa)
$$;
REVOKE ALL ON FUNCTION broquer.es_miembro(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION broquer.es_miembro(uuid) TO broquer_api;
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['usuarios','organizaciones','organizacion_miembros','plan_funciones','uso_cuotas','uso_ia','auditoria','trabajos'] LOOP
 EXECUTE format('ALTER TABLE broquer.%I ENABLE ROW LEVEL SECURITY',t);
 END LOOP; END $$;
CREATE POLICY perfil_propio ON broquer.usuarios FOR SELECT TO broquer_api USING(id=broquer.usuario_actual());
CREATE POLICY perfil_editar ON broquer.usuarios FOR UPDATE TO broquer_api USING(id=broquer.usuario_actual() AND activo) WITH CHECK(id=broquer.usuario_actual() AND activo);
CREATE POLICY organizacion_visible ON broquer.organizaciones FOR SELECT TO broquer_api USING(broquer.es_miembro(id));
CREATE POLICY membresia_propia ON broquer.organizacion_miembros FOR SELECT TO broquer_api USING(usuario_id=broquer.usuario_actual() AND broquer.es_miembro(org_id));
CREATE POLICY funciones_del_plan ON broquer.plan_funciones FOR SELECT TO broquer_api USING(EXISTS(SELECT 1 FROM broquer.organizaciones o WHERE o.plan=plan_funciones.plan AND broquer.es_miembro(o.id)));
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['uso_cuotas','uso_ia','auditoria','trabajos'] LOOP
 EXECUTE format('CREATE POLICY org_visible ON broquer.%I FOR SELECT TO broquer_api USING (broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual())',t);
 EXECUTE format('CREATE POLICY org_insertar ON broquer.%I FOR INSERT TO broquer_api WITH CHECK (broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual())',t);
 END LOOP; END $$;
CREATE POLICY cuota_actualizar ON broquer.uso_cuotas FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual()) WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual());
CREATE POLICY worker_trabajos ON broquer.trabajos FOR ALL TO broquer_worker USING(true) WITH CHECK(true);
CREATE POLICY worker_auditoria ON broquer.auditoria FOR INSERT TO broquer_worker WITH CHECK(true);
GRANT USAGE ON SCHEMA broquer TO broquer_api,broquer_worker;
GRANT SELECT ON ALL TABLES IN SCHEMA broquer TO broquer_api;
GRANT UPDATE(nombre,apellidos,telefono,zona_horaria) ON broquer.usuarios TO broquer_api;
GRANT INSERT ON broquer.uso_cuotas,broquer.uso_ia,broquer.auditoria,broquer.trabajos TO broquer_api;
GRANT UPDATE(usado) ON broquer.uso_cuotas TO broquer_api;
GRANT SELECT,UPDATE ON broquer.trabajos TO broquer_worker;
GRANT INSERT ON broquer.auditoria TO broquer_worker;
CREATE FUNCTION broquer.crear_cuenta_personal(p_nombre text,p_apellidos text,p_telefono text) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE uid uuid:=broquer.usuario_actual(); oid uuid; correo text;
BEGIN
 IF uid IS NULL THEN RAISE EXCEPTION 'sesion_requerida'; END IF;
 SELECT email INTO correo FROM auth.users WHERE id=uid AND email_confirmed_at IS NOT NULL;
 IF correo IS NULL THEN RAISE EXCEPTION 'correo_no_confirmado'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(uid::text,0));
 IF EXISTS(SELECT 1 FROM broquer.usuarios WHERE id=uid AND NOT activo) THEN RAISE EXCEPTION 'cuenta_inactiva'; END IF;
 SELECT org_id INTO oid FROM broquer.organizacion_miembros WHERE usuario_id=uid AND activo;
 IF oid IS NOT NULL THEN RETURN oid; END IF;
 INSERT INTO broquer.usuarios(id,nombre,apellidos,telefono,email) VALUES(uid,p_nombre,p_apellidos,p_telefono,correo) ON CONFLICT(id) DO NOTHING;
 INSERT INTO broquer.organizaciones(nombre,owner_id) VALUES(p_nombre||' '||p_apellidos,uid) RETURNING id INTO oid;
 INSERT INTO broquer.organizacion_miembros(org_id,usuario_id,rol_org) VALUES(oid,uid,'owner');
 INSERT INTO broquer.auditoria(org_id,creado_por,accion,referencia) VALUES(oid,uid,'cuenta_creada',uid);
 RETURN oid;
END $$;
REVOKE ALL ON FUNCTION broquer.crear_cuenta_personal(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION broquer.crear_cuenta_personal(text,text,text) TO broquer_api;
-- No plan rules, trial activation or pricing seeded: section 16 awaits product decisions.
