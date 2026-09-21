# Broquer · avance de cimientos y cuentas

Fecha: 16 de septiembre de 2026. F0 iniciada; NO certificada como terminada.

## Decisiones de integración
- LOGICA.md define las reglas de producto; DISENO.md define el sistema visual.
- Broquer es la marca; Broq el asistente. La marca provisional del prototipo no se utiliza.
- El mandato de reconstrucción desde cero de LOGICA prevalece sobre la instrucción genérica de adaptar un repositorio del documento visual. Este es un proyecto nuevo y separado del repositorio anterior.
- Se mantiene API FastAPI + PostgreSQL/Supabase. Sites aloja la interfaz y un proxy HTTP, no reemplaza la base por D1 ni lleva reglas de negocio al navegador.
- La interfaz de prueba es solo lectura para operaciones. Las preferencias de favoritas son locales. No se presenta como el modo demo persistente de producción requerido en 12.3: ese modo se construirá en F8.
- Inicio, Agenda y Campañas son muestras visuales; no se adelantan sus módulos de negocio a F0. No hay publicaciones, gasto ni envíos reales.
- El catálogo compartido es el origen de nombres; la API real expone estados calculados. No existen módulos de producción disponibles todavía.
- Planes, precios, activación de prueba y decisiones de sección 16 siguen pendientes. No se han inventado reglas para resolverlos.

## Implementado
- Interfaz responsive: Inicio, catálogo y búsqueda, favoritas, personalización, agenda semanal de ejemplo, detalles de citas y resultados de campaña de ejemplo.
- Acceso, registro, confirmación, recuperación con cambio de contraseña, Google PKCE, perfil y espacio de cuenta sin datos ficticios. Formularios inhabilitados sin backend configurado.
- Sesiones opacas revocables: el navegador recibe un identificador; tokens del proveedor cifrados en base con rotación de claves. Renovación serializada, expiración y separación de recuperación.
- Límites persistentes de solicitudes por IP/correo con hash HMAC, sin almacenar correo en las claves del limitador.
- Proxy HTTP de mismo origen con cookies HttpOnly, filtro de cookies, validación de origen, límite de cuerpo, timeout y sin redirecciones externas.
- Estructura FastAPI modular, errores uniformes, contexto de sesión con JWT por JWKS, comprobación de cuenta y membresía activa, permisos centralizados.
- Cinco migraciones versionadas: usuarios, organizaciones, membresías, planes configurables, cuotas, uso IA, auditoría y cola de trabajos.
- Onboarding transaccional e idempotente invocado por el backend después de una sesión verificada y correo confirmado. Usa una función SQL explícita versionada, no un trigger oculto.
- Roles de base separados. Lecturas RLS, privilegios de edición de perfil por columna y aislamiento de organización.
- Reserva atómica de cuotas antes de proveedor IA; gateway inicial no expuesto a clientes; registro de uso. Cola con adquisición persistente y lease; tipos de negocio aún no registrados.
- Servicio interno de encolado con llave por usuario, exclusión transaccional de duplicados y rechazo de reintentos con datos distintos. Consulta de estado autenticada sin exponer cargas ni respuestas privadas. No se abre un endpoint genérico para ejecutar trabajos.
- CI preparado con PostgreSQL 17 desechable para aislamiento y concurrencia; pendiente ejecutar en un runner compatible.
- Pruebas unitarias y suite de integración PostgreSQL preparada para una base de pruebas aislada.

## Pendiente para cerrar F0
- Desplegar API y worker en Railway y conectar Supabase nuevo/aislado. No se ha accedido ni modificado infraestructura de Broquer existente.
- Ejecutar y pasar pruebas de migraciones, RLS, concurrencia y onboarding contra Supabase de prueba. Las pruebas omitidas no son una validación de aislamiento.
- Validar con Supabase los flujos implementados de Google PKCE, confirmación por correo, recuperación, perfil incompleto, renovación y revocación. No están certificados con proveedor real.
- Validar almacenamiento privado: metadatos y firma por propietario implementados; carga, eliminación y su ciclo completo pendientes.
- Gateway IA implementa tarifas configurables, costos por intento, reintentos limitados y validación de esquema. Faltan pruebas con proveedor y política de compensación de cuota; los intentos fallidos consumen reserva. No hay endpoint público.
- Worker con reintentos acotados, recuperación de lease y manejador SQL idempotente de diagnóstico. Manejadores de negocio externos pendientes.
- Entitlements y planes requieren las decisiones de producto de la sección 16.
- Finalizar avisos de privacidad, términos, soporte y guía para el tratamiento real de datos y eliminación de cuentas. REGISTRO_HABILITADO debe seguir falso hasta completar estos puntos.
- Por instrucción posterior del usuario, se construyen módulos y app iOS antes de la configuración manual. F0 sigue sin certificarse; avanzar implementación no equivale a aprobar sus criterios.

