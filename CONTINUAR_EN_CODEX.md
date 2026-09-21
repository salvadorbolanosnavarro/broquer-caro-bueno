# Broquer — traspaso a Codex (19 septiembre 2026)

## Objetivo y autorización
Continuar esta reconstrucción de Broquer hasta completar los requisitos de docs/LOGICA.md y docs/DISENO.md en web y app iOS compatible con Codemagic. El usuario autorizó dejar credenciales y configuración externa para el final. No reiniciar, no sustituir el proyecto por otra plantilla, no confundirlo con el repositorio anterior Brokr-main/PR44. No afirmar que solo faltan variables: todavía faltan módulos y flujos completos. Trabajar por bloques coherentes, con comprobaciones enfocadas y actualizaciones breves, sin pedir «continúa» tras cada cambio pequeño.

## Lectura inicial
1. Este documento.
2. docs/ESTADO.md (histórico; las entradas posteriores actualizan las anteriores).
3. docs/LOGICA.md y docs/DISENO.md: elaborar una lista de cobertura verificable por requisito, priorizando dependencias; no releerlos completos en cada turno.
4. docs/CONEXION.md y docs/IOS.md cuando sean necesarios.

## Arquitectura existente
- React/TypeScript, Vinext/Vite y componentes Radix/shadcn instalados; conservar pnpm y lockfile.
- Backend FastAPI/Python, único escritor de negocio; PostgreSQL/Supabase Auth/Storage previstos; Railway previsto para API y worker.
- BFF app/api/v1/[...ruta]/route.ts: JSON same-origin, cookies HttpOnly, secretos solo servidor, origen validado, límite de cuerpo. No usar service role como identidad del runtime.
- Migraciones backend/migrations/001…009. Ejecutarlas únicamente en una base desechable para pruebas hasta la configuración final.
- Capacitor: mobile/main.tsx comparte UI, ios/ contiene proyecto nativo y codemagic.yaml los flujos simulador/firmado. Bundle provisional app.broquer.mobile. No se ha probado Xcode/Codemagic ni generado IPA validada. Sesión nativa/Keychain, deep links, APNs, RevenueCat y eliminación completa de cuenta siguen pendientes.
- Demo temporal de negocio en memoria. Solo preferencias se guardan localmente; no migrar datos sensibles a localStorage para aparentar persistencia.
- EnlaceModulo usa enlaces nativos en web e historial en Capacitor; se cambió por el problema de tarjetas que solo recibían foco. Preservarlo.

## Implementado parcialmente
Inicio modular, acceso por correo y base de sesiones; directorio con altas/edición/deduplicación; oportunidades con etapas configurables y bitácora; agenda con tareas, vínculos e ICS; inventario con venta/renta, notas, duplicación y archivo; finanzas con cuentas, ledger exacto, transferencias, anulación, categorías, reportes y CSV de periodo. No equivale a fases completas del brief.
No hay servicios de producción conectados. Logos oficiales no entregados en este checkout: no inventarlos ni afirmar que el wordmark temporal es el original.

## Estado exacto al entregar
Última versión publicada estable: v12, commit f77f97168489a5b869a73f960ded7e92b4f340a2.
Sitio privado: https://broquer-workspace.salvadorbolanosnavar.chatgpt.site
Este paquete incluye un avance POSTERIOR, NO PUBLICADO y aún en revisión:
- Nuevo components/crm/selector-contacto.tsx: búsqueda por nombre/empresa/correo, debounce, descarte de respuestas obsoletas, estados carga/error/vacío, máximo 30 coincidencias con aviso para afinar búsqueda. Usa Popover + Command existentes y endpoint contactos?q=….
- Clientes usa ese selector; Finanzas permite asociar contacto y mostrar su nombre. Backend agrega LEFT JOIN de contacto sujeto a RLS en listado de movimientos.
- TypeScript aprobado; suite Python 123 aprobadas / 19 integraciones PostgreSQL omitidas por falta de base desechable.
- QA pendiente: el popover mostró «ResizeObserver loop completed with undelivered notifications» en preview de desarrollo. Se agregó altura fija de lista y se deshabilitó animación del panel, PERO NO SE VERIFICÓ AÚN la corrección. Una recarga HMR cerró el formulario y dejó inválido el locator del intento posterior; no atribuir ese timeout automáticamente al producto. Retomar con DOM actual y probar selección, teclado, cierre/reapertura, alta de oportunidad y movimiento con contacto; comprobar móvil.
- No se ejecutó build web/móvil después de este último selector. NO presentarlo como terminado.

