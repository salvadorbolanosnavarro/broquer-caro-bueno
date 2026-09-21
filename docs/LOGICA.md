# BROQUER — Brief de lógica para reconstrucción desde cero

> **Qué es este documento.** Es la especificación funcional y de arquitectura de Broquer, obtenida de una auditoría completa del repositorio `salvadorbolanosnavarro/Brokr-main` (commit `cd8e57d`, 16-sep-2026: ~196 routers, 41 módulos core, 42 pantallas HTML, 30 migraciones SQL, `app-shell.js`).
> Describe **lo que Broquer DEBE hacer y cómo DEBE estar construido**, no lo que el código viejo hace. Donde el código actual tiene un error, una duplicación o una decisión mal tomada, aquí va la versión correcta y, al final de cada módulo, una lista corta de **"No repetir"** con lo que se encontró.
>
> **Qué NO contiene.** Nada de diseño visual: ni colores, ni tipografía, ni layout, ni componentes, ni copy de marketing. La capa visual se define aparte. Cuando se mencionan "pantallas" es solo para describir flujos y datos.

---

## 0. Instrucciones para quien construya (Claude Code)

1. **No copies código del repo viejo.** Úsalo solo como referencia de comportamiento cuando este brief lo pida. El repo viejo tiene capas de compatibilidad, duplicados y parches que no deben sobrevivir.
2. **Este brief manda sobre el código viejo.** Si hay contradicción, gana el brief.
3. **No inventes reglas de negocio, leyes, montos ni textos legales.** Si algo no está aquí y hace falta, pregunta a Chava con una sola propuesta concreta.
4. **Reglas fijas del producto (no se discuten):**
   - Broquer **nunca** publica ni sindica inventario a portales (Inmuebles24, Lamudi, Mercado Libre, etc.). Leer portales para valuar o buscar sí; publicar no.
   - La marca es **Broquer**; el asistente es **Broq**. Nada de "Brokr" ni "Shaark" en código, prompts, tablas o textos.
   - Modelo de IA por defecto: `claude-sonnet-4-6` (configurable por variable, nunca hardcodeado en 20 lugares).
   - En la app iOS no se muestra ningún flujo de pago externo (regla de Apple). En iOS se cobra por IAP (RevenueCat) o no se cobra.
   - Todo cambio que toque datos personales, dinero, firmas o estructura de equipo debe actualizar también: guía del agente, soporte, términos/legal y aviso de privacidad.
5. **Construye por fases** (sección 15) y con pruebas automáticas por fase. Nada se da por terminado sin pruebas de las reglas de negocio de este documento.
6. Todo en **español de México** para textos al usuario. Identificadores de código y base de datos en español `snake_case` (así ya los conoce el equipo), consistentes en todo el sistema.

---

## 1. Qué es Broquer

**Broquer** es el sistema operativo del asesor inmobiliario en México: CRM, inventario, WhatsApp con recepción por IA, contratos, firma electrónica, cumplimiento PLD, ISR, valuación, finanzas, marketing (fichas, fotos, video, anuncios, sitio web) y un asistente (Broq) que ejecuta acciones por texto o voz.

- **Usuario principal:** asesor independiente o equipo/inmobiliaria pequeña. Trabaja desde el celular, en la calle, entre visitas. No es técnico.
- **Segundo usuario:** el dueño de una inmobiliaria ("Broquer para Empresas") que administra a varios asesores, reparte registros y controla qué ve cada quien.
- **Terceros sin cuenta:** prospectos (WhatsApp, sitio web, Lead Ads), firmantes de contratos, clientes que llenan su expediente PLD. Nunca crean cuenta; entran por liga con token.
- **Mercado:** todo México desde el día uno (nada de defaults "Morelia, Michoacán" en lógica; la ciudad/estado siempre sale de un dato capturado o de la configuración de la cuenta).
- **Visión:** no un CRM con muchas funciones, sino un **sistema operativo de la transacción**: del primer mensaje del prospecto al cierre, con contrato, firma, expediente, impuestos y comisión cobrada, todo ligado.

### 1.1 Planes y acceso (lógica)
- **Gratis:** módulos CRM (contactos, clientes, inmuebles, tareas, estadísticas básicas, bolsa en modo lectura). *Decisión pendiente para Chava (sección 16): confirmar exactamente qué entra en gratis.*
- **Broquer Max (individual):** todo lo demás. Precio vigente según memoria del negocio: 899 MXN/mes (web con Stripe; iOS con RevenueCat). El precio vive en configuración, nunca en código.
- **Prueba gratuita:** 7 días, una sola vez por usuario (`prueba_usada`), sin tarjeta.
- **Broquer para Empresas:** organización tipo empresa con asientos. Hoy el código tiene tarifas fijas (3,499/mes base 5 asientos + 599 por asiento extra; anual 38,489 + 6,589) pero el negocio dice "precio por contacto y activación manual". *Decisión pendiente.* La lógica de asientos se construye igual en ambos casos.
- **Accesos especiales:** rol interno `equipo`/`admin` (acceso total) y "acceso completo hasta fecha X" otorgado por admin.

---

## 2. Principios de arquitectura (obligatorios)

1. **Un solo camino para leer y escribir datos de negocio: la API del backend.** El frontend nunca escribe directo a la base (hoy el frontend escribe a `contactos`, `tareas`, `actividades`, `pld_expedientes`, `usuarios` por PostgREST y el backend escribe con service role a las mismas tablas: dos fuentes de verdad y permisos imposibles de auditar). La base tiene RLS como **segunda** barrera, no como la única.
2. **Multi-tenant real por organización.** Toda cuenta pertenece a una organización (personal o empresa). Todo registro de negocio lleva `org_id` + `creado_por` + `asignado_a`. La visibilidad se resuelve por reglas de organización y permisos, en un solo lugar del backend.
3. **Permisos y planes se validan en el servidor.** Hoy el paywall es un interceptor de clics en el navegador que además "falla abierto", los módulos desactivados solo se ocultan del menú y los permisos de organización (`ver_telefonos`, etc.) casi no se aplican. Todo eso debe vivir en el backend: si no tienes derecho, el endpoint responde 402/403.
4. **Monolito modular.** Un backend, módulos con fronteras claras (`crm`, `inventario`, `whatsapp`, `firmas`, `pld`, …). Cada módulo declara: rutas, permisos, entitlement (plan), tareas en segundo plano, eventos que emite. Registro declarativo; nada de 150 `include_router` a mano.
5. **Nada de estado en memoria del proceso.** Hoy viven en RAM: límites de uso, caché, PDFs generados (`_pdf_store`), progreso de migraciones, locks de conversaciones, cooldowns de automatizaciones y los "cron" de recordatorios y buscador. Con dos instancias todo eso se rompe o se duplica. Debe ir a Postgres/Redis y a una cola de trabajos.
6. **Cola de trabajos y programador únicos.** Todo lo lento o programado (IA larga, PDFs, videos, importaciones, campañas, recordatorios, escaneos, webhooks) corre como job persistente con reintentos, idempotencia y estado consultable.
7. **Una sola implementación por capacidad.** Una sola función de "número a letras", un solo normalizador de teléfono MX, un solo cliente de IA, un solo generador de PDF, una sola búsqueda de inmuebles, un solo motor AVM, un solo modelo de contacto. (Hoy hay 2 números-a-letras, 2 pausas de IA idénticas, 2 creadores de contacto CRM, 5 motores AVM, 3 módulos de WhatsApp, 2 pantallas de contactos casi idénticas.)
8. **Fallar cerrado en seguridad, fallar suave en lo accesorio.** Autenticación, permisos, planes, firmas y webhooks: si no se puede verificar, se niega. Telemetría, caché, notificaciones: si fallan, no tumban la operación.
9. **Auditoría de todo lo sensible.** Bitácora inmutable (quién, qué, cuándo, desde qué IP) para firmas, PLD, permisos, borrados, exportaciones, cambios de plan y accesos de admin.
10. **Dinero y fechas bien.** Montos en `numeric(14,2)` con moneda explícita; cálculos con decimal (no float). Timestamps en UTC en la base; cada organización tiene zona horaria (default `America/Mexico_City`) y todo lo que se muestra o se interpreta ("mañana a las 5") usa esa zona.
11. **IDs `uuid` en todas las tablas.** Hoy `contactos.id` es texto tipo `c_<milisegundos>`, generado en el navegador y en tres lugares del backend (colisiones posibles con webhooks simultáneos).
12. **Borrado:** los registros de negocio se archivan (soft delete) y solo se purgan por proceso explícito. Excepción legal: la eliminación de cuenta (requisito de Apple y LFPDPPP) sí borra de verdad, con job verificable.
13. **Secretos cifrados en reposo.** Tokens de Meta/WhatsApp, API keys de EasyBroker, contraseñas de correo: cifrados con llave de aplicación y rotables. Nunca se devuelven al navegador.
14. **Todo endpoint costoso exige sesión, plan y cuota por usuario** (IA, PDFs, scraping, video, OCR).

---

## 3. Arquitectura objetivo

### 3.1 Componentes
| Pieza | Qué es | Notas |
|---|---|---|
| **API** | FastAPI (Python), monolito modular | Único punto de lectura/escritura de negocio. Versionada `/v1`. |
| **Base de datos** | Postgres (Supabase), con PostGIS | Migraciones versionadas en el repo y aplicadas por herramienta (no a mano en el SQL Editor). RLS como segunda barrera. |
| **Auth** | Supabase Auth (email+contraseña, Google con PKCE, recuperación) | El backend valida el JWT **localmente** (JWKS) y además revisa que la cuenta esté activa (cache corto). Hoy se hace una llamada HTTP a Supabase por cada request. |
| **Storage** | Supabase Storage | Buckets privados por defecto; URLs firmadas de vida corta. Público solo lo que debe ser público (fotos de inmuebles publicados, sitio del agente). |
| **Cola / jobs** | Worker(s) con cola persistente (p. ej. Postgres-based o Redis) + programador | Reintentos con backoff, idempotencia por llave, estado consultable por el frontend. |
| **Cache y límites** | Redis (o tabla Postgres) | Rate limit por usuario/IP, locks por conversación, caché de Places/Banxico/scraping. |
| **Frontend** | Una sola aplicación (SPA) empaquetada también para iOS con Capacitor | Un solo código para web, PWA e iOS; la capa visual se define aparte. Rutas públicas separadas: firma, expediente PLD, verificación de folio, sitio del agente, unirse a equipo. |
| **Generador de documentos** | Servicio interno (Chromium headless) detrás de la cola | PDFs (ficha, ISR, AVM, constancia de firma, reportes, contratos→PDF). Nunca recibe HTML arbitrario del navegador. |
| **Gateway de IA** | Módulo único | Anthropic (texto/visión/herramientas), Groq Whisper (voz), Gemini imagen (edición/amueblado). Cuotas, costo, reintentos, registro de uso, validación de JSON por esquema. |
| **Notificaciones** | Módulo único | Push iOS (APNs) por **dispositivo** (tabla de dispositivos, no una columna en usuarios), correo (Resend), WhatsApp plantilla, avisos in-app. |

### 3.2 Estructura del backend (módulos)
```
app/
  core/        config, auth, org_context, permisos, planes, db, storage, http_seguro, errores, auditoria, cola, ia, pdf, notificaciones, telemetria, dinero, fechas, telefonos, texto (numero_a_letras)
  modulos/
    cuentas/        registro, perfil, dispositivos, eliminación de cuenta
    organizaciones/ equipo, invitaciones, permisos, asignación
    planes/         suscripciones, Stripe, RevenueCat, prueba, accesos especiales
    crm/            contactos, oportunidades (pipeline), actividades (bitácora), etiquetas, etapas
    inventario/     propiedades, fotos, estatus, relaciones contacto-propiedad
    tareas/         tareas, recordatorios, citas (.ics)
    operaciones/    la transacción: partes, inmueble, contrato, firma, PLD, comisión, ISR, documentos
    estadisticas/
    bolsa/
    buscador/       requerimientos de búsqueda y resultados
    whatsapp/       números, bandeja, IA recepción, modo asesor, automatizaciones, campañas, plantillas, estadísticas
    correo/
    contratos/      plantillas estándar y machotes propios
    firmas/
    pld/
    documentos/     verificador documental, análisis de solicitud de arrendamiento
    avm/
    isr/
    finanzas/
    marketing/      ficha técnica, editor de imágenes, amueblado virtual, video, Facebook/Instagram
    sitio/          sitio público del agente y captura de leads
    broq/           asistente (app y WhatsApp comparten motor y herramientas)
    integraciones/  EasyBroker (migración), Meta, Google Places, Banxico, buscadores web
    admin/          consola interna
    publico/        endpoints sin sesión (firma, expediente, verificación, sitio, webhooks)
```

### 3.3 Contexto de cada request (resuelto por `core`)
`usuario_id`, `org_id`, `rol_org` (`owner|admin|agente`), `permisos` efectivos, `plan` y `entitlements`, `modulos_desactivados`, `zona_horaria`, `es_staff` (rol interno). Todo endpoint recibe este contexto ya validado; ningún módulo vuelve a consultar auth/org por su cuenta.

### 3.4 Convenciones de API
- Errores con forma única: `{codigo, mensaje_usuario, detalle_tecnico?}`. `mensaje_usuario` en español claro; nunca se regresa texto crudo de proveedores (hoy se filtra texto de Supabase, Stripe y Meta al usuario).
- 401 sin sesión · 402 falta plan · 403 sin permiso · 404 no existe **o no es tuyo** (no revelar existencia) · 409 conflicto de estado · 422 validación · 429 cuota.
- Operaciones con efectos externos (enviar WhatsApp, crear anuncio, cobrar, mandar a firma) aceptan `Idempotency-Key`.
- Paginación por cursor en listados grandes (contactos, inmuebles, mensajes).
- Webhooks: verificación de firma antes de cualquier efecto; se guardan crudos en `webhook_eventos` con llave única del proveedor para deduplicar y se procesan por la cola.

### 3.5 Permisos (fuente única)
Roles de organización: `owner`, `admin`, `agente`. Owner/admin tienen todo. Agente tiene por defecto:

| Permiso | Default agente | Qué controla (DEBE aplicarse en el backend) |
|---|---|---|
| `ver_telefonos` | no | Teléfonos/correos/WhatsApp de contactos que **no** le están asignados se devuelven enmascarados. |
| `ver_comisiones` | no | Campos de comisión de inmuebles y operaciones, y el módulo de Finanzas de la organización. |
| `ver_inventario_completo` | sí | Si es no: solo ve inmuebles creados por él o asignados a él. |
| `ver_contactos_equipo` | sí | Si es no: solo ve contactos creados por él o asignados a él. |
| `exportar` | sí | Exportaciones CSV/PDF masivas. |
| `ver_estadisticas_equipo` | no | Estadísticas agregadas de toda la organización. |
| `gestionar_integraciones` | no | Conectar/desconectar EasyBroker, Facebook, WhatsApp de la empresa. |
| `eliminar_registros` *(nuevo, explícito)* | no en empresa / sí en cuenta personal | Hoy está implícito en código ("en empresa solo owner/admin borra"). |
| `editar_registros_ajenos` *(nuevo)* | no | Hoy cualquier miembro activo puede editar cualquier inmueble de la org por un "fallback" del endpoint. |