## Ejecución
Frontend: scripts de package.json; pnpm es el gestor del proyecto.
Backend: desde backend, `python -m pip install -r requirements-dev.txt`; `python -m uvicorn broquer.main:app`.
Pruebas: desde backend, `python -m pytest -q`.
Migraciones: `MIGRATIONS_DATABASE_URL` debe ser una conexión de propietario separada. Ejecutar `python backend/migrar.py` contra una base nueva de Supabase, nunca contra producción sin revisar.
La conexión de aplicación debe pertenecer solamente a broquer_api. El worker usa un login diferente perteneciente a broquer_worker. No usar superuser/service role como identidad de runtime. La asignación inicial de roles/login corresponde al administrador de esa base.
Integración: `BROQUER_TEST_DATABASE_URL` apunta EXCLUSIVAMENTE a una base desechable con migraciones aplicadas; la suite crea y elimina registros ficticios con UUID únicos.
Docker: construir desde la raíz con `docker build -f backend/Dockerfile .`; API en puerto 8000. El worker es un proceso separado `python -m broquer.worker`.

## Variables
Sites: BROQUER_API_URL y BROQUER_PROXY_SECRET (solo servidor; no NEXT_PUBLIC). Ver CONEXION.md.
Backend: revisar backend/.env.example. Secretos nunca al navegador ni al repositorio.
El origen exacto de Sites debe agregarse a ORIGENES_PERMITIDOS. Cookies con Secure y HttpOnly; tokens nunca en localStorage.

## Fuentes técnicas consultadas
- Supabase JWKS: https://supabase.com/docs/guides/auth/signing-keys
- Transacciones Psycopg: https://www.psycopg.org/psycopg3/docs/basic/transactions.html

## Validación realizada
- Compilación de producción y revisión TypeScript.
- 62 pruebas unitarias de backend aprobadas. 15 pruebas de integración PostgreSQL omitidas por falta de base aislada; no se declara RLS ni concurrencia certificados.
- 23 verificaciones SQL aprobadas en PostgreSQL WASM (PGlite): migraciones, RLS de tablas, sesiones, cuota y límite de intentos. No sustituyen concurrencia ni integración real con Supabase.
- Navegador: Inicio y Agenda inspeccionados a anchos de marco de 390 y 375 px; Inicio, Agenda y Campañas comprobados en escritorio.
- Personalización y persistencia de favoritas después de recargar verificadas; favorita adicional fuera de las seis iniciales visible en filtro Favoritas.
- Cambio de día y estado sin citas comprobados.
- Acceso y confirmación revisados en marcos de 390 y 375 px; recuperación y espacio protegido comprobados sin servicios conectados.
- No se ha certificado accesibilidad completa, zoom 200%, iOS real, Google, correo, Meta, pagos ni proveedores IA.

## Cambio de orden autorizado

El usuario pidió construir web y app iOS para Codemagic antes de configurar servicios manualmente. Se conserva el documento original y se aplica esta instrucción posterior: implementación adelantada con integración real pendiente, sin inventar decisiones comerciales.

- Directorio inicial: interfaz compartida web/móvil, demo interactiva en memoria, alta y edición; API con búsqueda, normalización internacional, deduplicación por org, permisos y edición parcial con control de versión. No constituye F1 completa: fusión, roles/etiquetas/canales múltiples, exportación, oportunidades, tareas y bitácora siguen pendientes.
- Proyecto Capacitor iOS generado con SPM, bundle local y codemagic.yaml para simulador y archivo firmado. No se ha ejecutado Xcode/Codemagic ni validado una IPA; sesión nativa/Keychain, deep links, APNs y RevenueCat pendientes.
- La demo no persiste datos de negocio y sus teléfonos/correos son ficticios. Servicios reales permanecen deshabilitados sin configuración.

## Oportunidades — avance F1

