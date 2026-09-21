# modo — Diseño móvil primero para agentes inmobiliarios

Versión 2 · Sustituye las reglas de la primera propuesta · Septiembre de 2026

## 1. La decisión de producto

Diseñamos software de trabajo para agentes inmobiliarios mexicanos, de distintas edades y niveles de experiencia tecnológica. El usuario vende servicios y propiedades; necesita encontrar una herramienta, preparar una visita o revisar sus campañas sin aprender jerga de software.

La referencia a Steve Jobs describe el nivel de precisión y sencillez buscado. No implica copiar una interfaz de Apple ni presentarse como un producto de esa marca.

**Orden de trabajo:** primero resolver la experiencia móvil. Después extenderla a escritorio conservando nombres, jerarquía y acciones. No diseñar un panel de escritorio y comprimirlo.

El alcance sigue siendo una pantalla principal y dos subpantallas: Inicio, Campañas y Agenda. Las otras cuatro herramientas son conceptos seleccionables. La marca modo es provisional; no reemplazar la marca real del proyecto receptor.

## 2. Cómo se consideró el conjunto de referencias

Se revisaron el artículo y los ocho conjuntos de capturas desarrollados en [INSAIM: 10 best app UI/UX designs](https://www.insaim.design/blog/10-best-app-ui-ux-designs). Las decisiones siguientes son nuestra síntesis para el negocio inmobiliario; no son una receta literal del artículo.

| Referencia | Principio que tomamos | Aplicación en este prototipo | Qué evitamos trasladar |
|---|---|---|---|
| Airbnb | Contexto visual y recorrido claro | Fotografía y datos de la próxima visita; propiedad identificable en la campaña | Convertir la herramienta del agente en un portal para compradores |
| Spotify | Acceso personal a lo frecuente | Guardar herramientas favoritas, contador y filtro de selección | Recomendaciones infinitas o un tema oscuro impuesto a toda la app |
| Dropbox | Organización familiar | Nombres reconocibles, filas breves, formularios sencillos; Documentos como concepto | Carpetas y funciones de archivos que todavía no existen |
| Slack | Estructura y estados consistentes | Navegación estable, misma identidad del módulo en inicio y subpantalla, estados claros | Copiar canales, chats o barras laterales que el alcance no necesita |
| Headspace | Calma y un paso a la vez | Inicio sin saturación, formularios cortos, bloque opcional para concentrarse | Ilustraciones infantiles, gamificación o tono paternalista |
| Google Maps | Acción próxima siempre reconocible | Visita próxima, fecha/hora/lugar, detalles al tocar la cita | Mapas de relleno o navegación GPS que el prototipo no ofrece |
| Medium | Legibilidad y atención | Títulos directos, líneas cortas, cuerpo legible y jerarquía tipográfica contenida | Un diseño editorial que esconda las herramientas de trabajo |
| Pinterest | Reconocimiento visual y guardado | Fotografía de propiedad y acción explícita para guardar herramientas | Mosaico irregular en una interfaz donde el orden importa |
| Calm* | Reducir ruido | Superficies neutras, movimiento mínimo y color con función | Pantallas decorativas que demoren el trabajo |
| Notion* | Espacio modular personal | Elegir herramientas sin obligar a usar toda la plataforma | Un editor de bloques complejo para usuarios poco tecnológicos |

*Calm y Notion aparecen mencionados en la síntesis del artículo, sin el mismo desarrollo visual de los ocho casos principales. Se consideraron esos principios sin inventar un análisis de capturas que la página no proporciona.

**Regla:** combinar principios de experiencia, no mezclar diez identidades visuales. Un único sistema de tipografía, color, controles y espaciado gobierna todo.

## 3. Qué cambió respecto a la primera versión

- Se eliminó la barra lateral de escritorio. La navegación es horizontal y breve; en móvil permanece abajo.
- Se eliminaron las categorías en mayúsculas, las miniaturas de gráficos ornamentales y la paleta pastel diferente para cada módulo.
- El contenido ahora corresponde al trabajo inmobiliario: visitas, propiedades, campañas, propuestas y contratos.
- La próxima visita tiene información y fotografía útiles, no una tarjeta motivacional.
- Se redujo el texto promocional. Las pantallas se llaman Campañas y Tu agenda.
- Las seis herramientas conservan una posición y estructura predecibles.
- Campañas y Agenda tienen mayor énfasis porque son las dos herramientas implementadas. Las demás indican Ver concepto.
- El escritorio aprovecha dos columnas; el móvil conserva primero la próxima acción y luego las herramientas.

## 4. Instrucción lista para Claude Code

> Lee las instrucciones y arquitectura del repositorio antes de editar. Integra este sistema de diseño en el proyecto existente, conservando lógica, datos, permisos, autenticación e integraciones. No sustituyas el proyecto por un scaffold nuevo.
>
> Diseña y verifica primero a 390 px y después a 375 px. El usuario es un agente inmobiliario mexicano, puede tener 60 años y no estar familiarizado con la tecnología. Prioriza reconocimiento, legibilidad y acciones explícitas. No agregues jerga, pasos innecesarios ni controles diminutos.
>
> Aplica la síntesis de todas las referencias de la sección 2 bajo una sola identidad. No bases el producto únicamente en Airbnb ni copies el aspecto de cada aplicación. El objetivo es operar una inmobiliaria, no navegar anuncios como comprador.
>
> Construye tokens y componentes compartidos. Usa las primitivas accesibles que ya tenga el proyecto. Aplica la composición móvil de este documento y extiéndela a escritorio. No recuperes la barra lateral, los adornos o la paleta multicolor de la versión 1.
>
> Implementa o adapta Inicio, Campañas y Agenda. Conserva la marca real del proyecto. Las funciones no implementadas deben aparecer honestamente como conceptos o estados vacíos. No simules conexiones reales ni conviertas una acción del prototipo en gasto, envío o publicación real sin el flujo de autorización correspondiente.
>
> Cuando el sistema visual y el backend entren en conflicto, conserva los contratos funcionales y adapta el componente visual. Si la decisión afecta el significado del producto o los permisos, explícala en lugar de improvisarla.
>
> Antes de entregar, compila y verifica visualmente las tres rutas y sus diálogos en móvil y escritorio. Prueba teclado, foco, zoom 200%, movimiento reducido, nombres largos y estados vacíos. Reporta lo efectivamente probado. Corrige problemas concretos antes de declarar la integración terminada.

## 5. Paleta única

| Token | Color | Función |
|---|---|---|
| `--sky` | `#9FD8F5` | Contexto relevante y superficie de resultados |
| `--sky-soft` | `#E7F4FC` | Agenda, visita prioritaria y selección suave |
| `--sky-ink` | `#165474` | Texto sobre azul, iconos funcionales e interruptores activos |
| `--orange` | `#FF9257` | Acción principal y un acento de marca |
| `--orange-ink` | `#813B12` | Etiqueta temporal sobre superficie neutra |
| `--ink` | `#191C1F` | Texto, módulo Campañas y día seleccionado |
| `--white` | `#FFFFFF` | Fondo principal |
| `--surface` | `#F5F6F7` | Agrupaciones secundarias |
| `--muted-ink` | `#61666C` | Información secundaria |
| `--line` | `#E4E6E8` | Divisiones decorativas |
| `--control-border` | `#7C858D` | Límite visible de campos y controles |
| `--ring` | `#2675A3` | Foco de teclado |
| `--green` | `#246B48` | Estado activo, acompañado de texto |
| `--destructive` | `#B42318` | Error |
| Facebook | `#0866FF` | Logotipo oficial, sin recolorearlo a la marca propia |

Reglas de aplicación:

1. El blanco domina. El negro crea precisión. Azul y naranja orientan.
2. No asignar un color nuevo a cada herramienta.
3. Botón naranja con texto negro. Nunca texto blanco pequeño sobre naranja o azul cielo.
4. Sobre azul, texto azul oscuro. No gris lavado.
5. Campañas usa una tarjeta oscura para destacar la herramienta; esto no activa un tema oscuro global.
6. No degradados, brillos, glassmorphism ni halos decorativos.
7. Estados siempre con texto. Una etiqueta Activa no puede depender únicamente de un punto verde.
8. Tema claro deliberado. Un futuro tema oscuro requiere su propio diseño y validación.

```css
:root {
  color-scheme: light;
  --sky: #9FD8F5;
  --sky-soft: #E7F4FC;
  --sky-ink: #165474;
  --orange: #FF9257;
  --orange-ink: #813B12;
  --ink: #191C1F;
  --white: #FFFFFF;
  --surface: #F5F6F7;
  --muted-ink: #61666C;
  --line: #E4E6E8;
  --control-border: #7C858D;
  --ring: #2675A3;
  --green: #246B48;
  --destructive: #B42318;
  --radius-control: 12px;
  --radius-tile-mobile: 18px;
  --radius-tile-desktop: 22px;
  --radius-dialog: 24px;
  --shadow-hover: 0 10px 30px rgb(25 28 31 / 6%);
  --duration-feedback: 160ms;
  --duration-hover: 200ms;
  --ease: cubic-bezier(.16, 1, .3, 1);
}
```

Mapear estos valores a los tokens existentes. El color de acción y el de selección son conceptos distintos: no usar un único `primary` para convertir todos los controles en naranja.

## 6. Tipografía y lectura

Manrope autoalojada, pesos reales 400, 500, 600, 700 y 800. Licencia SIL OFL incluida. Usar rem y conservar el zoom.

| Uso | Móvil | Escritorio |
|---|---|---|
| Título de pantalla | 32 px / 2rem | 42 px; inicio amplio 48 px |
| Título de sección | 18 px | 20 px |
| Nombre de herramienta | 16 px | 18–19 px |
| Texto principal | 16 px | 16 px |
| Botón | 15–16 px | 15–16 px |
| Descripción breve | 14–15 px | 14–15 px |
| Metadato secundario | 12–13 px | 12–13 px |

Interlineado 1.5–1.7 para texto; 1.15–1.4 para títulos. Tracking de títulos no menor a −0.04em. Las métricas monetarias y horas usan números tabulares.

Para agentes de mayor edad: no hacer diminuto el texto para conservar una composición. Permitir dos líneas, ampliar la tarjeta o mover la acción. No confundir una interfaz limpia con falta de etiquetas.

## 7. Composición de las tres pantallas

### Inicio

Orden móvil:

1. Marca y avatar.
2. Saludo y fecha.
3. Próxima visita compacta: hora, propiedad, cliente, fotografía y acceso a Agenda.
4. Herramientas, Personalizar y filtro Todas/Favoritas.
5. Seis herramientas en dos columnas; cada tarjeta abre la herramienta o explica su concepto.
6. Navegación inferior estable.

En escritorio, las herramientas ocupan la columna principal y la visita aparece a la derecha con una fotografía más amplia. La cabecera contiene Inicio, Campañas y Agenda. No agregar un segundo sistema de navegación lateral.

### Campañas

- Una acción principal: Nueva campaña.
- Resultados expresados como personas interesadas, inversión y costo por contacto.
- Gráfico semanal con cantidades visibles; no depender de hover.
- Cada campaña se identifica por propiedad, operación y ubicación.
- Estado explícito con control Activar/Pausar.
- Exportar resultados es secundario.
- En móvil, resultados y propiedades se apilan. En escritorio se separan en dos columnas.

### Agenda

- Semana visible y día seleccionado inequívoco.
- Hora separada del contenido de cada cita.
- La visita destaca por contexto de propiedad, no por un borde de color arbitrario.
- Tocar la cita abre detalles con lugar, participantes, duración y zona horaria.
- Pendientes y reserva de tiempo después de las citas en móvil; columna lateral en escritorio.
- Nueva cita sigue siendo la acción principal de la pantalla.

## 8. Adaptación por ancho

| Ancho | Cabecera y navegación | Distribución |
|---|---|---|
| 320–479 px | Cabecera 74 px, navegación inferior | Una columna de secciones; herramientas en dos columnas; margen 24 px, 16 px bajo 360 |
| 480–767 px | Misma estructura móvil | Margen 32 px y más aire entre tarjetas |
| 768–1023 px | Cabecera 88 px, navegación horizontal | Herramientas y visita en columnas; margen 40 px |
| Desde 1024 px | Misma navegación horizontal | Margen 48 px y separación entre columnas de 60–72 px |
| Desde 1400 px | Contenido centrado | Máximo 1256 px; visita de 360 px |

La anchura es una condición de espacio, no una detección de modelo de dispositivo. Evitar reglas especiales para un teléfono concreto. La aplicación sigue siendo web responsive; no se entrega aquí una app nativa ni PWA instalable.

## 9. Componentes y estados

- **Navegación:** tres rutas y un acceso móvil a Herramientas. Etiqueta debajo del icono; `aria-current` en la ruta activa.
- **Tarjeta de herramienta:** icono, nombre, función y acción. Favorito es un botón hermano, nunca un botón anidado en un enlace.
- **Favorito:** área 44 × 44 px; nombre accesible; estado con `aria-pressed`.
- **Botón principal:** mínimo 50 px de alto, naranja, texto negro, radio 12 px.
- **Campo:** etiqueta permanente, altura mínima 52 px, fuente 16 px para evitar zoom automático de iOS.
- **Diálogo:** radio 24 px; foco contenido; cerrar y Escape; regreso de foco al disparador; scroll interno cuando haga falta.
- **Interruptor:** texto de acción, estado accesible y área expandida de toque.
- **Checkbox:** toda la fila sirve como objetivo de interacción.
- **Pestañas:** control accesible con selección y navegación por teclado.
- **Fotografía:** dimensiones reservadas, encuadre coherente y alternativa textual cuando aporte información. Sin imágenes de interfaz generadas como sustituto de controles reales.
- **Vacío:** explicación breve y salida útil; no una pantalla muerta.

En producción, añadir carga, error, reintento y prevención de envíos duplicados donde existan APIs. No simular retrasos artificiales para una preferencia local instantánea.

## 10. Movimiento y tacto

Feedback de 160–200 ms. Cambios sutiles de fondo, borde y sombra. No saltos de tarjetas, entradas repetidas, parallax ni animación ornamental infinita. Respetar `prefers-reduced-motion`.

Botones principales de 48–52 px; controles de icono al menos 44 px. Evitar depender de arrastrar, deslizar o mantener presionado. Respetar las zonas seguras y dejar espacio bajo el último elemento para la navegación fija.

## 11. Datos, permisos y alcance real

- Las selecciones de herramientas se conservan en `modo.modules.v1` en el dispositivo. Se mantienen los identificadores de la primera versión.
- Las campañas, citas y pendientes son demostraciones en memoria. Navegar o recargar puede restablecerlos.
- La fotografía es generada para una propiedad ficticia; no corresponde a un anuncio real.
- No hay conexión a Facebook, envío de mensajes, publicación de anuncios ni cargos.
- No hay backend, multiusuario o persistencia de negocio implementados en este prototipo visual.
- Fotografía, Documentos, Clientes y Automatizar son conceptos, no módulos completos.
- El proyecto receptor puede tener todas esas capacidades; conservar sus contratos al integrar la interfaz.

## 12. Integración y verificación

1. Leer instrucciones, rutas, componentes y estado actual del proyecto.
2. Mapear tokens del sistema, sin crear una segunda identidad paralela.
3. Adaptar shell móvil y navegación.
4. Construir componentes compartidos y sus estados.
5. Integrar las tres pantallas con datos reales solo donde haya contratos disponibles.
6. Validar primero móvil, después tablet y escritorio.
7. Probar búsqueda vacía, cero favoritas, nombres largos, formularios inválidos, interruptores, exportación, cambio de día y diálogos.
8. Revisar teclado, focus, zoom 200%, reducción de movimiento y contraste.
9. Evitar pérdida de datos real al cambiar de ruta; la persistencia temporal solo es aceptable en esta demostración explícita.
10. Compilar y comprobar que las tres rutas abren directamente.

**Comprobación de esta entrega:** compilación de las tres rutas y revisión TypeScript; revisión de recursos y tokens. Las capturas de las referencias sí se inspeccionaron. La interfaz construida no se ha sometido a pruebas visuales/interactivas de navegador en este entorno; no se declara perfección ni certificación de accesibilidad. WebMCP se conserva como mejora opcional detectada por capacidad, sin validación en un navegador compatible.

## 13. Fuentes de diseño

- Referencias proporcionadas por el usuario: [INSAIM](https://www.insaim.design/blog/10-best-app-ui-ux-designs).
- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): prioridades de interacción, touch y legibilidad. Se rechazó la sugerencia automática de landing inmobiliaria porque no corresponde a una herramienta operativa.
- [Impeccable](https://github.com/pbakaus/impeccable): modo Operate, jerarquía, coherencia y craft floor, subordinados a las decisiones expresas del usuario.
- [Manrope](https://fonts.google.com/specimen/Manrope), [Lucide](https://lucide.dev/) y [Simple Icons](https://github.com/simple-icons/simple-icons): tipografía e iconografía.

La consistencia final se evalúa por lo que el agente entiende y puede hacer. Si necesita adivinar una acción o descifrar una etiqueta, la interfaz todavía requiere trabajo.