Además: el admin de Broquer puede **desactivar módulos por cuenta** (`modulos_desactivados`); eso también se aplica en el backend (403), no solo ocultando el menú.

### 3.6 Entitlements por plan
Tabla de configuración `plan_funciones(plan, modulo, accion, cuota_mensual)`. Ejemplos de acciones premium que hoy solo se bloquean en el navegador: calcular ISR, analizar AVM, limpiar/editar imagen, generar contrato, generar ficha PDF, generar texto con IA, crear anuncio, conectar WhatsApp, crear plantilla de WhatsApp, mandar a firma, conectar correo, generar video. El backend responde 402 con `{codigo:"requiere_plan", plan_sugerido:"max"}`.

### 3.7 Uso y costos de IA
Cada llamada a proveedor se registra en `uso_ia` (usuario, org, módulo, herramienta, proveedor, modelo, tokens in/out, unidades, segundos de audio, costo USD calculado con tabla de precios configurable). Cuotas por plan y por usuario (diarias/mensuales) aplicadas **antes** de llamar al proveedor. Hoy el OCR de tickets de Finanzas y otros endpoints no tienen cuota.

---

## 4. Modelo de datos canónico

> Campos comunes a toda tabla de negocio (no se repiten abajo): `id uuid`, `org_id`, `creado_por`, `creado_en`, `actualizado_en`, `archivado_en` (null = activo). Tablas con dueño operativo agregan `asignado_a` (usuario de la org).
> Los enums se listan en el Anexo A.

### 4.1 Cuentas y organización
- **usuarios** (perfil de la persona; 1:1 con auth): `nombre`, `apellidos`, `telefono` (E.164), `email`, `rol_interno` (`agente|equipo|admin`), `activo`, `prueba_usada`, `acceso_completo_hasta`, `modulos_desactivados text[]`, `zona_horaria`, `foto_url`. **El usuario solo puede editar** nombre, apellidos, teléfono, foto y zona horaria. Rol interno, activo, accesos y módulos solo los cambia un admin de Broquer por endpoint de admin. (Hoy el registro hace PATCH directo a `usuarios` desde el navegador; si la RLS no restringe columnas, un usuario podría darse rol admin.)
- **dispositivos**: `usuario_id`, `plataforma` (`ios|web`), `token_push`, `entorno` (`sandbox|prod`), `ultimo_uso`. Varios por usuario. Se limpian con 410 de APNs.
- **organizaciones**: `nombre`, `tipo` (`personal|empresa`), `owner_id`, `activa`, `plan`, `asientos_max`, `vence_en`, `zona_horaria`, `logo_url` (para marca de agua), `ciudad_base`, `estado_base`.
- **organizacion_miembros**: `org_id`, `usuario_id`, `rol_org`, `permisos jsonb` (solo overrides booleanos), `activo`. **Un usuario pertenece a una sola organización activa.**
- **invitaciones**: `org_id`, `email`, `rol_org`, `permisos`, `token_hash`, `expira_en` (14 días), `aceptada_en`, `invitado_por`, `traer_mis_datos` (lo decide **el invitado** al aceptar, no el admin).
- **suscripciones**: `org_id`, `usuario_pagador_id`, `plan` (`max|ampi|empresas`), `estado` (`trialing|active|past_due|canceled|expired`), `proveedor` (`stripe|revenuecat|manual`), `id_externo_suscripcion`, `id_externo_cliente`, `periodo` (`mensual|anual`), `asientos`, `prueba_hasta`, `periodo_actual_fin`, `cancelar_al_fin_de_periodo`. **Una fila vigente por organización** (llave única parcial), historial aparte.
- **integraciones**: `org_id`, `proveedor` (`easybroker|facebook|whatsapp|correo`), `credencial_cifrada`, `meta jsonb` (sin secretos), `estado`, `expira_en`, `ultimo_error`.

### 4.2 CRM
- **contactos** (la persona o empresa, sin importar su rol): `nombre`, `apellidos`, `es_persona_moral`, `razon_social`, `sexo` (para concordancia de género en contratos), `telefonos jsonb` (lista `{numero E.164, tipo: movil|fijo|whatsapp, principal}`), `emails jsonb`, `empresa`, `domicilio` (calle, num_ext, num_int, colonia, cp, municipio, estado, pais), `roles text[]` (propietario, inquilino, comprador, vendedor, obligado_solidario, fiador, colega, notario, otro — **un contacto puede tener varios**), `fuente`, `etiquetas text[]`, `notas_privadas` (texto libre interno), `consentimiento_contacto` (para marketing/campañas: `si|no|desconocido`, fecha y canal). Unicidad blanda por organización: teléfono principal normalizado y email.
- **canales_contacto**: identidades externas del mismo contacto: `contacto_id`, `canal` (`whatsapp|facebook_lead|sitio|easybroker|email`), `identificador` (wa_id, leadgen_id, id EB…), `numero_whatsapp_id` cuando aplica. Así un prospecto de WhatsApp y el contacto del CRM **son el mismo registro** (hoy existen `wa2_contactos` y `contactos` en paralelo con sincronización a medias).
- **oportunidades** (el pipeline; lo que hoy es `es_potencial` + `estatus` en el contacto): `contacto_id`, `tipo` (`busca_comprar|busca_rentar|quiere_vender|quiere_rentar`), `etapa_id`, `temperatura` (`caliente|tibio|frio|nuevo`), `score` 0–100, `presupuesto_min/max`, `moneda`, `forma_pago` (`contado|credito_bancario|infonavit|fovissste|mixto|por_definir`), `zona_interes`, `resumen_ia`, `probabilidad` (`baja|media|alta`), `valor_estimado`, `cerrada_en`, `motivo_perdida`. Un contacto puede tener varias oportunidades en el tiempo. La vista "Clientes" es un tablero de oportunidades abiertas por etapa.
- **etapas_pipeline** (por organización, ordenables): `nombre`, `orden`, `tipo` (`abierta|ganada|perdida`). **El tipo es explícito**; hoy las estadísticas adivinan cuál etapa es "cierre" con una expresión regular sobre el nombre. Default: Futuro, Nuevo, Contactado, Activo (abiertas), Cerrado (ganada), Descartado (perdida).
- **historial_etapas**: `oportunidad_id`, `de_etapa`, `a_etapa`, `cambiado_por`, `cambiado_en`. Base de todas las métricas de tiempo (hoy se calcula con `updated_at`, que cambia con cualquier edición).
- **actividades** (bitácora única y append-only de todo el sistema): `tipo` (Anexo A), `texto`, `adjuntos jsonb` (rutas de storage), `contacto_id?`, `propiedad_id?`, `oportunidad_id?`, `operacion_id?`, `tarea_id?`, `origen` (`manual|ia|whatsapp|sistema|importacion`), `autor_id`. Las "notas" que hoy se concatenan como texto dentro de `contactos.notas`, `propiedades.notas` y `tareas.notas` (con marcas `[fecha · Broq]`) **son actividades**.

### 4.3 Inventario
- **propiedades**: `titulo`, `clave_interna` (única por org), `tipo` (Anexo A), `estatus` (Anexo A) + `estatus_cambiado_en`, `exclusiva` (`si|no|no_indicado`), `origen` (`manual|easybroker|whatsapp|csv`), `id_externo_easybroker` (único por org), `propietario_contacto_id?`, `es_ajena` (inventario de colega), ubicación (`calle, num_ext, num_int, colonia, cp, municipio, estado, pais, lat, lng, esquina_con`), `mostrar_ubicacion_exacta`, superficies (`m2_terreno, m2_construccion, m2_no_cubierta`) en `numeric`, `recamaras int`, `banos numeric(3,1)`, `medios_banos int`, `estacionamientos int`, `nivel`, `anio_construccion`, `mantenimiento_mensual`, `amenidades text[]`, `descripcion`, `notas_privadas`, `codigo_llave`, `etiquetas text[]`, `comparte_comision` (`si|no|no_indicado`), `condiciones_compartir`.
- **propiedad_operaciones** (una propiedad puede estar en venta **y** renta a la vez): `propiedad_id`, `operacion` (`venta|renta`), `precio`, `moneda`, `mostrar_precio`, `comision_tipo` (`porcentaje|meses|monto`), `comision_valor`, `activa`. (Hoy solo cabe una operación y el importador de EasyBroker descarta la otra.)
- **propiedad_fotos**: `propiedad_id`, `ruta_storage`, `orden`, `es_portada`, `es_editada_ia` (bool), `origen` (`subida|easybroker|whatsapp|editor|amueblado`), `ancho`, `alto`. (Hoy es un arreglo de URLs dentro de la fila, con fotos base64 históricas y URLs externas de EasyBroker mezcladas.)
- **contacto_propiedad**: `contacto_id`, `propiedad_id`, `relacion` (`interesado|propietario|inquilino|comprador|relacionado`), `notas`. Único por (contacto, propiedad, relación). **Siempre filtrado por organización** (hoy hay lecturas de esta tabla sin filtro de tenant: fuga entre cuentas).
- **historial_estatus_propiedad**: igual que historial de etapas (métrica de días en mercado real).

### 4.4 Tareas
- **tareas**: `titulo`, `tipo` (`llamada|visita|cita|seguimiento|tramite|otro` — hoy las visitas se detectan buscando la palabra "visita" en el título), `inicio` (timestamptz con hora real; hoy la tarea manual siempre se guarda a las 12:00), `duracion_min`, `todo_el_dia`, `completada_en`, `recordatorio_min_antes` (default 60), `recordatorio_enviado_en`, `descripcion`, `ubicacion`, `origen` (`manual|broq|whatsapp_ia|sistema`).
- **tarea_vinculos**: `tarea_id` + uno de (`contacto_id`, `propiedad_id`, `oportunidad_id`, `operacion_id`). **Solo vínculos N:M**; hoy hay además columnas sueltas `contacto_id`/`propiedad_id` en la tarea, duplicando.

### 4.5 Operación (transacción) — entidad nueva y central
Hoy la "operación" está dispersa: un JSON `operaciones` dentro del contacto, `pld_operaciones` aparte, la comisión como `comision_real` en la propiedad, los contratos se generan y no se guardan (la tabla `contratos` que cuenta el dashboard nunca se escribe), la firma cuelga de un PDF suelto. Debe existir:
- **operaciones**: `tipo` (`compraventa|arrendamiento|promesa|exclusiva|otro`), `propiedad_id`, `estado` (`preparacion|contrato|firma|cierre|cerrada|cancelada`), `precio_pactado`, `moneda`, `fecha_cierre_estimada`, `fecha_cierre_real`, `comision_total`, `comision_compartida_con` (colega/empresa), `mi_parte_comision`, `notaria`, `notas`.
- **operacion_partes**: `operacion_id`, `contacto_id`, `rol` (`vendedor|comprador|arrendador|arrendatario|obligado_solidario|fiador|conyuge|copropietario|colega|notario|testigo`), `porcentaje` (copropiedad), `expediente_pld_id?`.
- **operacion_documentos**: checklist de documentos requeridos por tipo de operación y rol (ver módulo Verificador), con estado por documento.
- De la operación cuelgan: contratos, documentos de firma, operación PLD, movimientos de finanzas (comisión cobrada), cálculo ISR guardado, tareas y actividades.

### 4.6 WhatsApp
- **wa_numeros**: `alias`, `phone_number_id` (único global), `numero_mostrado`, `waba_id`, `waba_nombre`, `token_cifrado`, `token_expira_en`, `token_valido`, `token_error_en`, `coexistencia` (bool), `webhook_verificado`, `ia_habilitada`, `numero_personal_asesor` (E.164; para modo asesor), `responsable_id` (usuario de la org dueño de la línea), `conectado_en` (mensajes con timestamp anterior se ignoran), `calidad`.
- **wa_entrenamiento** (por número, con uno default de la org): `nombre_ia`, `identidad`, `tono`, `puede`, `debe`, `no_debe`, `especialidad`, `conocimiento` (texto ≤ 6,000 caracteres, "fuente de verdad"), `objetivo`, `datos_a_calificar text[]`, `preguntas_extra text[]`, `palabras_escalar text[]`, `horario_activo`, `hora_inicio`, `hora_fin`, `mensaje_fuera_horario`, `max_mensajes_ia` (tope global de sistema 25), `activo`, `zona_horaria`, `modo_global` (`siempre_encendida|solo_nuevos|siempre_apagada`), `pausa_al_responder` (bool), `pausa_minutos` (0 = apagar para siempre en ese chat), `meses_para_considerar_nuevo` (default 3).
- **wa_agenda**: nombres de la agenda del celular del asesor (coexistencia): `numero_id`, `telefono`, `nombre`, `conocido` (ya había platicado antes de conectar).
- **wa_conversaciones**: `numero_id`, `contacto_id` (CRM), `wa_id`, `nombre_wa`, `ia_modo` (`auto|on|off`), `ia_pausada_hasta`, `sesion_nueva` (bool), `no_leida`, `sin_leer_count`, `ultimo_mensaje_en`, `ultimo_entrante_en` (controla la ventana de 24 h), `ultimo_entrante_wamid`, `propiedad_contexto_id?` (anuncio/propiedad de origen), `ultimas_propiedades_enviadas jsonb`, `memoria_asesor jsonb` (último contacto/tarea/propiedad tocados en modo asesor), `opt_out` (bool, y fecha), `etiquetas text[]`, `es_chat_asesor` (bool).
- **wa_mensajes**: `conversacion_id`, `wamid` (único), `direccion` (`entrante|saliente`), `autor` (`prospecto|ia|asesor|sistema|campana|flujo`), `tipo` (`texto|imagen|audio|video|documento|ubicacion|contacto|plantilla|nota_interna`), `texto`, `transcripcion`, `descripcion_ia`, `media_ruta`, `media_mime`, `estado_entrega` (`enviado|entregado|leido|fallido`), `error_entrega`, `plantilla_nombre?`.
- **wa_automatizaciones**: `nombre`, `numero_id?` (null = todos), `activa`, `disparador` (`palabra|primer_mensaje|regreso_tras_inactividad`), `palabras text[]` (≤15), `pasos jsonb` (≤12; ver módulo), `veces_usada`.
- **wa_flujo_estado**: `conversacion_id` (único), `automatizacion_id`, `paso`, `datos jsonb`, `actualizado_en`.
- **wa_campanas**: `numero_id`, `nombre`, `plantilla`, `idioma`, `variables jsonb`, `filtro_audiencia` (etiqueta), `estado` (`borrador|programada|enviando|terminada|cancelada`), `programada_para`, `total`, `enviados`, `entregados`, `leidos`, `fallidos`, `terminada_en`.
- **wa_campana_envios**: `campana_id`, `conversacion_id`, `wamid`, `estado`, `error`.
- **wa_plantillas_cache**: espejo de plantillas de Meta por WABA (nombre, idioma, categoría, estatus, cuerpo, variables).

### 4.7 Correo
- **correo_cuentas**: 1 por usuario. `email`, `usuario`, `imap_host`, `imap_puerto` (solo 993), `smtp_host`, `smtp_puerto` (465/587), `smtp_ssl`, `secreto_cifrado`, `modo_envio` (`smtp|relay`), `activo`.

