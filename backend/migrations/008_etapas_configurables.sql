CREATE POLICY etapa_editar ON broquer.etapas FOR UPDATE TO broquer_api USING(broquer.es_miembro(org_id) AND EXISTS(
 SELECT 1 FROM broquer.organizacion_miembros m WHERE m.org_id=etapas.org_id AND m.usuario_id=broquer.usuario_actual() AND m.rol_org IN ('owner','admin')))
 WITH CHECK(broquer.es_miembro(org_id));
GRANT UPDATE(nombre,orden) ON broquer.etapas TO broquer_api;