## Próximo trabajo
1. Resolver/verificar el selector y terminar sus dos flujos. Probar nombres repetidos, ausencia de resultados, cambio rápido de búsqueda y permisos en integración cuando haya base desechable.
2. Completar mapa de cobertura del brief y avanzar funcionalidades enteras según dependencias, en lugar de seguir añadiendo detalles aislados a Finanzas.
3. Faltan, entre otros: inventario con fotos/storage y comisiones; operaciones y relaciones contacto-propiedad; importaciones; funciones de equipo; canales WhatsApp/correo; contratos/firma/PLD; IA y cuotas completas; marketing/fichas/sitio; suscripciones; experiencia nativa y eliminación de cuenta. Ver documentos para alcance real. No habilitar cálculos fiscales como certificados sin validación requerida.
4. Mantener configuración manual final en lista única: cuentas/proveedores, secretos, dominios, firma Apple, logos y validaciones externas. Construir adaptadores con estados claros cuando falten credenciales, sin simular éxito real.

## Entorno y comandos
Node >=22.13.0; pnpm 11.25.0 según package.json; Python 3.12 usado en pruebas. macOS/Xcode solo para compilar iOS localmente; Codemagic ofrece ese entorno después de conectar el repositorio.
En un equipo nuevo usar `pnpm install --frozen-lockfile`. No usar install:ci fuera del entorno Linux de Sites (contiene herramientas y rutas propias de ese entorno). scripts/run-framework.mjs selecciona modo portable si falta el perfil local ignorado.

```sh
pnpm dev
pnpm exec tsc --noEmit
pnpm build
pnpm mobile:sync
python -m venv .venv
# Activar el entorno según el sistema operativo.
python -m pip install -r backend/requirements-dev.txt
python -m pytest -c backend/pytest.ini backend/tests -q
node --test tests/agenda.test.mjs tests/finanzas.test.mjs
node backend/tests/sql/rls.mjs
```

No ejecutar todas las suites tras cada edición reversible. Usar pruebas relevantes al riesgo y una compilación final por bloque. PGlite/WASM no certifica Supabase ni concurrencia real. BROQUER_TEST_DATABASE_URL debe apuntar SOLO a una base desechable; hay limpieza de registros en pruebas.

## Herramientas y publicación
Se necesitan acceso a esta carpeta, terminal, Git y navegador/preview para QA. No es necesario instalar conectores de Figma, Slack, Notion ni otros para continuar el código. GitHub privado es opcional para respaldar/conectar Codemagic; no se creó un GitHub en esta conversación.
Este ZIP es el código fuente, no la web compilada: no incluye node_modules, credenciales, .git ni resultados de build. Si se abre como carpeta sin Git, inicializar un repositorio local y rama de trabajo; no inventar un remote.
El origen existente es Git de Sites, no GitHub. No asumir que Codex tendrá acceso automático ni copiar credenciales de Work. .openai/hosting.json identifica el Site existente; si está disponible el plugin Sites, reutilizar ese ID y seguir sus instrucciones. Si no lo está, desarrollar y validar localmente sin intentar publicar con credenciales inventadas ni reemplazar el sitio. La decisión de migrar hosting queda pendiente.

## Eficiencia
- Conservar un registro corto de decisiones y checklist; leer solo archivos relevantes.
- Agrupar cambios por objetivos de producto; evitar releer instrucciones y lanzar pruebas amplias redundantes.
- No desplegar cada ajuste de CSS; validar un bloque completo y luego publicar cuando corresponda.
- No iniciar subagentes ni habilitar servicios adicionales por defecto.
- No declarar éxito sin evidencia; informar brevemente de cualquier bloqueo real.