### 4.8 Contratos
- **plantillas_contrato**: `tipo` (`estandar|machote`), `nombre`, `tipo_documento` (`arrendamiento|promesa_compraventa|exclusiva|carta_intencion|convenio|otro`), `version`, `ruta_docx_plantilla`, `ruta_docx_original?`, `campos jsonb` (esquema de formulario), `org_id` (null = plantilla oficial de Broquer), `activa`.
- **contratos**: `operacion_id?`, `propiedad_id?`, `plantilla_id`, `plantilla_version`, `datos jsonb` (valores capturados), `clausulas_especiales jsonb` (texto del usuario + redacción IA aceptada), `estado` (`borrador|generado|enviado_a_firma|firmado|cancelado`), `ruta_docx`, `ruta_pdf`, `documento_firma_id?`.

### 4.9 Firma electrónica
- **firma_documentos**: `operacion_id?`, `contrato_id?`, `propiedad_id?`, `titulo`, `tipo` (Anexo A), `nivel` (`simple`; `reforzado` reservado), `estado` (`borrador|enviado|parcial|completo|rechazado|vencido|cancelado`), `folio` (`BRQ-XXXXXXXX`, alfabeto sin ambigüedades `23456789BCDFGHJKMNPQRSTVWXYZ`), `archivo_ruta`, `archivo_nombre`, `bytes`, `paginas`, `hash_original` (SHA-256), `firmado_ruta`, `hash_firmado`, `exige_ine`, `mensaje`, `vence_en` (default 30 días, 1–365), `completado_en`, `cancelado_en`, `motivo_cancelacion`, `campos_colocados`, `rubrica_todas`, `nom151_folio/ruta/en` (reservado para PSC).
- **firma_firmantes**: `documento_id`, `contacto_id?`, `expediente_pld_id?`, `nombre`, `email`, `telefono` (E.164), `rol` (Anexo A), `orden` (null = paralelo), `obligatorio`, `token_hash`, `estado` (`pendiente|firmado|rechazado`), `otp_hash`, `otp_expira_en`, `otp_intentos`, `otp_canal`, `otp_enviado_en`, `verificado_en`, `firmado_en`, `rechazado_en`, `motivo_rechazo`, `trazo_ruta`, `ine_frente_ruta`, `ine_reverso_ruta`, `ip`, `user_agent`, `geo_lat/lng/precision`, `consentimiento_en`, `consentimiento_texto_version`.
- **firma_campos**: `documento_id`, `firmante_id`, `pagina ≥1`, `tipo` (`firma|rubrica|nombre|fecha`), `x,y,ancho,alto` normalizados 0–1.
- **firma_paginas**: imagen por hoja para colocar campos (`pagina`, `ruta`, `ancho_pt`, `alto_pt`).
- **firma_eventos**: bitácora inmutable (`tipo`, `detalle`, `actor` `agente|firmante|sistema`, `ip`, `user_agent`, `payload`). **Solo inserción**; ni el dueño puede borrar.

### 4.10 Cumplimiento PLD (LFPIORPI, actividad vulnerable fracción V)
- **pld_config** (por organización): `alta_sppld`, `fecha_alta`, `folio_padron` (clave de sujeto obligado), `fraccion` (`V`), `responsable_nombre/email/rfc`, `valor_uma` + `vigencia_uma`, `umbral_aviso_uma` (8,025), `umbral_efectivo_uma` (8,025 — ver módulo), `meses_acumulacion` (6), `retencion_anios` (10), `dia_limite_aviso` (17), `alertas_activas`, `dias_aviso_previo` (7).
- **pld_expedientes**: `contacto_id`, `tipo_persona` (`fisica|moral|fideicomiso`), datos de identificación completos (Anexo B), domicilio, identificación, datos de persona moral y representante, `es_pep`, `pep_cargo/dependencia/parentesco`, `pep_revisado_en`, beneficiario controlador (`bc_es_el_mismo`, datos, `bc_declarado_en`), `origen_recursos`, `proposito_operacion`, `nivel_riesgo` (`bajo|medio|alto`) + `riesgo_motivos`, `completitud` 0–100, `estatus` (`incompleto|completo|observaciones`), `observaciones`, `token_publico_hash`, `token_expira_en` (14 días), `enviado_al_cliente_en`, `autollenado_en`, `firma_cliente_en`, `firma_cliente_ip`.
- **pld_documentos**: `expediente_id`, `tipo` (Anexo A), `ruta`, `mime`, `bytes`, `subido_por` (`agente|cliente`).
- **pld_operaciones**: `operacion_id?` (liga a la operación), `expediente_id`, `contraparte_expediente_id?`, `propiedad_id?`, `tipo_operacion`, `fecha_operacion`, `monto`, `moneda`, `tipo_cambio`, `monto_mxn`, `monto_sin_iva`, `forma_pago`, `monto_efectivo`, `instrumento_monetario`, `inusual`, `inusual_motivo`, `inusual_detectada_en`, `inusual_reportada_en`, `estatus` (`abierta|cerrada|cancelada`), `genera_aviso`, `motivo_aviso` (`umbral|acumulacion|inusual`), `monto_acumulado`, `evaluado_en`, `aviso_id?`.
- **pld_avisos**: `periodo` (AAAA-MM), `tipo` (`normal|en_ceros|inusual_24h`), `referencia`, `estatus` (`borrador|generado|presentado`), `fecha_limite`, `num_operaciones`, `monto_total`, `xml_ruta`, `xml_generado_en`, `acuse_folio`, `presentado_en`.
- **pld_bitacora**: inmutable (acción, detalle, expediente/operación/aviso, actor, ip).

### 4.11 Finanzas
- **fin_cuentas**: `nombre`, `tipo` (`banco|efectivo|tarjeta|otra`), `saldo_inicial`, `moneda`, `activa`. **El saldo nunca se guarda; se calcula.**
- **fin_categorias**: `nombre`, `tipo` (`ingreso|gasto`), `clave` (semillas), `orden`.
- **fin_movimientos**: `tipo` (`ingreso|gasto|transferencia`), `monto ≥0`, `fecha`, `concepto`, `notas`, `categoria_id?`, `cuenta_id?`, `cuenta_destino_id?` (transferencias), `propiedad_id?`, `contacto_id?`, `operacion_id?`, `origen` (`manual|ticket|comision_operacion`), `comprobante_ruta`, `comprobante_mime`, `iva`, `requiere_factura`, `cfdi_uuid?`.

### 4.12 Valuación e impuestos (resultados guardados)
- **avm_valuaciones**: `propiedad_id?`, `operacion_id?`, `entrada jsonb` (sujeto), `resultado jsonb` (valor, rango, $/m², confianza, comparables incluidos y descartados, factores, fuentes, queries, advertencias, metodología), `pdf_ruta`, `estado` (`procesando|listo|error`), `costo_usd`.
- **avm_cache_paginas**: `url_canonica` (pk), `host`, `colonia`, `ciudad`, `estado_lectura`, `texto`, `creado_en` (TTL 14 días).
- **isr_calculos**: `operacion_id?`, `propiedad_id?`, `entrada jsonb`, `resultado jsonb` (desglose completo), `valores_oficiales jsonb` (INPC/UDIS usados con fecha de publicación), `version_reglas` (año de tarifa y anexo), `pdf_ruta`.
- **indicadores_banxico**: caché persistente de INPC mensual y UDIS diarias con `fecha_publicacion`.

### 4.13 Marketing, sitio, bolsa, buscador
- **fichas** (PDF de propiedad generado): `propiedad_id`, `version_datos`, `pdf_ruta`, `creado_en`.
- **imagenes_editadas**: `origen_ruta`, `resultado_ruta`, `modo` (`mejora_automatica|edicion_ia|amueblado`), `estilo?`, `prompt?`, `marca_de_agua` (bool), `leyenda_ilustrativa` (bool).
- **video_trabajos**: `propiedad_id?`, `formato` (`16:9|9:16`), `fotos jsonb` (orden y movimiento), `estado` (`en_cola|procesando|listo|error`), `plan_ia jsonb`, `ruta_mp4`, `duracion_s`, `error`.
- **facebook_entidades**: registro de creaciones en Meta con `llave_idempotencia` única (campaña, adset, creativo, anuncio, ids externos, estado `CREANDO|ACTIVA|PAUSADA|ERROR|HUERFANA`).
- **facebook_leads**: `leadgen_id` único, `page_id`, `form_id`, `ad_id`, `campaign_id`, `payload`, `procesado`, `contacto_id`, `error`.
- **sitios**: `usuario_id` (o `org_id`), `slug` único, `activo`, `plantilla`, `nombre_publico`, `foto_url`, `bio`, `whatsapp_publico`, `anios_experiencia`, `zona_cobertura`, redes sociales. **testimonios**: `sitio_id`, `autor`, `texto`, `calificacion`, `fecha`, `verificado_por_asesor` (bool).
- **bolsa_publicaciones**: `propiedad_id`, `publicada` (bool), `comision_compartida_pct` 0–100, `notas` (≤600), `publicada_en`, `retirada_en`.
- **requerimientos_busqueda**: `oportunidad_id` (no `contacto_id` suelto), `activo`, `operacion`, `tipo`, `colonia`, `ciudad`, `estado`, `precio_min/max`, `recamaras_min`, `notas`, `ultima_busqueda_en`. **busqueda_resultados**: `requerimiento_id`, `titulo`, `url`, `portal`, `precio`, `precio_confirmado`, `snippet`, `encontrado_en`, `descartado_por_usuario`.

### 4.14 Plataforma
- **importaciones** (EasyBroker y CSV): `tipo`, `estado`, `paso`, `progreso_texto`, `resumen jsonb`, `error`, `iniciada_por`, `iniciada_en`, `terminada_en`.
- **uso_ia**, **sesiones_modulo** (segundos activos por módulo, heartbeat), **auditoria**, **webhook_eventos**, **jobs**.
- **admin_correos** (bandeja de hola@: entrantes y salientes), **facturas_cfdi** (control manual de facturación de cobros de Stripe: `id_factura_stripe` pk, `uuid_cfdi`, `estado` `pendiente|emitida|cancelada|no_requiere`, `monto`, `notas`).
- **demos_agendadas** (landing): `nombre`, `contacto`, `fecha`, `hora`, `mensaje`, `origen`, `usuario_id?`.

---

## 5. Módulos de plataforma

### 5.1 Registro, sesión y perfil
**Flujos**
1. **Registro** con email+contraseña o Google (PKCE). Campos obligatorios: nombre, apellidos, teléfono móvil MX válido (10 dígitos → E.164 `+52…`). Si viene de una invitación, el email queda fijo al de la invitación.
2. Al confirmar la cuenta, **el backend** (no el navegador, no un trigger invisible) crea en una transacción: `usuarios`, organización `personal` con el usuario como `owner`, membresía activa y estado de plan `gratis`. Idempotente (si ya existe, no duplica).
3. **Login** → si el perfil está incompleto (sin nombre/teléfono) se exige completarlo antes de entrar. Si la cuenta está desactivada, se cierra sesión con mensaje claro.
4. **Recuperar contraseña** por correo (Supabase) con pantalla de restablecimiento que valida el token.
5. **Verificación de correo existente** en registro: **no** exponer un endpoint público "¿existe este correo?" (enumeración de cuentas). El error de registro se maneja con el mensaje genérico del proveedor + opción "¿Ya tienes cuenta? Inicia sesión / recupera tu contraseña".
6. **Perfil**: editar nombre, teléfono, foto; ver plan y estado; conectar integraciones (según permiso); cambiar contraseña (requiere contraseña actual o reautenticación); cerrar sesión en todos los dispositivos.
7. **Eliminar cuenta** (requisito App Store 5.1.1(v) y LFPDPPP): doble confirmación escribiendo el correo. Dispara un **job** único (el mismo que usa el admin) que: cancela la suscripción en Stripe de inmediato, revoca tokens de Meta/WhatsApp, borra archivos del usuario en **todos** los buckets, borra filas de negocio del usuario (si es owner de empresa con otros miembros, primero exige transferir la empresa o eliminarla), borra `usuarios` y el usuario de Auth, y deja constancia en auditoría (sin datos personales). Resultado verificable (hoy la versión del usuario borra solo 7 tablas y deja datos en WhatsApp, firmas, PLD, finanzas, storage, etc.).

**Sesión en el cliente**: tokens en almacenamiento seguro del dispositivo (Keychain en iOS), refresh automático, nunca en `localStorage` junto con copias del perfil. Cierre de sesión limpia cachés locales de datos personales.

**No repetir**
- Perfil y `usuarios` escritos directo desde el navegador; creación de org personal fuera del repo.
- Endpoint público `GET /auth/correo-existe`.
- Guardar `sb_token`, `sb_user`, `pending_profile` y cachés completas de contactos en `localStorage`.

### 5.2 Organizaciones, equipo y permisos
**Reglas**
- Cuenta `personal`: un solo miembro (owner). No puede invitar.
- Cuenta `empresa`: owner + admins + agentes, con `asientos_max`. Asientos usados = miembros activos + invitaciones pendientes no vencidas. **La creación de invitación y el conteo se hacen en una transacción con bloqueo** (hoy hay condición de carrera que permite exceder asientos).
- **Convertir a empresa**: por contratación del plan Empresas (webhook de pago) o por admin de Broquer (con días de vigencia opcionales). Al convertir, el usuario queda como owner.
- **Regresar a personal** (solo admin de Broquer): el owner conserva todo lo de la org; los demás miembros quedan inactivos al instante; invitaciones pendientes se cancelan.
- **Invitar**: owner/admin captura email, rol (`admin|agente`) y permisos iniciales. Se genera liga `…/unirse?inv=<token>` (token aleatorio, se guarda solo el hash, vence en 14 días). Se puede reenviar por correo desde Broquer además de copiar la liga. Reinvitar al mismo correo reemplaza la invitación anterior.
- **Validaciones al invitar**: el correo no puede pertenecer ya a esta empresa; si pertenece a **otra empresa**, se rechaza ("debe salir de esa organización primero"); si es owner de otra empresa, se rechaza.
- **Aceptar invitación**: requiere sesión con el **mismo correo** de la invitación. La persona decide en ese momento si **se lleva sus datos** de su cuenta personal (inmuebles, contactos, oportunidades, tareas) a la empresa o los deja. (Hoy lo decide el admin al invitar: el admin no debe poder llevarse los datos personales de alguien sin su consentimiento.) Su org personal queda vacía y se elimina si no tiene datos.
- **Cambiar rol / permisos / dar de baja**: solo owner/admin; nadie se cambia a sí mismo; el owner no puede ser degradado ni dado de baja; a owner/admin no se le ponen overrides (tienen todo). Dar de baja **no borra** su historial; pierde acceso inmediato (el backend revisa membresía activa en cada request).
- **Salir de una empresa** (el propio agente): *nuevo*, hoy no existe. Sale sin llevarse los registros de la empresa; se le crea org personal vacía.
- **Transferir propiedad de la empresa** a otro admin: *nuevo*, necesario para eliminar cuenta del owner.
- **Asignar registros**: owner/admin asigna contactos, oportunidades o inmuebles (máx. 500 por operación) a un agente **activo** de la misma org, o quita la asignación. Queda actividad en cada registro.
- **Nombre de la empresa**: editable por owner/admin (2–120 caracteres).
- **Visibilidad de WhatsApp en empresa**: owner/admin pueden ver las conversaciones de las líneas de todos los miembros activos; un agente ve solo las líneas de las que es responsable. *Esto es sensible: debe estar explicado en el aviso de privacidad y en la pantalla de equipo.*