- Tablero compartido web/iOS con etapas abiertas, ganadas y perdidas; alta vinculada al directorio y cambio de etapa con motivo obligatorio al perder.
- API y migración de etapas, oportunidades, historial y actividades. Alta de etapas iniciales idempotente por organización, importes Decimal, control de versión, cambio e historial en una transacción, referencias de contacto/etapa dentro de la misma organización.
- Historial append-only y lectura de oportunidades propias. El acceso de equipo, configuración personalizada de etapas, captura avanzada, importaciones y alertas por inactividad siguen pendientes.
- Demo de oportunidades en memoria; su directorio de contactos se comparte en memoria entre ambas vistas mientras la app permanece abierta. La versión conectada usa un directorio compartido en PostgreSQL.
- F1 sigue incompleta. No se activaron recordatorios, envíos ni proveedores externos.

Validación del tablero: cambio a Perdida con motivo probado en navegador; compilaciones web, móvil y TypeScript aprobadas. No equivale a prueba de integración real.

### Avance 18 septiembre — notas de seguimiento
- Clientes web y paquete iOS: agregar notas de hasta 4000 caracteres al historial de la oportunidad, con fecha; sin edición ni borrado.
- API: POST /v1/crm/oportunidades/{id}/actividad, autor/organización/tipo determinados por el servidor, acceso por permisos y RLS existentes.
- Demo mantiene las notas mientras permanece abierto el tablero. No representa persistencia real; los servicios externos siguen pendientes.
- Validación: 68 pruebas Python aprobadas, 15 de integración omitidas por falta de PostgreSQL configurado; TypeScript, web y sincronización iOS aprobados. Navegación Inicio → Clientes y agregar nota probados en navegador local, sin verificar el navegador del usuario ni iOS nativo.

### Avance 18 septiembre — tareas y agenda operativa
- Sustituida la agenda de muestra por flujo interactivo compartido web/iOS: crear, editar, completar, reabrir, buscar y vistas Hoy/Vencidas/Próximas/Completadas; aviso de empalmes y descarga ICS en web.
- API propia con migración 006: tareas aisladas por organización y responsable, vínculo opcional a oportunidad, bitácora al crear/completar/reabrir/editar, auditoría y control de versiones para evitar sobrescrituras.
- Horas guardadas en UTC y convertidas desde la zona horaria de la organización. Rechaza horas inexistentes o ambiguas por cambios de horario. ICS usa UTC, escapado y plegado UTF-8.
- Las cuentas reales ofrecen Agenda, Clientes y Directorio; el proxy ahora conserva parámetros de búsqueda y límites, que antes se perdían.
- Validado: 80 pruebas Python, 24 comprobaciones SQL WASM, 3 pruebas de hora/conflicto/ICS, TypeScript y paquete móvil. 16 integraciones PostgreSQL permanecen omitidas sin base desechable. Navegador local: crear, advertir empalme, completar, reabrir, editar y mostrar 10:35 exactas en Próximas.
- Pendiente de este módulo: recordatorios automáticos y entrega push, vista por agente/equipo, vínculos con contactos/inmuebles/operaciones, tareas de día completo, paginación completa. La demo es temporal; vincular oportunidades requiere el modo con API. No se validó iOS con Xcode ni se afirma persistencia conectada.

### Avance 18 septiembre — inventario y configuración CRM
- Inmuebles compartido web/iOS: alta, edición, venta y renta simultáneas, precios MXN/USD, superficies y baños decimales, ficha, búsqueda/filtros, estatus, notas, duplicar, archivar/restaurar. Imagen de muestra solo en el inmueble ficticio correspondiente.
- API + migración 007: propiedades y operaciones separadas, unicidad de clave por organización, permisos de lectura/edición, control de versiones y paginación. Disponibilidad explícita: estatus disponible y sin archivo.
- La bitácora de inmuebles usa la tabla común de actividades, que ahora acepta vínculos a propiedad y oportunidad. Agenda real permite vincular un inmueble editable; completar/reabrir queda registrado en su bitácora.
- Configuración de etapas compartida web/iOS + migración 008: agregar, renombrar y reordenar; solo owner/admin en API. Revisión de concurrencia, IDs estables, sin borrar etapas ni cambiar el tipo de las existentes. Las nuevas cuentas y la demo usan las etapas canónicas del brief: Futuro, Nuevo, Contactado, Activo, Cerrado, Descartado. No se renombran automáticamente las etapas existentes.
- Se deshabilitan las acciones principales de Clientes/Inmuebles hasta que el navegador termine de activarlas, para evitar pulsaciones sin respuesta durante la carga.
- Validación local: 106 pruebas Python aprobadas; 18 integraciones PostgreSQL omitidas sin base desechable; 26 comprobaciones PostgreSQL WASM. UI: alta con dos operaciones y 2.5 baños/185.75 m², notas, cambio de estatus, duplicación y archivo, configuración de etapas sin perder oportunidades. Vista móvil de 390px revisada; compilación iOS no equivale a prueba con Xcode.
- Pendiente del inventario: fotografías propias/subida/reordenado y borrado de storage, CSV/EasyBroker, asignación de equipo, comisiones, propietario/interesados y cierre de operaciones con acciones externas. La configuración manual permanece al final; esta publicación sigue siendo una demo temporal, sin servicios conectados.

