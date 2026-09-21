CREATE UNIQUE INDEX auditoria_trabajo_unica ON broquer.auditoria(accion,referencia) WHERE accion='cola_verificada';
CREATE TABLE broquer.precios_ia (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), proveedor text NOT NULL,modelo text NOT NULL,
 entrada_millon_usd numeric(14,6) NOT NULL CHECK(entrada_millon_usd>=0),
 salida_millon_usd numeric(14,6) NOT NULL CHECK(salida_millon_usd>=0),
 activo boolean NOT NULL DEFAULT true, actualizado_en timestamptz NOT NULL DEFAULT now(),
 UNIQUE(proveedor,modelo)
);
ALTER TABLE broquer.precios_ia ENABLE ROW LEVEL SECURITY;
CREATE POLICY precio_visible ON broquer.precios_ia FOR SELECT TO broquer_api USING(activo AND broquer.usuario_actual() IS NOT NULL);
GRANT SELECT ON broquer.precios_ia TO broquer_api;
ALTER TABLE broquer.uso_ia ADD COLUMN costo_usd numeric(14,8);
ALTER TABLE broquer.uso_ia ADD COLUMN latencia_ms integer CHECK(latencia_ms>=0);
ALTER TABLE broquer.uso_ia ADD COLUMN error_codigo text;
ALTER TABLE broquer.uso_ia ADD COLUMN intento integer NOT NULL DEFAULT 1;
-- Prices are configured from provider invoices/documentation at deployment, never guessed.