### 5.3 Planes, pagos y acceso
**Estados y resolución de acceso** (función única `tiene_acceso(org, usuario, funcion)`):
1. Usuario desactivado → sin acceso.
2. `rol_interno` en (`equipo`,`admin`) → acceso total.
3. `acceso_completo_hasta` futuro → acceso total hasta esa fecha.
4. Módulo en `modulos_desactivados` → sin acceso a ese módulo.
5. Org `empresa` activa y no vencida → plan Empresas.
6. Suscripción de la org en `active|trialing` y (si `trialing`) `prueba_hasta` futura → plan de la suscripción. Al vencer la prueba, pasa a `expired` por job programado (no "al consultar").
7. `past_due`: periodo de gracia configurable (p. ej. 3 días) y luego sin acceso premium.
8. Si no se puede determinar el estado (error de base) → **sin acceso premium** y mensaje de reintento.

**Stripe (web)**
- Checkout de suscripción para `max`; plan `ampi` como **código promocional de Stripe** (cupón), no como comparación de texto contra `"ampi2026"` en código.
- URLs de retorno solo a dominios propios configurados.
- Webhook verificado (firma + tolerancia de 5 min). Eventos: `checkout.session.completed` (crear/actualizar suscripción; si es empresas, activar org y asientos), `customer.subscription.updated` (estado, `periodo_actual_fin`, `cancelar_al_fin_de_periodo`, asientos), `customer.subscription.deleted` (cancelada; si empresas, org inactiva), `invoice.paid` (renovación), `invoice.payment_failed` (past_due + aviso al pagador).
- **Cancelar**: marca `cancel_at_period_end` en Stripe y **mantiene acceso hasta el fin del periodo pagado** (hoy se marca `canceled` de inmediato y el usuario pierde lo que ya pagó).
- **Empresas**: checkout con base (incluye 5 asientos) + asientos extra; cambiar asientos con prorrateo; no se puede bajar de los asientos usados.
- Cliente de Stripe único por organización pagadora.

**RevenueCat (iOS)**
- Webhook con secreto compartido comparado en tiempo constante. `INITIAL_PURCHASE|RENEWAL|UNCANCELLATION|NON_RENEWING_PURCHASE|SUBSCRIPTION_EXTENDED` → active (con `periodo_actual_fin`); `CANCELLATION` → sigue activa, `cancelar_al_fin_de_periodo=true`; `EXPIRATION` → expired; `BILLING_ISSUE` → past_due.
- `app_user_id` de RevenueCat = `usuario_id` de Broquer (se configura al iniciar sesión en la app).
- En iOS la app consulta RevenueCat solo para desbloquear la **interfaz** inmediatamente tras comprar; el backend sigue siendo quien autoriza (espera al webhook con reintento corto).

**Prueba gratuita**: 7 días, una vez por usuario (`prueba_usada`), sin tarjeta; al terminar, el usuario conserva sus datos y vuelve a gratis.

**No repetir**
- Paywall por interceptación de clics en el navegador y "si falla la consulta, dejar pasar".
- Endpoint `/subscription/activate` con secreto para Zapier (legado; Stripe webhook es la fuente).
- Upserts a `suscripciones` con `merge-duplicates` sin columna de conflicto (crea filas duplicadas).
- MRR del admin calculado con un precio fijo de 499 MXN por suscriptor.

### 5.4 Navegación y registro de módulos (solo lógica)
- El backend expone `GET /v1/me/modulos`: lista de módulos con `clave`, `nombre`, `grupo`, `estado` (`disponible|requiere_plan|desactivado_por_admin|oculto|proximamente`) calculado para ese usuario. El frontend pinta a partir de eso; no mantiene su propia lista hardcodeada de módulos y permisos.
- Grupos lógicos actuales: **CRM** (Inmuebles, Directorio, Clientes, Tareas, Estadísticas, Bolsa), **Seguimiento** (WhatsApp, Correo), **Documentos** (Buscador de propiedades, Contratos, Firma electrónica, Cumplimiento, Verificador documental), **Herramientas** (Estimación de valor, ISR, Finanzas), **Marketing** (Editor de imágenes, Ficha técnica, Facebook/Instagram Ads, Video, Mi sitio), **Más** (Guía/Blog, Ayuda, Perfil, Admin solo staff).
- Módulos que hoy existen pero están ocultos o sin pantalla: Bolsa (oculto), Correo (oculto), Facebook Ads (oculto), Análisis de solicitud de arrendamiento (endpoint sin pantalla), Amueblado virtual (endpoint usado solo desde video), Teléfono con IA (próximamente, fuera de este repo). Cada uno debe tener estado explícito en el registro.
- **Contexto para Broq**: cada pantalla informa a Broq en qué módulo está y qué registro tiene abierto (id), para que las acciones se apliquen ahí.
- **Telemetría de uso**: heartbeat de segundos activos por módulo (ignorar ráfagas < 5 s, inactividad > 60 s no cuenta, máximo 3,600 s por envío), enviado cada 30 s y al salir.

### 5.5 Inicio (dashboard)
Resumen del día del asesor, calculado en el backend en un solo endpoint:
- Tareas y citas de hoy y vencidas (con vínculos).
- Conversaciones de WhatsApp sin leer / esperando respuesta humana.
- Oportunidades nuevas esta semana y oportunidades "enfriándose" (sin actividad en N días, configurable; default 7).
- Inmuebles activos (estatus disponible, no archivados).
- Documentos de firma pendientes; avisos PLD próximos a vencer; inusuales con plazo de 24 h.
- Contratos generados este mes (tabla `contratos` real).
- Comisiones por cobrar (operaciones cerradas sin movimiento de ingreso).
- Frase motivacional opcional (catálogo propio).

**No repetir:** el dashboard hoy cuenta `contratos` del mes, pero ningún flujo guarda contratos: siempre sale 0.

---

## 6. CRM e inventario

### 6.1 Directorio de contactos
**Qué hace:** todas las personas y empresas con las que trabaja el asesor, sin importar su rol.
- **Alta mínima:** nombre + (teléfono **o** email). Hoy se exige teléfono siempre; un notario o colega con solo correo es válido.
- Nombre se guarda tal cual lo escribe el usuario; la versión en MAYÚSCULAS se genera solo al imprimir contratos (hoy se guarda en mayúsculas en la base).
- Teléfonos normalizados a E.164 con un solo normalizador MX: 10 dígitos → `+52`; `521XXXXXXXXXX` → `+52XXXXXXXXXX`; otros países se respetan.
- **Duplicados:** al crear/importar se busca por teléfono principal normalizado y por email dentro de la organización; se ofrece fusionar. **Fusión de contactos** (nuevo): une canales, roles, etiquetas, oportunidades, actividades, tareas, vínculos y documentos, conservando el más antiguo.
- **Filtros:** texto (nombre, teléfono, email, empresa), rol, etiqueta, agente asignado ("sin asignar" incluido), fuente.
- **Acciones rápidas:** llamar, abrir WhatsApp (si la org tiene línea conectada, abre la conversación en Broquer; si no, `wa.me`), email.
- **Selector de contacto** reutilizable desde contratos, firmas, PLD, tareas, finanzas (por componente del frontend + endpoint de búsqueda; hoy se usa `postMessage('*')` entre ventanas enviando el contacto completo, lo que expone datos a cualquier origen).
- **Ficha del contacto:** datos, roles, canales, oportunidades, inmuebles vinculados (con relación), tareas, bitácora (actividades con adjuntos), documentos (PLD, firmas, contratos), conversaciones de WhatsApp, operaciones. Registrar notas y archivos en la bitácora.
- **Borrado masivo:** seleccionados o "todos" dentro del alcance permitido; en empresa solo con permiso `eliminar_registros`; lotes de 200; se reporta cuántos se borraron y cuántos no por permisos. Borrar un contacto **no** borra operaciones/firmas/PLD ligados (se bloquea o se archiva; la evidencia legal no se destruye).
- **Exportar** (con permiso `exportar`): CSV.
- **Permisos de lectura:** `ver_contactos_equipo` y `ver_telefonos` aplicados en el backend (máscara `••••1234`).
- **Edición concurrente:** actualizaciones parciales (PATCH de campos cambiados) con control de versión (`actualizado_en` como precondición); nunca "upsert del objeto completo" que pisa lo que otro cambió. **Editar un contacto no cambia su `creado_por`** (hoy el upsert pone `user_id` del editor: el registro "cambia de dueño" al editarlo).

### 6.2 Clientes (pipeline de oportunidades)
- Tablero por etapas de la organización; mover una tarjeta cambia `etapa_id`, escribe `historial_etapas` y una actividad "Etapa: A → B".
- Crear oportunidad desde: contacto, WhatsApp (IA o manual), sitio web, Lead Ads, historial de EasyBroker, Broq.
- Datos: tipo, presupuesto, forma de pago, zona, temperatura, score, probabilidad, requerimiento de búsqueda (6.6), inmuebles ofrecidos/interesados.
- Etapas configurables por organización (nombre, orden, tipo abierta/ganada/perdida); al marcar perdida se pide motivo.
- "Enfriándose": oportunidad abierta sin actividad en N días → aparece en Inicio y puede generar tarea de seguimiento automática (configurable).
- **No repetir:** `clientes.html`/`clientes-ficha.js` son copias casi idénticas de `contactos.html`/`contactos-ficha.js`. Debe ser un solo módulo con dos vistas.

### 6.3 Inmuebles
**Alta y edición**
- Obligatorios para guardar: tipo, al menos una operación con precio, colonia y municipio/estado. Título se sugiere automáticamente ("Casa en venta · Colonia"), editable.
- Fotos: subir, reordenar (la primera es portada), quitar; compresión en cliente (lado largo ≤ 2,560 px) y conversión HEIC→JPG en servidor; límite por inmueble configurable (p. ej. 40).
- Precio con formato; moneda MXN/USD.
- **Comisión** por operación: venta en %; renta en meses de renta; o monto fijo. **Comisión real** se captura al cerrar (y se sugiere la estimada: venta = precio × %/100; renta = precio × meses).
- Estatus con historial (Anexo A). Cambiar a vendida/rentada propone: crear/cerrar la operación, capturar comisión real, retirar de bolsa, desactivar anuncios activos.
- **Duplicar** inmueble (copia con estatus `disponible`, sin fotos compartidas mutables, sin id externo).
- **Archivar** / desarchivar (no borra).
- **Borrado masivo** (con permiso): borra registros y agenda borrado de fotos del storage en job.
- **Importar CSV**: columnas `titulo, tipo, operacion, estatus, precio, moneda, calle, num_exterior, num_interior, colonia, ciudad, estado, cp, m2_construccion, m2_terreno, recamaras, banos, medio_bano, estacionamientos, anio_construccion, mantenimiento, descripcion, amenidades, etiquetas, clave_interna, notas`; obligatorias `titulo, tipo, operacion, precio, colonia`; numéricas validadas; vista previa con errores por fila antes de confirmar.
- **Asignación** a agente (owner/admin).
- **Ficha del inmueble:** detalles, fotos, operaciones y precios, interesados (contactos vinculados), tareas, bitácora, documentos (contratos, firmas, avalúos, ISR), conversaciones de WhatsApp donde se envió, estadísticas del inmueble (demanda, visitas, chats), acciones: generar ficha PDF, video, anuncio, publicar en bolsa, estimar valor, mandar a firma.
- **Permisos:** `ver_inventario_completo`, `editar_registros_ajenos`, `ver_comisiones` en backend.
- **Inmuebles recibidos por WhatsApp** entran con estatus `borrador_whatsapp` (no visibles en sitio, bolsa ni búsquedas de la IA) hasta que un humano los revise.

**No repetir**
- `banos` y superficies convertidos a entero en el alta desde WhatsApp (se pierden medios baños y decimales).
- Estatus inconsistentes entre módulos: la bolsa solo acepta `activa`; la búsqueda de la IA excluye una lista; el dashboard cuenta `activa` no archivada; las estadísticas usan otra lista. Debe haber **un solo** criterio "disponible para ofrecer" (Anexo A).
- Fotos como arreglo de URLs en la fila (y fotos base64 históricas).

### 6.4 Tareas y agenda
- Crear con título, tipo, fecha **y hora** (en la zona de la org), duración, vínculos (contactos, inmuebles, oportunidad, operación), recordatorio.
- Vistas: hoy, vencidas, próximas, completadas; filtro por vínculo y por agente.
- Completar/reabrir. Al completar, actividad en cada registro vinculado.
- **Recordatorios:** job cada minuto. Toma tareas no completadas con `inicio` y sin recordatorio enviado, cuyo `inicio − recordatorio_min_antes ≤ ahora` y que no tengan más de 6 h de vencidas. Push: "Título — en N minutos" / "está por comenzar" / "ya venció". Si se cambia la fecha, se resetea el recordatorio.
- **Citas con prospectos** (desde WhatsApp o manual): generan tarea tipo `visita` + archivo `.ics` (con zona horaria) que se envía al prospecto; aviso push al asesor.
- **Detección de conflicto** (nuevo): al agendar una visita, avisar si el asesor ya tiene otra cita que se empalma.
- Actividad reciente (feed de actividades de la org según permisos).

### 6.5 Estadísticas
Todo se calcula en el backend con datos estructurados (nada de adivinar por texto). Periodos: semana (7 días), mes (30), trimestre (90), todo. Alcance: personal o equipo (permiso `ver_estadisticas_equipo`).

- **Captación:** contactos nuevos; oportunidades nuevas; oportunidades ganadas en el periodo (entradas a etapa tipo `ganada`); tasa de conversión = ganadas / nuevas; **mediana** de días de creación a primer cambio de etapa (ignorando negativos y > 5 años).
- **Fuentes:** oportunidades nuevas por fuente y conversión por fuente (ordenado por tasa y luego volumen).
- **Embudo:** oportunidades por etapa.
- **Inventario:** captados en periodo; cerrados (cambio a vendida/rentada **dentro** del periodo, por historial); vendidos/rentados; inventario disponible; valor del inventario disponible por moneda; valor cerrado; días en mercado (captación → cierre, promedio y mediana); precio promedio disponible; comisión potencial del inventario (según ver_comisiones); comisión ganada (real o, si falta, estimada, marcándolo); m² promedio; antigüedad promedio del inventario.
- **Ranking de demanda por inmueble:** `demanda = interesados×3 + conversaciones×2 + visitas realizadas×4 + actividades`; con visitas agendadas/realizadas/pendientes (por tipo de tarea).
- **WhatsApp:** mensajes entrantes/salientes, salientes por IA vs asesor; tiempo de primera respuesta (mediana; pares mensaje entrante → primera salida, ignorando > 72 h), por IA y por asesor; conversaciones sin responder (último mensaje es entrante); mapa de calor día×hora (zona local); distribución de temperatura, etapa, forma de pago y score (0–24, 25–49, 50–74, 75–100); conversaciones nuevas; activas últimas 24 h; conversaciones pasadas a humano; inmuebles más enviados.
- **Actividad:** por tipo (notas, cambios de etapa, tareas completadas, otros).
- **Reporte PDF** descargable con los paneles del periodo; y generable por Broq con análisis y recomendaciones.

**No repetir:** "cierre" detectado con regex sobre el nombre de la etapa; "visita" detectada con regex sobre el título de la tarea; días en mercado con `updated_at`.