### Avance 18 septiembre — Finanzas del asesor
- Web y paquete móvil: cuentas, ingresos, gastos y transferencias, categorías semilla editables, filtros de fecha/cuenta y resumen por moneda; CSV de la página visible en web. Saldo calculado, nunca editable; cuentas desactivables sin borrar historial.
- API y migración 009: movimientos con importes Decimal exactos (JSON como cadena), idempotencia por solicitud, control de versiones, anulación con motivo y auditoría. Transferencias entre cuentas propias de igual moneda, sin inflar ingresos/gastos. RLS privada por asesor dentro de su organización; no incluye aún finanzas compartidas de empresa.
- Vínculo opcional a inmueble en UI; API valida también contacto dentro de la organización. La demo usa centavos enteros BigInt; cada moneda se mantiene separada.
- Validación: 120 pruebas Python aprobadas, 19 integraciones PostgreSQL omitidas por falta de base desechable; 27 comprobaciones SQL WASM y 7 pruebas JS. TypeScript, compilación web y bundle/sincronización iOS aprobados. Navegador local: transferencia de 250.25, conservación del resultado, saldos exactos, anulación con reversión, renombrar categoría y validación de rango. Diseño revisado a 390 px y filtros corregidos para evitar solapamientos.
- Pendiente: comprobantes privados, OCR sujeto a cuota, vínculo a operación, selector de contacto en UI, comisiones por cobrar, desglose/gráficas por categoría/mes/inmueble, PDF y exportación de todo el periodo. Los servicios siguen sin conectar y la demo pierde cambios al salir/recargar. No se ha ejecutado Codemagic/Xcode ni probado una IPA.

### Avance 19 septiembre — reportes y exportación financiera
- Reportes compartidos web/móvil por mes, categoría e inmueble, con barras comparativas y cifras exactas; periodos rápidos mes/trimestre/año hasta hoy. Cada moneda se presenta por separado. Se excluyen transferencias y anulados del resultado.
- API de agregados sobre todo el periodo, independiente de la paginación. Propiedades no visibles quedan agrupadas sin revelar su identidad. Conserva RLS privada por asesor. Límite explícito de 5,000 grupos, sin resultados parciales silenciosos.
- Exportación CSV del periodo completo (todas sus monedas), con los filtros de fecha/cuenta; incluye el estado anulado. Límite de 10,000 registros: si lo supera, exige acotar filtros sin descargar un archivo truncado. Se neutralizan fórmulas de hoja de cálculo y se preservan decimales exactos. Exportación disponible solo en web.
- Validación: 123 pruebas Python en total (122 suite completa + nueva prueba de límite, 17 pruebas del módulo); 19 integraciones nativas permanecen omitidas. 9 pruebas JS aprobadas. Navegador local: reporte mensual, categoría, trimestre, exportación de 3 registros demo y reporte de Casa del Encino a 390 px. No se probaron los nuevos endpoints contra Supabase real; se amplió su prueba de integración pendiente.
- Permanecen pendientes PDF, comprobantes/OCR, comisiones por cobrar, enlaces a operaciones y configuración de proveedores. App iOS sigue sin validación Xcode/Codemagic.

### Avance 19 septiembre — selector compartido de contactos
- Clientes y Finanzas comparten un selector que busca por nombre, empresa o correo, limita a 30 resultados y distingue carga, vacío, error y resultados adicionales.
- La búsqueda remota espera 250 ms y ahora cancela físicamente la solicitud anterior al cambiar el texto, cerrar el panel o desmontar el componente. Además del descarte de respuestas obsoletas, esto evita trabajo innecesario y elimina la posibilidad de que un error de una consulta cancelada reemplace el estado de la búsqueda vigente.
- Pendiente de validación visual en un navegador con dependencias instaladas: selección por teclado, cierre/reapertura, nombres repetidos y los flujos completos de alta de oportunidad y movimiento financiero. La integración con PostgreSQL desechable sigue pendiente.
