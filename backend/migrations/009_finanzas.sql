CREATE TABLE broquer.fin_cuentas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),nombre text NOT NULL CHECK(length(nombre) BETWEEN 1 AND 100),
 tipo text NOT NULL CHECK(tipo IN ('efectivo','banco','tarjeta','otra')),moneda text NOT NULL CHECK(moneda IN ('MXN','USD')),
 saldo_inicial numeric(16,2) NOT NULL DEFAULT 0,activa boolean NOT NULL DEFAULT true,
 creado_en timestamptz NOT NULL DEFAULT now(),actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(org_id,id)
);
CREATE UNIQUE INDEX fin_cuenta_nombre ON broquer.fin_cuentas(org_id,creado_por,lower(nombre));
CREATE TABLE broquer.fin_categorias (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),nombre text NOT NULL CHECK(length(nombre) BETWEEN 1 AND 100),
 tipo text NOT NULL CHECK(tipo IN ('ingreso','gasto')),clave text,
 UNIQUE(org_id,id),UNIQUE(org_id,creado_por,clave)
);
CREATE UNIQUE INDEX fin_categoria_nombre ON broquer.fin_categorias(org_id,creado_por,tipo,lower(nombre));
CREATE TABLE broquer.fin_movimientos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),org_id uuid NOT NULL REFERENCES broquer.organizaciones(id),
 creado_por uuid NOT NULL REFERENCES broquer.usuarios(id),tipo text NOT NULL CHECK(tipo IN ('ingreso','gasto','transferencia')),
 monto numeric(16,2) NOT NULL CHECK(monto>0),moneda text NOT NULL CHECK(moneda IN ('MXN','USD')),fecha date NOT NULL,
 concepto text NOT NULL CHECK(length(concepto) BETWEEN 1 AND 200),notas text NOT NULL DEFAULT '' CHECK(length(notas)<=4000),
 cuenta_id uuid NOT NULL,cuenta_destino_id uuid,categoria_id uuid,propiedad_id uuid,contacto_id uuid,
 idempotencia uuid NOT NULL,huella text NOT NULL,anulada_en timestamptz,motivo_anulacion text,
 creado_en timestamptz NOT NULL DEFAULT now(),actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(org_id,cuenta_id) REFERENCES broquer.fin_cuentas(org_id,id),
 FOREIGN KEY(org_id,cuenta_destino_id) REFERENCES broquer.fin_cuentas(org_id,id),
 FOREIGN KEY(org_id,categoria_id) REFERENCES broquer.fin_categorias(org_id,id),
 FOREIGN KEY(org_id,propiedad_id) REFERENCES broquer.propiedades(org_id,id),
 FOREIGN KEY(org_id,contacto_id) REFERENCES broquer.contactos(org_id,id),
 UNIQUE(org_id,creado_por,idempotencia),
 CHECK((tipo='transferencia' AND cuenta_destino_id IS NOT NULL AND cuenta_destino_id<>cuenta_id AND categoria_id IS NULL)
    OR (tipo IN ('ingreso','gasto') AND cuenta_destino_id IS NULL AND categoria_id IS NOT NULL)),
 CHECK((anulada_en IS NULL AND motivo_anulacion IS NULL) OR (anulada_en IS NOT NULL AND length(motivo_anulacion) BETWEEN 1 AND 1000))
);
CREATE INDEX fin_movimiento_fecha ON broquer.fin_movimientos(org_id,creado_por,fecha DESC,id);
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['fin_cuentas','fin_categorias','fin_movimientos'] LOOP
 EXECUTE format('ALTER TABLE broquer.%I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY fin_leer ON broquer.%I FOR SELECT TO broquer_api USING(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual())',t);
 EXECUTE format('CREATE POLICY fin_editar ON broquer.%I FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual()) WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual())',t);
 END LOOP; END $$;
CREATE POLICY fin_cuenta_crear ON broquer.fin_cuentas FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual());
CREATE POLICY fin_categoria_crear ON broquer.fin_categorias FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual());
CREATE POLICY fin_movimiento_crear ON broquer.fin_movimientos FOR INSERT TO broquer_api WITH CHECK(broquer.es_miembro(org_id) AND creado_por=broquer.usuario_actual()
 AND EXISTS(SELECT 1 FROM broquer.fin_cuentas c WHERE c.id=fin_movimientos.cuenta_id AND c.org_id=fin_movimientos.org_id AND c.moneda=fin_movimientos.moneda AND c.activa)
 AND (cuenta_destino_id IS NULL OR EXISTS(SELECT 1 FROM broquer.fin_cuentas c WHERE c.id=fin_movimientos.cuenta_destino_id AND c.org_id=fin_movimientos.org_id AND c.moneda=fin_movimientos.moneda AND c.activa))
 AND (categoria_id IS NULL OR EXISTS(SELECT 1 FROM broquer.fin_categorias c WHERE c.id=fin_movimientos.categoria_id AND c.org_id=fin_movimientos.org_id AND c.tipo=fin_movimientos.tipo))
 AND (propiedad_id IS NULL OR EXISTS(SELECT 1 FROM broquer.propiedades p WHERE p.id=fin_movimientos.propiedad_id AND p.org_id=fin_movimientos.org_id))
 AND (contacto_id IS NULL OR EXISTS(SELECT 1 FROM broquer.contactos c WHERE c.id=fin_movimientos.contacto_id AND c.org_id=fin_movimientos.org_id)));
GRANT SELECT,INSERT ON broquer.fin_cuentas,broquer.fin_categorias,broquer.fin_movimientos TO broquer_api;
GRANT UPDATE(nombre,activa,actualizado_en) ON broquer.fin_cuentas TO broquer_api;
GRANT UPDATE(nombre) ON broquer.fin_categorias TO broquer_api;
GRANT UPDATE(anulada_en,motivo_anulacion,actualizado_en) ON broquer.fin_movimientos TO broquer_api;