### 6.6 Buscador de propiedades (requerimientos de clientes)
- Cada oportunidad de compra/renta puede tener **un requerimiento** activo: operación, tipo, colonia, ciudad, estado, precio mín/máx, recámaras mín, notas.
- **Primero busca adentro** (nuevo): inventario propio disponible y bolsa, con los mismos filtros; muestra coincidencias internas arriba.
- Luego **busca en la web** (solo lectura de portales, jamás publicación): construye consultas (`"{tipo} en {operación} "{colonia}" "{ciudad}" [rango]"` y variantes `site:` para inmuebles24.com, lamudi.com.mx, propiedades.com, vivanuncios.com.mx, easybroker.com), consulta proveedores configurados (Google CSE, SerpAPI, Brave, Tavily; Firecrawl search solo si los otros no regresan nada), deduplica por URL canónica, excluye dominios bloqueados (Google, Facebook, Instagram, TikTok, YouTube).
- Verifica precio leyendo hasta 8 páginas de portales "premium" (con la caché de páginas del AVM); si el precio está confirmado y fuera de rango (±10 %), descarta. Guarda hasta 15 resultados (confirmados primero).
- Se escanea al guardar (si está activo y tiene colonia) y luego por job cada ~20 h (lotes de 30 por hora). **Solo notifica si hay resultados nuevos.**
- El asesor puede descartar un resultado (no vuelve a aparecer) o convertirlo en "inmueble de colega" (`es_ajena`) con la URL como fuente.

### 6.7 Bolsa inmobiliaria (inventario compartido entre asesores Broquer)
- Un asesor publica un inmueble **suyo** y **disponible** en la bolsa con comisión compartida (0–100 %) y notas (≤ 600).
- Listado nacional para cualquier usuario con sesión: filtros texto (tokens ≥2 letras, máx. 6, insensible a acentos) sobre título, colonia, ciudad, estado, descripción, tipo; ciudad; estado; tipo; operación; rango de precio; recámaras mín; baños mín; m² mín. Orden: reciente, precio asc/desc, comisión. Páginas de 24 con total.
- **Solo campos públicos:** título, tipo, operación, precio (si `mostrar_precio`), colonia, ciudad, estado, recámaras, baños, m², estacionamientos, descripción pública, hasta 12 fotos, comisión compartida, notas de bolsa, fecha, si es propia, y del captador: nombre y teléfono de contacto **público** (el que el asesor decida mostrar en bolsa, no su teléfono personal por default). Nunca calle/número si `mostrar_ubicacion_exacta = false`, nunca notas privadas ni datos del propietario.
- Contactar al captador (WhatsApp) registra actividad "interés de colaboración" en el inmueble del captador.
- Si el inmueble deja de estar disponible o se archiva, sale de la bolsa automáticamente.
- Retirar de bolsa: solo el dueño del inmueble (o admin de su org).

### 6.8 Migración desde EasyBroker
Una sola acción "Migración completa" que corre como **job** (no con llamadas HTTP del servidor a sí mismo) en 3 pasos, con progreso consultable y reanudable:
1. **Inmuebles:** API key de la organización (`gestionar_integraciones`). Estatus a importar: `published→disponible`, `reserved→reservada`, `sold→vendida`, `rented→rentada` (y `not_published→suspendida` si se pide). Máximo 1,000 inmuebles por corrida. Lista por estatus (páginas de 50) → detalle por id en lotes concurrentes de 8 con pausa de 0.5 s entre lotes; reintentos ante 429/5xx respetando `Retry-After` o backoff exponencial (1.5 s base, máx. 20 s, 5 intentos); si 4 lotes seguidos fallan completos, se pausa con mensaje "EasyBroker está limitando; se reanuda sola". Upsert por (org, id_externo). En reimportación **se conservan** notas y estatus que el asesor ya cambió en Broquer. Mapeo de tipos (Anexo A.4). Separar calle/número exterior/interior del texto de calle. Si una propiedad trae venta **y** renta, se crean ambas operaciones. Fotos: se registran las URLs externas y un job las copia a Storage en lotes, sin bloquear.
2. **Contactos:** lista de ids → detalle; teléfono principal (móvil/whatsapp), WhatsApp, primer email, empresa, descripción privada → notas privadas, etiquetas, fuente, probabilidad (`low/medium/high → baja/media/alta`), domicilio. Asignación al miembro de la org cuyo email o nombre normalizado coincide con el agente de EasyBroker; si no coincide, nota "Asesor en EasyBroker: X". Si ya existe (teléfono/email): solo se llenan campos vacíos y se unen etiquetas.
3. **Historial de leads (solicitudes de contacto):** agrupa por teléfono/email/nombre; si el contacto existe, se le crea/marca oportunidad; si no, se crea contacto + oportunidad (tipo compra, etapa nueva, fuente original, fecha más antigua, mensajes como actividades). Vincula interés con el inmueble por id público de EasyBroker.
- **Importar archivo** (Excel/CSV exportado de EasyBroker u otro): detección de encabezados por alias (nombre, apellidos, teléfono, WhatsApp, email, empresa, notas, etiquetas, fuente, probabilidad, estatus, domicilio, municipio, CP, fecha de creación, agente, códigos de propiedad, tipo), separador `,`/`;`, codificaciones utf-8/latin-1, fechas en formatos comunes, códigos `EB-XXXX` detectados en la columna de propiedades o en notas para vincular intereses. Máx. 15 MB. Validación de expansión de ZIP (xlsx) contra bombas de descompresión. Resumen: nuevos, actualizados, omitidos, vínculos, sin propiedad, errores.
- Diagnóstico de conexión (solo lectura) para soporte.
- **"Eliminar de Broquer no elimina de EasyBroker"** debe decirse al borrar.

**No repetir**
- `EB_API_KEY` global del dueño de Broquer usada como respaldo para **todos** los usuarios (AVM legado, autocompletar de colonias con la etiqueta "ya en tu inventario" mostrando el inventario de Grupo Navarro a cualquier cuenta) y un `config.json` que el backend escribe en disco.
- API key de EasyBroker guardada en texto plano.
- Migración que se llama a sí misma por HTTP a `127.0.0.1` con el token del usuario y estado en un diccionario en memoria.

### 6.9 Captura de leads entrantes (común)
Todo lead externo (sitio web, Lead Ads, WhatsApp, formulario de demo propio del asesor) pasa por **un solo servicio** `registrar_lead(org, canal, datos, contexto)`:
1. Normaliza teléfono/email; busca contacto existente en la org.
2. Existe → agrega canal si falta, abre oportunidad si no hay abierta, agrega actividad con el mensaje.
3. No existe → crea contacto (fuente = canal), oportunidad (etapa nueva) y actividad.
4. Asigna: al dueño del sitio/página/línea; en empresa, según regla de reparto (nuevo, configurable: al responsable del canal, round-robin o sin asignar).
5. Vincula inmueble de interés si el lead trae uno (anuncio, ficha del sitio, conversación).
6. Notifica (push) al asignado.
- **Sitio web:** campo trampa (honeypot) vacío obligatorio; límite 5 por hora por IP y 30 por hora por sitio; nombre obligatorio; teléfono o mensaje.
- **Lead Ads:** webhook verificado; deduplicado por `leadgen_id`; se busca la organización dueña de la página (índice por `page_id`, no búsqueda `LIKE` en JSON); se descarga el lead con el token de página; mapeo `full_name/first_name+last_name → nombre`, `email`, `phone_number`, `company_name`, `city`, `street_address`, `post_code`; campos no mapeados van a la actividad; si no trae nombre, teléfono ni email, se registra error y no se crea contacto.

---

## 7. Comunicación: WhatsApp y correo

### 7.1 WhatsApp (un solo módulo)
Hoy existen **tres** implementaciones (legado `wa_*`, variante "chatgpt" `wac_*` y `wa2_*`). Se construye **una sola**, basada en la lógica de `wa2`, con estas reglas.

**Conexión**
- Meta WhatsApp Cloud API con **Embedded Signup** (el asesor conecta su número desde Broquer). Soportar **coexistencia** (el número sigue usándose en la app WhatsApp Business del teléfono).
- Una organización puede tener varias líneas (`numeros_whatsapp`); cada línea tiene responsable. Dueño/admin ven todas; asesores solo las suyas.
- Tokens **cifrados** en BD (hoy en texto plano). Webhook con verificación de firma `X-Hub-Signature-256`.
- Salud del token: si Meta responde error 190 o 102 → `token_valido=false`, IA apagada en esa línea y push al responsable "Reconecta tu WhatsApp". Job diario de revisión.
- Coexistencia: los *echoes* (mensajes que el asesor manda desde su teléfono) se guardan como salientes manuales; `state_sync` de contactos e historial importan la agenda como contactos **conocidos**. Contactos conocidos empiezan con IA **apagada**.

**Datos por conversación**: contacto (vinculado al CRM único vía `canales_contacto`, nunca una tabla de contactos paralela), línea, modo IA (`on` / `off` / `pausada` + `pausada_hasta`), última entrada, ventana 24 h abierta hasta, etiquetas, temperatura, score, resumen, opt-out.

**Decisión "¿responde la IA?"** (función pura, con pruebas):
1. Línea con `ia_enabled=false` → no.
2. Modo de la conversación `off` → no; `pausada` y no ha vencido → no; `on` explícito → sí.
3. Si no hay modo explícito, regla global de la línea:
   - `siempre_apagada` → no.
   - `solo_nuevos` → sí solo si es **sesión nueva** (contacto nuevo, o la entrada previa fue hace ≥ `nuevos_meses × 30` días).
   - `siempre` → sí.
4. Opt-out activo → no se responde ni se envían campañas.

**Pipeline de mensaje entrante** (en cola/job, nunca en el request del webhook):
1. Guardar mensaje (idempotente por `wamid`), actualizar ventana 24 h, push al responsable.
2. Palabras de baja (`baja, stop, alto, cancelar, no molestar, darme de baja, no me escribas, unsubscribe`) → opt-out, confirmar una vez, fin.
3. Audio → transcribir (Whisper); imagen → descripción corta (visión). El texto resultante entra al pipeline.
4. Si hay **flujo de automatización activo** en la conversación → continuar flujo; fin.
5. Evaluar **disparadores de automatizaciones**; si alguno aplica → iniciar flujo; fin.
6. **Debounce 8 s**: esperar; si llegó otro entrante más nuevo, abortar (lo procesará el último). Esto agrupa ráfagas.
7. Lock por conversación (no dos respuestas simultáneas).
8. Si el remitente es el **número personal del asesor** (comparar últimos 10 dígitos) → **modo asesor** (7.1.3). Si no → **modo recepción** (7.1.2) si la decisión IA dice sí.

#### 7.1.2 Modo recepción (IA atiende prospectos)
- Contexto: entrenamiento activo de la línea (tono, info del asesor, zonas, reglas), historial últimos 16 mensajes, ficha del contacto, inventario vía herramienta.
- **Horario**: fuera del horario configurado → mensaje fuera de horario (una vez por sesión) y seguir capturando datos; no agenda visitas en horarios cerrados.
- **Palabras de escalamiento** configurables (ej. "abogado", "queja", "hablar con persona") → IA `off` + push "requiere atención".
- **Tope**: máx. 25 mensajes IA por conversación sin intervención humana → pasa a humano.
- Salida estructurada (JSON validado): `reply, nombre, temperatura (frio/tibio/caliente), score 0–100, presupuesto, forma_pago (contado/credito_bancario/infonavit/fovissste/otro), busca, resumen, nota, accion`.
- Los campos extraídos actualizan contacto/oportunidad **sin pisar** datos capturados por humanos (solo rellena vacíos; cambios quedan en actividad).
- Acciones:
  - `enviar_inmuebles(filtros: operacion, tipo, colonia, zona_amplia, ciudad, precio_max, recamaras)`: ciudad es filtro duro; se busca por colonia → zona amplia → calle; solo inmuebles `disponible` de la org; envía hasta 3 fichas PDF. Si no hay: respuesta honesta ("no tengo en esa zona ahorita, lo reviso con el asesor") + push. **Nunca inventar inmuebles, precios ni disponibilidad.**
  - `agendar_visita(fecha, hora, inmueble)`: crea tarea tipo visita con vínculos (contacto, oportunidad, inmueble), mueve oportunidad a etapa "Cita", manda `.ics`, push. Debe validar contra agenda del asesor (hoy no lo hace → DEBE ofrecer solo huecos libres).
  - `registrar_inmueble` (el que escribe es propietario): crea inmueble `borrador_whatsapp` con datos y fotos recibidas en el chat, vínculo propietario, push para revisión. Nunca se publica solo.
  - `pasar_a_humano`: IA off + push.
- Falla técnica del modelo: 3 reintentos con backoff → mensaje de respaldo ("en un momento te atiende el asesor") + IA off + push.
- **Respuesta manual del asesor** (desde Broquer o echo del teléfono) → pausa la IA `pausa_duracion_min` minutos (config; 0 = apagada hasta reactivar).
- Fuera de ventana 24 h solo se puede escribir con plantilla aprobada; la UI DEBE mostrar el estado de la ventana y ofrecer plantilla en vez de caja de texto cuando esté cerrada.
- **Banco de pruebas**: el asesor simula conversaciones contra su entrenamiento sin enviar nada a Meta.

#### 7.1.3 Modo asesor (el asesor le escribe a su propia línea)
Asistente operativo por WhatsApp. Herramientas: `buscar_contactos`, `buscar_tareas`, `buscar_propiedades`, `agregar_comentario`, `crear_tarea`. Memoria corta del asesor (`asesor_ctx`). Mismas herramientas y permisos que Broq (sección 11) — **es Broq por otro canal**, no un agente distinto.

#### 7.1.4 Automatizaciones (flujos sin IA)
- Disparadores: `palabra` (≤15 palabras clave), `nuevo` (primer mensaje), `nuevo_3m` (sin mensajes en 3 meses).
- Pasos (≤12): `mensaje`, `etiqueta`, `pregunta` (guarda respuesta en nombre/presupuesto/interés/nota), `opciones` (2–6, cada una con salto `ir` a paso), `humano`, `ia` (entrega a la IA).
- Cooldown por contacto; máx. 20 pasos ejecutados por turno (anti-bucle); flujo caduca a las 24 h; respuesta no válida a opciones → 2 reintentos y luego humano.
- Editor DEBE ser un constructor de pasos con selector de tipo y destino de salto (lista de pasos), no texto libre.

#### 7.1.5 Plantillas y campañas
- Plantillas: crear (nombre, categoría MARKETING/UTILITY/AUTHENTICATION, idioma, cuerpo con variables), enviar a Meta, sincronizar estado aprobado/rechazado.
- Campañas: plantilla aprobada + segmento de contactos del CRM (etiqueta, etapa, temperatura, fuente) con variable `{nombre}`; tope 250 destinatarios por campaña; 0.5 s entre envíos (en job); excluye opt-out y sin WhatsApp; reporte enviados/entregados/leídos/fallidos (webhooks de estado).
- Entrega fallida (`failed`) de cualquier mensaje → marca error en el mensaje + push.

**No repetir**: tres módulos WA, tokens sin cifrar, funciones de pausa duplicadas con reglas distintas, contactos WA separados del CRM, ids generados en cliente (`c_<ms>`), `banos` entero (DEBE decimal: 2.5).

