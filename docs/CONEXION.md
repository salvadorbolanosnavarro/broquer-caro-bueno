# Conectar los cimientos

Este procedimiento utiliza infraestructura nueva, separada de Broquer existente. No habilitar registros hasta completar F0. La interfaz publicada funciona como demostración sin servicios externos.

## Base y servicios

1. Crear un proyecto Supabase aislado. Mantener confirmación de correo obligatoria y claves de firma asimétricas RS256 o ES256. El verificador no admite HS256.
2. Aplicar las cinco migraciones con `python backend/migrar.py`, usando MIGRATIONS_DATABASE_URL de propietario. No modificar migraciones ya aplicadas.
3. El administrador debe crear dos logins distintos sin SUPERUSER, BYPASSRLS ni permisos de propietario; asignar únicamente broquer_api al de API y broquer_worker al worker. DATABASE_URL y DATABASE_WORKER_URL usan esos logins. Asegurar TLS en las conexiones.
4. Crear bucket privado broquer-privado. El endpoint implementado firma solo archivos previamente registrados en metadatos, del usuario y organización autenticados. No hay endpoint de carga todavía. Configurar SUPABASE_STORAGE_KEY únicamente en API.
5. Desplegar dos procesos Railway desde backend/Dockerfile con contexto raíz: API `python -m uvicorn broquer.main:app --host 0.0.0.0 --port 8000` y worker `python -m broquer.worker`. Separar sus variables: el worker no necesita clave de Storage o Supabase Auth. Salud `/salud`; estado `/v1/estado` informa configuración, no certifica conectividad.

## Secretos y origen

Copiar los nombres de backend/.env.example al gestor de secretos del servicio; nunca pegar secretos en el chat o guardarlos en Git. Establecer SITIO_URL al origen exacto de la interfaz, sin barra final, y agregarlo a ORIGENES_PERMITIDOS.

Generar PROXY_SECRET y RATE_LIMIT_SECRET distintos, aleatorios, de al menos 32 caracteres. Generar claves Fernet mediante cryptography. SESIONES_CLAVES es un array JSON: la primera cifra las nuevas sesiones y las anteriores permiten descifrar sesiones existentes. No retirar claves antiguas hasta revocar o migrar esas sesiones.

En Sites establecer BROQUER_API_URL a la raíz HTTPS de API y BROQUER_PROXY_SECRET al mismo PROXY_SECRET. Nunca usar variables NEXT_PUBLIC. El proxy transmite únicamente cookies reconocidas y la IP aportada por la plataforma; la API exige secreto y origen en mutaciones. El acceso directo del navegador a API no forma parte de esta arquitectura.

## Correo y Google

En Supabase configurar Site URL y redirección permitida a SITIO_URL/acceso/confirmar. Configurar SMTP y probar entrega. Las plantillas deben dirigir a `{{ .SiteURL }}/acceso/confirmar?token_hash={{ .TokenHash }}&type=email` para confirmación, y `{{ .SiteURL }}/acceso/confirmar?token_hash={{ .TokenHash }}&type=recovery` para recuperación. La pantalla elimina el token de la URL y requiere pulsar Continuar antes de consumirlo. No usar la plantilla implícita que entrega access_token en el fragmento.

Configurar el proveedor Google en Supabase y su callback allí. GOOGLE_HABILITADO permanece false hasta probar el ciclo PKCE desde el mismo navegador. REGISTRO_HABILITADO permanece false hasta cerrar privacidad, soporte, eliminación de cuenta y pruebas F0.

## Validación pendiente obligatoria

Usar exclusivamente una base desechable con migraciones para BROQUER_TEST_DATABASE_URL. Ejecutar `python -m pytest -c backend/pytest.ini backend/tests -q`. Las quince pruebas PostgreSQL no deben omitirse en esa validación. La suite SQL local `node backend/tests/sql/rls.mjs` usa PostgreSQL WASM con auth.users de prueba; no sustituye Supabase ni pruebas concurrentes.

Probar con dos usuarios reales: registro y confirmación, enlace vencido y reutilizado, Google, completar perfil, renovar sesión, cerrar una/todas, cambiar contraseña, recuperar sin dar acceso a otras rutas, cuenta desactivada, intentos limitados y archivos ajenos. Confirmar aislamiento bajo los logins de runtime, no solamente SET ROLE del propietario. Configurar monitoreo sin cuerpos, cookies ni tokens; backups y restauración, limpieza programada de sesiones y ventanas de límite expiradas. Definir retención antes de datos reales.

Para IA, cargar tarifas revisadas en broquer.precios_ia y decisiones de cuotas en plan_funciones. No se incluyen precios inventados ni se activa un proveedor. El worker solo tiene el diagnóstico verificar_cola; no encolar trabajos de negocio todavía.

## Cola de trabajos

Los módulos llaman internamente a core.cola.encolar después de comprobar permisos, cuotas y validar su entrada. La clave de idempotencia identifica una intención del usuario: reusar la clave con otros datos devuelve conflicto. El bloqueo transaccional evita dos creaciones concurrentes; el ámbito incluye organización, tipo y usuario. No existe endpoint público para encolar tipos arbitrarios.

GET /v1/trabajos/{id} devuelve únicamente el estado, fecha y mensaje de un trabajo propio. No expone datos de entrada, resultados crudos ni códigos internos del proveedor. Un ID ajeno recibe el mismo 404 que uno inexistente. Cada módulo tendrá su endpoint de resultado con sus propios permisos.

El workflow postgres_integracion usa una base efímera PostgreSQL 17 y auth.users mínimo, nunca credenciales externas. Debe ejecutarse en un runner GitHub Actions habilitado; guardar ese workflow en el repositorio de Sites no demuestra que haya corrido. La validación Supabase real permanece pendiente.