### 7.2 Correo (IMAP/SMTP del asesor)
- Plan Max. Conectar cuenta con presets Gmail / Outlook / iCloud (host y puertos 993 IMAP, 465/587 SMTP) o manual. Contraseña de aplicación **cifrada**.
- Validación anti-SSRF del host (no IPs privadas/locales).
- Leer bandeja (últimos N, por carpeta), leer mensaje, responder/enviar; los correos con remitente que coincide con un contacto se muestran en su ficha como actividad.
- Si el asesor no conectó cuenta: envío por relay Resend "Nombre vía Broquer" con `reply_to` al correo del asesor.
- Envíos desde Broquer (fichas, contratos, invitaciones de firma) usan este mismo servicio.

---

## 8. Documentos y cumplimiento

**Regla madre:** todo documento generado, recibido, firmado o analizado se guarda en el expediente de una **Operación** (sección 4) o, si aún no existe, del contacto/inmueble. Hoy los contratos generados no se guardan, el verificador vive en `localStorage` y el análisis de solicitud no persiste → DEBE persistir todo con versión, autor y fecha.

### 8.1 Contratos generados (arrendamiento y promesa de compraventa)
Un generador por plantilla **de servidor** (DOCX → PDF), alimentado por datos del CRM (partes = contactos, inmueble = inventario) con prellenado y edición.

**Arrendamiento — campos**
- Arrendador(es) y arrendatario(s): nombre, sexo (para concordancia gramatical "el/la arrendador(a)"), nacionalidad, identificación, domicilio, RFC opcional; persona moral con representante y poder.
- **Garantía** (DEBE ser selector, hoy el obligado solidario es obligatorio siempre): `ninguna | obligado_solidario | fiador | poliza_juridica | deposito_adicional`. Solo si es obligado solidario/fiador se piden sus datos e inmueble en garantía (escritura, folio real).
- Inmueble: domicilio completo, uso (habitacional/comercial), muebles/inventario anexo.
- Renta mensual (número; el texto en letra se genera: "$15,000.00 (QUINCE MIL PESOS 00/100 M.N.)"), día de pago, forma y cuenta de pago.
- Depósito (default = 1 renta, editable), plazo en meses (se escribe en letra), `fecha_contrato` **independiente** de `fecha_inicio` (hoy se igualan: bug), fecha fin calculada.
- Actualización anual: por INPC (fecha de aplicación = aniversario) o porcentaje fijo.
- Pena por retraso: % o monto diario, días de gracia.
- Mantenimiento, servicios a cargo de, prohibición de subarrendar, mascotas, jurisdicción (ciudad).
- Cláusulas especiales: texto libre que la IA **redacta en lenguaje jurídico** sin cambiar el sentido; se muestra antes/después para aprobar.

**Promesa de compraventa — campos**
- Promitente vendedor(es)/comprador(es) (mismos datos de partes; estado civil y régimen matrimonial → si casado en sociedad conyugal, comparece cónyuge).
- Inmueble con antecedentes de propiedad (escritura, notario, folio real), libre de gravamen sí/no.
- Precio total; **arras** (señal, penalizable) y **enganche** (anticipo a cuenta del precio) son conceptos distintos (hoy se mezclan) → dos campos; saldo y forma de pago (contado, crédito bancario, Infonavit, Fovissste, cofinavit), fecha límite de firma de escritura, notaría designada, gastos (quién paga ISR, escrituración, avalúo), entrega de posesión, pena convencional.
- Salida en letra de todos los importes con **una sola** función `numero_a_letras` (hoy hay dos).

**Acciones**: vista previa → guardar en expediente → descargar PDF/DOCX → **enviar a firma** (8.3).

### 8.2 Machotes (plantillas propias del asesor)
Para que el asesor use sus propios contratos Word.
1. Subir DOCX; se guarda snapshot inmutable.
2. **Detección de campos** (en este orden, sin duplicar): marcadores `{{ }}`, `[[ ]]`, `<< >>`, `« »`, `[MAYÚSCULAS]`, blancos `____` (≥4), y detección por IA que devuelve el **literal exacto** del texto a reemplazar + nombre sugerido + tipo (texto, número, importe, fecha, persona, inmueble). Se verifica que cada literal exista en el documento; los que no, se descartan.
3. El asesor confirma/renombra campos; se normalizan a `{{id}}` en una copia de trabajo. Cada campo: etiqueta, tipo, obligatorio, valor fijo o default, fuente CRM (ej. `arrendatario.nombre`), `auto_letras_de` (campo importe del que genera su versión en letra).
4. **Rellenar**: formulario generado desde los campos (tipado: fecha = selector de fecha, importe = número con moneda, persona = selector de contacto que llena sus subcampos); campos vacíos según modo `linea` (____), `marcador` (deja el marcador) o `vacio`.
5. Vista previa PDF, guardar en expediente, enviar a firma.
- Preserva formato del DOCX (reemplazo a nivel de *runs*, incluso cuando el marcador está partido entre runs).

### 8.3 Firma electrónica
- Tipos de documento: `promesa, arrendamiento, exclusiva, carta_intencion, convenio, otro`.
- Roles de firmante: arrendador, arrendatario, obligado solidario, fiador, promitente vendedor, promitente comprador, propietario, agente, testigo, representante legal, otro. El **agente** solo aparece como firmante en `exclusiva` y `convenio` (en los demás es intermediario, no parte).
- Crear solicitud: PDF (generado o subido) + firmantes (desde contactos: nombre, email, WhatsApp, rol, orden) + opciones: orden secuencial o paralelo, exigir INE, exigir geolocalización, vencimiento (default 30 días).
- Al crear: folio público `BRQ-XXXXXXXX` (8 caracteres, sin ambiguos), hash SHA-256 del PDF original, token único por firmante.
- **Cascada**: en modo secuencial solo se invita a quien le toca (todos los anteriores firmaron). Invitación por WhatsApp (plantilla) y, si falla o no hay, por correo.
- **Posicionamiento de firma**: el emisor coloca cajas de firma/rúbrica/fecha/nombre por firmante sobre las páginas (imágenes 110 dpi); coordenadas normalizadas 0–1. Rúbrica opcional en todas las páginas (escala 0.80).
- **Flujo del firmante** (liga pública con token):
  1. Ve el documento completo.
  2. OTP de 6 dígitos (vence 10 min, máx. 5 intentos, reenvío cada 45 s), guardado como hash ligado al token; envío por plantilla WhatsApp AUTHENTICATION, o texto si hay ventana 24 h, o correo. Verificación **atómica** (hoy hay condición de carrera).
  3. Si se exige: foto de INE (frente y reverso).
  4. Casilla "acepto" con texto de consentimiento visible; trazo de firma (PNG 400 B–1 MB, rechaza trazos vacíos); geolocalización si se exige.
  5. Se registra: IP, user agent, fecha-hora UTC, geo, hash del documento que vio, texto de consentimiento.
- **Rechazar**: motivo obligatorio → solicitud `rechazado`, firmantes pendientes cancelados, notificación al emisor.
- **Completar** (todos firmaron): sellar = estampar firmas en las posiciones sobre el PDF original + **constancia anexa** (folio, hash original, tabla de firmantes con evidencias, liga de verificación, QR) → hash del PDF firmado → enviar copia a todos → guardar en expediente.
- Estados de solicitud: `borrador | enviado | parcial | completo | rechazado | vencido | cancelado` (mismos que el modelo de datos). Job diario de vencimiento y recordatorio a pendientes (día 3 y 7).
- **Verificación pública** por folio: muestra estado, fechas, hash y nombre enmascarado de firmantes (hoy expone nombres completos) y permite subir un PDF para comparar hash.
- Recuperar trabajos de sellado fallidos con cola persistente (hoy la tabla `firma_contrato_jobs` se usa sin migración).
- Aviso legal visible: firma electrónica simple con evidencias; para escrituras se requiere notario; NOM-151 (constancia de conservación) como mejora futura opcional.

### 8.4 PLD — Prevención de lavado de dinero (LFPIORPI art. 17 fracción V)
**Expediente de cliente** (por contacto y operación)
- Tipo de persona: `fisica | moral | fideicomiso` (+ nacionalidad; extranjeros piden pasaporte y documento migratorio vigente como identificación). Campos y documentos requeridos por tipo (Anexo B). Completitud también cuenta: revisión PEP hecha y declaración de beneficiario controlador (datos del BC solo si no es la misma persona).
- Completitud % = campos + documentos requeridos presentes.
- **Liga pública** para que el cliente llene y suba sus documentos: vence 14 días, solo acepta la lista blanca de campos de su tipo, firma del cliente sobre la declaración de dueño beneficiario y origen de recursos.
- **Identificación siempre** en actividad vulnerable de fracción V (compraventa/intermediación), sin umbral; hoy solo se exige al pasar umbral → corregir.

**Evaluación de operación**
- Datos: tipo (compraventa / arrendamiento si aplica fracción XV para arrendador), monto, moneda, forma de pago con desglose (**efectivo**, transferencia, crédito, cheque), fecha, partes.
- Umbral de aviso: monto ≥ `umbral_uma × valor_uma` (fracción V: 8,025 UMA). **Valor UMA y umbrales en tabla de configuración por año**, no en código (hoy 117.31 por defecto y el analizador de solicitudes tiene cifras 2026 fijas). Verificar vigencia cada febrero.
- Acumulación: suma de operaciones del mismo cliente en 6 meses.
- **Efectivo**: validar límite de pago en efectivo del art. 32 (8,025 UMA para inmuebles) → bloquear/alertar.
- **Matriz de riesgo real** (hoy la UI tiene paso "riesgo" sin backend): factores cliente (PEP, nacionalidad/país de riesgo, persona moral opaca, actividad), producto (monto vs perfil, efectivo, terceros pagando), geografía, canal (no presencial) → nivel bajo/medio/alto con justificación guardada.
- Operación inusual (marcada por asesor o por reglas) → aviso con plazo 24 h desde que se detecta.
- **Aviso**: XML borrador conforme al esquema del SAT (validar contra XSD vigente), fecha límite día 17 del mes siguiente; **informe en ceros** mensual si no hubo avisos. Estados: borrador, listo, presentado (con acuse subido).
- Bitácora inmutable de todo cambio y consulta. Conservación 10 años.
- Resumen: expedientes incompletos, avisos por vencer, operaciones sobre umbral.
- Disclaimer: Broquer ayuda a preparar; el sujeto obligado presenta en el portal del SAT.

### 8.5 Verificador documental (checklist por operación)
Checklist por tipo de operación, **dentro de la Operación** (no en el navegador):
- **Arrendamiento** — Arrendador: INE, escritura/título, predial (≤2 años, sin adeudo), agua (≤6 meses). Arrendatario: INE, comprobante de domicilio (≤3 meses), comprobante de ingresos (≥3× renta). Garantía (según selector 8.1): INE del obligado solidario/fiador, escritura del inmueble en garantía libre de gravamen, predial.
- **Compraventa** — Inmueble: escritura inscrita en RPP, certificado de libertad de gravamen (≤3 meses), predial al corriente, agua sin adeudo (y constancia de no adeudo de mantenimiento si es condominio). Vendedor: INE, RFC, comprobante de domicilio, estado de cuenta (3 meses); acta de matrimonio si aplica. Comprador: INE, RFC, domicilio, carta de crédito si aplica. Operación: avalúo, carta de instrucción notarial.
- Cada documento: estado `pendiente | en_revision | aprobado | atencion | rechazado`, archivo, notas.
- **Análisis IA** por documento (visión; PDF se manda como documento, no como `image/jpeg` como hoy): identifica tipo, extrae datos, valida formalidades, detecta problemas (vencido, ilegible, nombre no coincide con otras piezas del expediente), recomienda; veredicto `APROBADO / ATENCIÓN / RECHAZADO`. Cruza datos entre documentos (nombre INE = escritura, domicilio = predial). El veredicto IA es sugerencia; el asesor confirma.
- Usa el gateway IA (no `/chat` ni `/chat-claude`).

### 8.6 Análisis de solicitud de arrendamiento
- Entrada: solicitud (PDF, imagen o DOCX, ≤15 MB) + hasta 5 documentos de respaldo (≤8 MB c/u). Se liga al contacto arrendatario e inmueble.
- Salida JSON validada: `puntaje 0–100`, `nivel_riesgo verde|amarillo|rojo`, `veredicto_corto`, `datos_extraidos` (nombre, edad, ocupación, ingresos mensuales, renta, ratio ingreso/renta calculado con 2 decimales, tiene aval, tiene referencias), **7 secciones fijas en orden**: Identificación, Domicilio, Empleo e ingresos, Estabilidad y referencias, Fiador o garantía, Indicadores PLD, Coherencia documental — cada una `ok|atencion|critico|faltante` + puntos concretos; `banderas_rojas`, `recomendaciones` (acciones antes de firmar).
- Rúbrica: 90–100 verde (completo, ratio ≥3×, aval sólido libre de gravamen); 75–89 verde (ratio 2.5–3×); 60–74 amarillo (ratio 2–2.5× o aval débil); 40–59 amarillo/rojo (faltan críticos, ratio 1.5–2×); 0–39 rojo (inconsistencias graves, posible falsificación, ratio <1.5×).
- Reglas: nunca inventar (null), "faltante" ≠ "crítico". El ratio y el nivel se **recalculan en servidor** a partir de los datos extraídos (no confiar en el número del modelo).
- Resultado guardado en expediente; exportable PDF.

---

## 9. Herramientas del asesor

### 9.1 Estimador de valor (AVM)
Hoy hay 5 motores (legado con llave global de EasyBroker, Apify, solo-Claude, PostGIS cercanos, búsqueda web) y solo se usa el de búsqueda web. **Se construye uno**, con comparables internos como primera fuente y web como complemento.

**Entrada** (formulario): operación (venta/renta), tipo, dirección → geocodificada (lat/lng, colonia, ciudad, estado; selector con autocompletar de Google Places, no texto libre), superficie terreno m², construcción m², recámaras, baños (decimal), estacionamientos, antigüedad (años), estado de conservación (`excelente | bueno | regular | requiere_remodelacion`), amenidades, factores negativos (lista seleccionable: frente a avenida, sin escrituras, invasión, sobre falla, vecino conflictivo, etc.).

**Pipeline**
1. **Comparables internos**: inventario de la org (y en fase posterior, agregado anónimo de Broquer) mismo tipo/operación en radio creciente 1→3→5 km (PostGIS), superficie ±40%.
2. **Vecindad**: colonias vecinas por geocodificación inversa de 8 puntos a 0.9 km alrededor.
3. **Búsqueda web**: consultas por tipo+operación+colonia/vecinas+ciudad a proveedor configurable (Google CSE/SerpAPI/Brave/Tavily); lectura de páginas (Firecrawl u otro), caché 14 días en BD; detectar páginas bloqueadas/captcha y descartarlas; extraer JSON-LD; si una página trae múltiples anuncios, marcarlo.
4. **Extracción IA** de comparables estructurados (precio, m², $/m², recámaras, colonia, URL) con reglas: nunca valor 0, factor negativo −5% venta / −3% renta cada uno, no mezclar venta y renta.
5. **Post-proceso determinista** (en código, no en el modelo):
   - Descartar comparables sin $/m² calculable.
   - Outliers: fuera de 0.4×–2.5× la mediana de $/m² → fuera.
   - Homologación por comparable: factores de superficie, edad, conservación, ubicación con **dirección correcta** (hoy los factores del frontend están invertidos: si el comparable es mejor que el sujeto, el factor debe ser < 1).
   - $/m² sujeto = mediana ponderada de homologados; valor = $/m² × superficie (construcción para casas/deptos; terreno para terrenos).
   - Si el valor del modelo difiere >15% del calculado → usar el calculado y confianza `baja`.
   - Rango ±8% (confianza alta/media) o ±15% (baja).
   - Último recurso sin $/m²: mediana de precios entre 200 mil y 100 millones, rango ±30%, confianza baja.
6. **Salida**: valor sugerido, rango, $/m², confianza, lista de comparables con URL y ajustes, explicación en lenguaje llano.
- **Guardar** el estimado ligado al inmueble/contacto (hoy no se guarda) y generar PDF de opinión de valor con el **nombre y datos del asesor real** (hoy dice "Agente Broquer®") y la leyenda "Opinión de valor comercial, no es un avalúo".
- Consume cuota IA; límite por plan.

### 9.2 Calculadora de ISR por venta de inmueble (persona física)
Motor de cálculo **en servidor**, puro y con pruebas contra cálculos notariales reales; el PDF se genera con plantilla de servidor (hoy el navegador manda HTML al backend para Chromium: inyección).

**Entradas**
- Fecha y precio de venta; fecha y costo de adquisición (o valor de avalúo/costo del autor si fue **herencia o donación**; ver abajo).
- Forma de adquisición: `compra | herencia | donacion | construccion_propia`.
- % terreno (default 20%, editable con base en avalúo o predial) y % construcción.
- Mejoras: lista de (fecha, monto, con CFDI sí/no).
- Gastos deducibles de venta: comisión (con CFDI), gastos notariales/escrituración, avalúo.
- Copropiedad: número de copropietarios y % de cada uno → cálculo por copropietario.
- ¿Casa habitación del vendedor? + ¿usó la exención en los últimos 3 años? + documentos que acreditan (INE/recibos con el domicilio).
- Estado (para ISR estatal; tasa en tabla por estado, default 5%).
- ¿Inmueble comercial/no habitacional? → IVA 16% sobre la parte de construcción.

**Cálculo**
1. Años transcurridos = entre adquisición y venta, mínimo 1, máximo 20.
2. **Factor de actualización** = INPC del mes anterior a la venta ÷ INPC del mes de adquisición, **truncado a 4 decimales**, mínimo 1. INPC desde Banxico SIE (serie cacheada en BD, job mensual). Para adquisiciones anteriores a la serie disponible usar Anexo 9 RMF (tabla en config).
3. Costo terreno actualizado = costo × % terreno × factor.
4. Construcción: costo × % construcción, depreciación 3% anual × años (máximo 80%; queda piso de 20%), × factor.
5. Mejoras: cada una con su depreciación y factor desde su fecha (solo con CFDI si posteriores a 2014).
6. **Piso**: el costo total actualizado no puede ser menor al 10% del precio de venta.
7. Deducciones = costo actualizado + mejoras + gastos de venta.
8. Ganancia = precio de venta − deducciones (si ≤ 0 → sin ISR).
9. **Exención casa habitación** (art. 93 fr. XIX-a LISR): hasta 700,000 UDIS **sobre el precio de venta** (UDI del día de la venta, Banxico). Si el precio excede, la parte gravada es proporcional: ganancia gravada = ganancia × (excedente ÷ precio) y las deducciones se aplican en esa misma proporción. Hoy el código resta las UDIS a la ganancia → **DEBE** corregirse; **Chava debe validar el criterio con su notario antes de liberar**.
10. **ISR** (art. 120 y 126): ganancia gravada ÷ años = parte anual; ISR de la parte = tarifa aplicable a esa parte; ISR total = ISR de la parte × años (mecánica simplificada de acumulación que usan notarios para el pago provisional). La tarifa usada debe ser la que corresponda al art. 126 (tarifa del art. 96 **elevada al número de meses del año de enajenación**); hoy se usa la anual fija → marcar **"verificar con notario"** y parametrizar tarifas por año en config.
11. ISR estatal = ganancia gravada × tasa estatal (acreditable), acotado a no exceder el total.
12. Pago federal al notario = ISR total − estatal.
13. IVA (si comercial) = 16% del valor de construcción en la venta.
- Casos bloqueados con mensaje: adquisición anterior a 1982 sin avalúo; datos incoherentes (venta antes de adquisición).
- Regla de comprobación: si adquisición es posterior a abril de 2014, deducciones requieren CFDI; si es anterior, basta escritura.
- Salida: desglose línea por línea (cada paso arriba con su valor), resumen "Esto pagarías", supuestos usados, disclaimer "estimación, el cálculo definitivo lo hace el notario".
- Guardar cálculo ligado al inmueble/contacto; PDF.
- **Mantenimiento**: tarifas, UMA/UDIS y reglas se actualizan cada diciembre (RMF) y abril; recordatorio interno.

### 9.3 Finanzas del asesor
- **Cuentas** (efectivo, banco, tarjeta): saldo = saldo inicial + Σ movimientos (calculado, nunca editable). Una cuenta con movimientos no se borra: se desactiva.
- **Categorías semilla** — ingresos: comisión venta, comisión renta, referidos recibidos, otros ingresos; gastos: publicidad, fotografía, gasolina, notaría, referidos pagados, sueldos, renta oficina, software, otros gastos. Editables, con tipo ingreso/gasto.
- **Movimiento**: tipo (ingreso/gasto/**transferencia** entre cuentas, que no afecta resultados), fecha, monto, cuenta, categoría, descripción, vínculos opcionales (inmueble, contacto, operación) **validados contra la org** (hoy no se verifican), comprobante.
- **Comprobantes**: almacenamiento privado; URL firmada que vence en 300 s.
- **OCR de ticket/factura**: foto → IA extrae fecha, monto, proveedor, categoría sugerida → prellena el movimiento para confirmar. Cuenta en la cuota IA (hoy no).
- **Comisiones pendientes**: inmuebles marcados vendida/rentada con comisión real capturada y sin ingreso registrado → lista "por cobrar" con botón "registrar cobro" que crea el ingreso ligado. Si hay reparto con otro asesor/inmobiliaria, la comisión neta se calcula (bruta − reparto − IVA si aplica).
- **Resumen**: por periodo (mes, trimestre, año, rango): ingresos, gastos, utilidad; por categoría, por mes, por inmueble (rentabilidad de cada captación). Exportable CSV/PDF.

---

## 10. Marketing y presencia

### 10.1 Ficha de inmueble (PDF y liga)
- Fuente: **modelo de inventario de Broquer** (hoy usa el esquema de EasyBroker).
- Contenido: fotos (portada + hasta N), título, precio y operación, características, amenidades, descripción, ubicación aproximada (mapa sin dirección exacta si el asesor lo elige), datos del asesor (nombre, foto, WhatsApp, correo, logo de la org).
- Descripción: la del inmueble; botón "mejorar con IA" (≤120 palabras, sin inventar características).
- Descarga de imágenes **solo desde el almacenamiento propio** o con guardia anti-SSRF (hoy no la tiene).
- Variantes: PDF, imagen para redes, liga pública en "Mi sitio".
- Usada por WhatsApp (enviar_inmuebles), Broq y el sitio.

### 10.2 Mejora de fotos
- Límites: 8 imágenes por lote, 12 MB por imagen, 40 MB por lote, 40 MP.
- Correcciones automáticas deterministas (OpenCV): enderezar horizonte/verticales, exposición, balance de blancos, nitidez, recorte.
- Edición generativa (Gemini) opcional: limpiar objetos, cielo. Toda imagen con cambios generativos se **marca** en metadatos y se muestra la etiqueta "editada con IA" al publicar.
- **Marca de agua**: logo/texto configurado por la organización (hoy tiene correos de Grupo Navarro fijos en código), posición y opacidad.
- Resultado se guarda como nueva versión de la foto del inmueble (no reemplaza el original).

### 10.3 Amueblado virtual
- Estilos: moderno, mexicano, minimalista, clásico. Tipo de espacio (sala, recámara, comedor, cocina, terraza).
- Leyenda obligatoria quemada en la imagen: "Amueblado virtual · imagen ilustrativa". No se puede quitar.
- No altera muros, ventanas, pisos ni vistas (instrucción al modelo + comparación visual básica).

### 10.4 Video de inmueble
- 2–8 fotos, formato 16:9 o 9:16, 5.5 s por foto, 30 fps, zoom Ken Burns hasta 1.18, fundido 0.7 s; texto opcional (precio, colonia, asesor) y música libre de derechos.
- IA propone orden y movimiento por foto (hacia dónde acercar); el asesor puede reordenar.
- Render en **job** (ffmpeg), notificación al terminar, guardado en el inmueble.

### 10.5 Facebook e Instagram (anuncios)
- Conexión OAuth con **validación del parámetro `state`** (hoy no se valida); guardar token cifrado; elegir página e ad account; Instagram vinculado a la página.
- **Crear campaña desde un inmueble** (o varios): objetivo único y coherente en todo Broquer (hoy la pantalla usa `OUTCOME_ENGAGEMENT` Click-to-Messenger/WhatsApp y Broq usa `OUTCOME_LEADS`). DEBE ser selector explícito: `mensajes (WhatsApp/Messenger)` o `formulario (Lead Ads)`.
- Campos: inmuebles (carrusel), presupuesto diario MXN, duración (días) o fecha fin, zona (radio km alrededor del inmueble o ciudad), edad, audiencia (`abierta | contactos del CRM | similar a mis contactos`), texto principal (IA sugiere, editable), llamada a la acción.
- Creación idempotente con bitácora (campaña → conjunto → anuncio): si un paso falla, se reintenta sin duplicar; reconciliación con Meta en job.
- Categoría especial de anuncios de vivienda (Housing) cuando Meta lo exija: restringe edad/segmentación → la UI oculta esos campos.
- Audiencias: subir contactos con hash SHA-256 (email/teléfono normalizados), audiencia similar 1%.
- Métricas (insights): alcance, impresiones, clics, costo por resultado, mensajes/leads; pausar/activar.
- Leads de formulario → `registrar_lead` (6.9).
- Publicación orgánica del inmueble en página e Instagram (post con fotos + descripción).
- **Nunca** publicación en portales inmobiliarios (decisión de producto).
- Confirmación explícita antes de gastar dinero (resumen con presupuesto total).

### 10.6 Mi sitio (sitio público del asesor)
- `slug` único (validado, palabras reservadas), plantilla `editorial | ejecutiva`, logo, foto, bio, zonas, redes, WhatsApp, testimonios (texto real proporcionado por el asesor, con nombre y permiso).
- Muestra inmuebles `disponible` marcados "publicar en mi sitio"; filtros por operación/tipo/precio; ficha pública por inmueble.
- Solo lectura vía vistas públicas (`usuarios_publicos`, `propiedades_publicas`) que exponen **lista blanca** de columnas (sin dirección exacta, sin datos del propietario, sin comisión).
- Formulario de contacto → `registrar_lead` con `org_id` correcto (hoy los leads del sitio quedan sin org).
- SEO: título/descr. por página, sitemap, Open Graph con foto del inmueble.
- Dominio propio: fase posterior.

---

## 11. Broq — asistente único

**Un solo agente** para app, voz y WhatsApp modo asesor. Se eliminan `/chat` (Groq) y `/chat-claude` con etiquetas `[ACCION]`.

- Modelo: claude-sonnet-4-6 vía gateway IA, tool use nativo, máx. 8 turnos de herramienta por petición.
- **Todas las herramientas se ejecutan con el contexto de la request** (org + usuario + permisos). Hoy filtran por `user_id` en vez de org y `contactos_propiedades` se lee sin filtro (fuga) → prohibido.
- **Herramientas de servidor (lectura/escritura)**: `buscar_propiedades`, `detalle_propiedad`, `buscar_contactos`, `detalle_contacto`, `buscar_tareas`, `crear_tarea`, `agregar_comentario`, `mover_oportunidad`, `resumen_cartera`, `resumen_estadisticas`, `buscar_web` (solo información pública, citar fuente).
- **Acciones de cliente** (Broq abre un módulo con datos prellenados y el usuario confirma): calcular ISR, estimar valor, generar contrato, crear contacto, crear inmueble, generar fichas, crear campaña de Facebook (siempre con confirmación de gasto), generar reporte PDF, abrir módulo.
- Toda escritura destructiva o que envía algo a terceros requiere confirmación del usuario en el chat.
- **Reglas de honestidad**: no inventar datos, precios, leyes ni resultados; si una herramienta falla, decirlo; distinguir "en tu inventario" de "en internet"; montos fiscales/legales siempre con disclaimer y enviando a la calculadora.
- Voz: dictado con Whisper + corrección del nombre "Broq" (variantes "brok", "broke", "brog").
- Historial de conversaciones por usuario (guardado en BD, borrable).
- Cuota IA por plan; mostrar consumo.

---

## 12. Operación de la plataforma

### 12.1 Notificaciones
- Push APNs (iOS) + web push opcional + centro de notificaciones in-app (tabla `notificaciones`: usuario, tipo, título, cuerpo, liga interna, leída).
- Tipos: lead nuevo, mensaje WhatsApp, requiere atención, visita agendada, recordatorio de tarea, firma completada/rechazada, token WhatsApp inválido, video listo, prueba por vencer, pago fallido.
- Preferencias por tipo y horario silencioso por usuario.
- Registro de tokens de dispositivo por usuario; se borran los inválidos que APNs rechaza.

### 12.2 Consola de administración (solo staff de Broquer)
- Acceso por rol de plataforma (`staff`), **no** por correo en código; auditado.
- **Panorama**: usuarios totales/activos (7/30 días), en prueba, pagando, MRR calculado **desde precios reales de Stripe/RevenueCat** (hoy multiplica por 499 fijo), churn mensual, conversión prueba→pago.
- **Ingresos**: facturas Stripe; marcar CFDI emitido (folio, fecha).
- **Segmentos**: nuevos sin activar (≤14 días sin acción clave), activos sin pagar (≥7 días), en riesgo (sin actividad >14 días y pagando), power users (≥2 h en 30 días), recuperables (cancelaron), sin suscripción. Exportables y usables para correo.
- **Correo**: individual o a segmento vía Resend en **job por lotes** (no uno por uno en el request), con plantilla, vista previa, baja (link de desuscripción) y registro; correos entrantes por webhook a una bandeja de soporte.
- **Usuarios**: buscar, ver org/plan/uso, cambiar rol, activar/desactivar, ajustar módulos/entitlements manuales con motivo y fecha de expiración, eliminar cuenta (mismo proceso de 5.1 con registro).
- **Uso**: IA por usuario (tokens/costo), WhatsApp mensajes, almacenamiento.

### 12.3 Modo demo
- Organización demo con datos ficticios **persistentes en BD** (hoy en memoria), reseteable por job nocturno; sin envíos reales (WhatsApp/correo/Meta simulados); banner "modo demo".

---

## 13. Transversales: IA, seguridad, integraciones y jobs

### 13.1 Gateway de IA (un solo punto)
- Todas las llamadas a modelos pasan por `servicios/ia`: elige proveedor/modelo por variable (`IA_MODELO_DEFAULT=claude-sonnet-4-6`), aplica cuota por plan **antes** de llamar, registra uso (org, usuario, módulo, tokens entrada/salida, costo estimado, latencia, éxito), reintentos con backoff en 429/5xx, timeouts, salida JSON validada con esquema (reintento 1 vez si no valida).
- Proveedores: Anthropic (texto/visión/tool use), Groq Whisper (voz), Gemini (edición de imagen). Prompts versionados en archivos, no incrustados en funciones.
- Nunca mandar a la IA datos de PLD/INE salvo en los módulos que lo requieren (verificador, PLD, análisis de solicitud) y nunca guardarlos en logs.

### 13.2 Seguridad y privacidad (requisitos, con lo que se encontró)
| DEBE | Hallazgo en el código actual |
|---|---|
| CORS con lista de orígenes permitidos (web, app Capacitor) | `allow_origins=*` |
| Rate limit y almacenamiento temporal (PDFs, límites) en Redis/BD | Diccionarios en memoria (se pierden al reiniciar, no escalan) |
| PDFs desde plantillas de servidor con datos, nunca HTML del cliente | ISR manda HTML a Chromium (inyección) |
| Descargas de URLs externas con guardia anti-SSRF | Ficha descarga imágenes de cualquier URL |
| Mensajes idénticos en registro/recuperación exista o no el correo | Enumeración de correos |
| Secretos de terceros cifrados (tokens WA/Meta, API keys EB, contraseñas IMAP) | En texto plano |
| Toda consulta filtrada por `org_id` del contexto; sin respaldo "si no hay org, usa usuario" | PATCH de propiedades con fallback de org; herramientas de Broq por `user_id`; `contactos_propiedades` sin filtro |
| Módulos y paywall verificados en servidor | Solo en el cliente |
| Datos personales no cacheados en `localStorage` (solo preferencias de UI) | Caches de contactos/inmuebles con PII |
| `postMessage` con origen explícito y validación del origen al recibir | `postMessage(..., '*')` |
| El usuario no puede modificar su rol, plan, org ni módulos | PATCH propio a `usuarios` permite más campos de los debidos |
| Upsert de contacto no cambia de dueño | Upsert reasigna propietario |
| Cancelar suscripción = al final del periodo pagado | Cancela inmediato |
| Webhooks idempotentes con clave única (Stripe event id, RevenueCat event id, `wamid`, `leadgen_id`) | RevenueCat upsert sin conflicto definido |
| Aceptar invitación con bloqueo de asientos (transacción) | Carrera: se puede exceder asientos |
| "Traer mis datos" al unirse a una empresa lo decide **el usuario** que se une | Lo decide el admin |
| Verificación pública de firmas con nombres enmascarados | Expone nombres completos |
| RLS activo en todas las tablas + backend con service role solo en servicios | Mezcla |
- Auditoría (`auditoria`): quién, qué, cuándo, antes/después para cambios de permisos, plan, eliminación, PLD, firmas, exportaciones.
- Exportar mis datos (JSON/CSV) y eliminar cuenta (5.1) — derechos ARCO; aviso de privacidad actualizado cuando cambie el tratamiento.
- Storage: buckets privados por defecto con URL firmada; públicos solo fotos de inmuebles publicados y logos.
- Logs sin PII (enmascarar teléfonos/correos/tokens).

### 13.3 Integraciones (inventario)
| Servicio | Uso | Notas |
|---|---|---|
| Supabase | Auth, Postgres (+PostGIS), Storage, RLS | Migraciones SQL idempotentes, en orden, versionadas |
| Railway | Backend y workers | Un proceso web + un worker de jobs |
| Stripe | Suscripción web, portal de cliente, facturas | Webhooks firmados |
| RevenueCat | Suscripción iOS (IAP) | Webhook con secreto; entitlements unificados con Stripe |
| Resend | Correo transaccional y masivo | Dominio verificado, bajas |
| Meta WhatsApp Cloud API | Mensajería, plantillas, Embedded Signup, coexistencia | Firma de webhook |
| Meta Graph (Facebook/Instagram) | Ads, Lead Ads, publicaciones, audiencias | Revisión de app y permisos |
| Anthropic | Texto, visión, tool use | Vía gateway |
| Groq | Whisper (voz) | Vía gateway |
| Google Gemini | Edición de imagen / amueblado | Vía gateway |
| Google Places / Geocoding | Autocompletar direcciones, coordenadas, colonias vecinas | Llave restringida |
| Buscador web (CSE/SerpAPI/Brave/Tavily) + Firecrawl | AVM y buscador de propiedades | Proveedor por variable, caché |
| Banxico SIE | INPC y UDIS | Job y caché en BD |
| APNs | Push iOS | Token por dispositivo |
| EasyBroker API | Migración de inventario y contactos | Llave por org, cifrada |
| Playwright/Chromium | PDFs desde plantillas propias | Solo HTML generado en servidor |
| ffmpeg | Video de inmueble | En worker |
| Capacitor | App iOS | Sin pagos externos visibles |

### 13.4 Jobs programados (worker persistente, no `asyncio` en el proceso web)
| Job | Frecuencia | Qué hace |
|---|---|---|
| Recordatorios de tareas | cada 1 min | Push/WhatsApp al asesor según `recordar_min_antes`; marca enviado (idempotente) |
| Buscador de propiedades para clientes | cada 20 h | Corre búsquedas guardadas (6.6), notifica coincidencias nuevas |
| Pruebas vencidas | cada hora | Termina pruebas de 7 días, quita entitlements, avisa |
| Fotos EasyBroker | continuo en cola | Copia fotos externas a Storage propio |
| Campañas WhatsApp | cola | Envío espaciado 0.5 s, estados |
| Salud de tokens (WA/Meta) | diario | Marca inválidos, apaga IA, avisa |
| Plantillas WA | cada 6 h | Sincroniza estado de aprobación |
| Firmas | diario | Vencimientos, recordatorios día 3 y 7, reintento de sellado |
| PLD | diario | Avisos por vencer (día 17), recordatorio informe en ceros |
| INPC/UDIS | diario UDIS, mensual INPC | Actualiza series Banxico |
| Reconciliación Meta Ads | cada 6 h | Estado y métricas de campañas |
| Demo | nocturno | Resetea org demo |
| Limpieza | diario | Borra temporales, cachés vencidas (AVM 14 días), cuentas en eliminación tras periodo de gracia |
| Uso/MRR | diario | Agregados para consola admin |

---

## 14. No replicar (código muerto o que se elimina)
- AVM legado (llave EB global), AVM Apify, AVM solo-Claude, AVM PostGIS aislado → se funden en el AVM único (9.1).
- `/chat` (Groq) y `/chat-claude` con etiquetas `[ACCION]` → Broq (11).
- `whatsapp.py` (tablas `wa_*`) y `whatsapp_chatgpt` (tablas `wac_*`) → WhatsApp único (7.1). `bandeja.html` legado.
- `leads.html` (solo redirige) → Clientes.
- Pantalla "Robin" de exhibición.
- Endpoint `subscription/activate` que activa plan sin pago verificado.
- Catálogo/colonias de EasyBroker con llave global y etiqueta "ya en tu inventario".
- `facebook_qa_selfcheck` expuesto en producción → solo en pruebas.
- Token fijo de feed de Instagram en código.
- Lector de noticias RSS si no tiene uso medido (confirmar con Chava; por defecto fuera).
- Generación de contratos llamando scripts por `subprocess` → servicio de plantillas (8.1).
- Homologación manual del AVM en frontend (muerta y con factores invertidos).
- Duplicados: dos `numero_a_letras`, dos sistemas de contactos, funciones de pausa de IA repetidas, múltiples listas de "estatus disponible".
- `config.json` escrito en disco por el backend; migración que se llama a sí misma por HTTP.

---

## 15. Fases de construcción y criterios de aceptación
Cada fase termina con pruebas automáticas verdes y demo funcional. No se avanza con pendientes de la anterior.

| Fase | Alcance | Criterios de aceptación |
|---|---|---|
| **F0 Cimientos** | Repo, migraciones base, auth, org/membresías, contexto de request, permisos, entitlements, gateway IA, auditoría, jobs worker, storage, CI | Usuario se registra, crea org personal; pruebas de RLS: un usuario de otra org no lee nada (tabla por tabla); cuota IA bloquea al exceder |
| **F1 CRM** | Contactos, canales, oportunidades, etapas, actividades, tareas/recordatorios, directorio, `registrar_lead` | Dedupe por teléfono/email; mover etapa registra historial; recordatorio llega al minuto correcto; tarea guarda hora real |
| **F2 Inventario** | Propiedades, operaciones venta/renta, fotos, estatus con historial, contacto↔propiedad, migración EasyBroker, importación CSV | Importar 1,000 inmuebles con pausas y reintentos; reimportar no pisa cambios del asesor; un solo criterio "disponible" |
| **F3 Equipo y planes** | Invitaciones, asientos, roles, Stripe, RevenueCat, prueba 7 días, consola admin básica | Asientos no se exceden con aceptaciones simultáneas; cancelar respeta periodo pagado; iOS sin pagos externos |
| **F4 WhatsApp** | Conexión, inbox, IA recepción, modo asesor, automatizaciones, plantillas, campañas | Tabla de verdad de `_ia_decide` cubierta; debounce agrupa ráfaga; respuesta manual pausa IA; opt-out bloquea campañas; token 190 apaga IA |
| **F5 Documentos** | Operaciones, contratos, machotes, firmas, verificador, análisis solicitud | Hash del original = hash que vio cada firmante; OTP atómico; rechazo cambia estado; contrato con `fecha_contrato ≠ fecha_inicio` |
| **F6 Cumplimiento y cálculo** | PLD, ISR, AVM, finanzas | ISR reproduce ≥3 cálculos notariales reales (±1 peso tras redondeo) — **después** de validar exención y tarifa con notario; UMA/umbrales desde config; AVM guarda estimado y descarta outliers |
| **F7 Marketing** | Ficha, fotos, amueblado, video, Facebook/Instagram, Mi sitio | Campaña creada sin duplicados tras fallo simulado; leyenda de amueblado presente; leads del sitio con org |
| **F8 Broq y pulido** | Agente único, voz, notificaciones, estadísticas, demo, bolsa, buscador | Herramientas de Broq no devuelven datos de otra org (pruebas); acciones destructivas piden confirmación |

---

## 16. Decisiones pendientes para Chava
Cada una con la propuesta recomendada; Claude Code no avanza esos puntos sin respuesta.
1. **Qué entra gratis.** Propuesta: CRM + inventario + tareas + estadísticas básicas + bolsa lectura + ficha PDF; todo IA, WhatsApp, firmas, PLD, marketing en Max.
2. **Precio y límites del plan Empresas.** Propuesta: seguir "contacto" pero definir asientos incluidos y precio por asiento extra antes de F3.
3. **Activación de la prueba de 7 días.** Propuesta: se activa sola al registrarse, una vez por persona (email + dispositivo), sin tarjeta.
4. **ISR:** confirmar con notario (a) exención 700,000 UDIS sobre precio con deducciones proporcionales y (b) tarifa art. 126 mensualizada. Hasta entonces la calculadora muestra "verificar con notario".
5. **Reparto de leads en empresas.** Propuesta: por defecto al responsable del canal; opción round-robin.
6. **Noticias RSS / funciones sin uso medido.** Propuesta: fuera de la v1.

---

## Anexo A — Enumeraciones canónicas

**A.1 Estatus de propiedad**: `disponible` (única que cuenta como "disponible para ofrecer" en bolsa, IA, sitio, estadísticas), `en_proceso`, `reservada`, `vendida`, `rentada`, `suspendida`, `no_activa`, `borrador_whatsapp` (creada por IA, requiere revisión).

**A.2 Tipo de propiedad**: `casa`, `departamento`, `terreno`, `local`, `oficina`, `bodega`, `nave_industrial`, `edificio`, `rancho`, `otro` + `subtipo` libre (ej. "en condominio", "penthouse", "loft", "quinta"). Hoy el mapeo pierde información (edificio→oficina, nave→bodega, rancho→terreno) → DEBE conservar tipo propio.

**A.3 Tipos de actividad**: `nota`, `llamada`, `whatsapp_entrante`, `whatsapp_saliente`, `correo`, `visita`, `cambio_etapa`, `cambio_estatus`, `tarea_creada`, `tarea_completada`, `documento`, `firma`, `lead_entrante`, `ia_resumen`, `importacion`, `sistema`.

**A.4 Mapeo EasyBroker → Broquer**
- Tipos: Casa, Casa en condominio (subtipo), Quinta, Villa, Casa uso de suelo → `casa`; Departamento, Departamento en condominio, Loft, Penthouse → `departamento`; Terreno, Terreno comercial → `terreno`; Local comercial, Local en centro comercial → `local`; Oficina → `oficina`; Edificio → `edificio`; Bodega comercial/industrial → `bodega`; Nave industrial → `nave_industrial`; Rancho → `rancho`; resto → `otro` con subtipo = nombre EB.
- Estatus: `published→disponible`, `reserved→reservada`, `sold→vendida`, `rented→rentada`, `not_published→suspendida` (hoy `published` se mapea a `activa`, que no existe en el modelo nuevo).

**A.5 Tipos de documento de firma**: `promesa, arrendamiento, exclusiva, carta_intencion, convenio, otro`.
**A.6 Roles de firmante**: `arrendador, arrendatario, obligado_solidario, fiador, promitente_vendedor, promitente_comprador, propietario, agente, testigo, representante_legal, otro`.
**A.7 Documentos PLD** (`pld_documentos.tipo`): `ine, pasaporte, documento_migratorio, curp, rfc` (constancia de situación fiscal), `comprobante_domicilio, acta_constitutiva, contrato_fideicomiso, poder, otro`.
**A.8 Temperatura**: `nuevo, frio, tibio, caliente`. **Forma de pago**: `contado, credito_bancario, infonavit, fovissste, cofinavit, otro`.

## Anexo B — Campos PLD requeridos
- **Persona física**: nombre, apellido paterno (materno opcional), fecha de nacimiento, nacionalidad, país de nacimiento, CURP (nacionales), RFC, ocupación/actividad económica, teléfono, email, domicilio (calle, núm. ext., núm. int. opc., colonia, municipio, estado, CP, país), identificación (tipo, número, autoridad, vigencia). Docs: identificación, CURP, constancia de situación fiscal, comprobante de domicilio.
- **Persona moral**: razón social, fecha de constitución, folio mercantil, RFC, giro, nacionalidad, domicilio completo; representante: nombre, apellidos, CURP, RFC, identificación, datos del poder (número, notario). Docs: acta constitutiva, constancia fiscal, comprobante de domicilio, poder, identificación del representante.
- **Fideicomiso**: denominación, fecha de constitución, RFC, domicilio; fiduciario/representante: nombre, apellido, CURP. Docs: contrato de fideicomiso, constancia fiscal, comprobante de domicilio, identificación del fiduciario.
- **Todos**: revisión PEP (sí/no + cargo, dependencia, parentesco si aplica, fecha de revisión), beneficiario controlador (¿es el mismo? si no: nombre, apellido, CURP) con fecha de declaración firmada, origen de recursos, propósito de la operación, nivel de riesgo con justificación.
