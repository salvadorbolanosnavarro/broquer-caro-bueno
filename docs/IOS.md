# Broquer para iOS

Proyecto Capacitor 8 con código visual compartido y recursos locales. `mobile/main.tsx` selecciona las mismas pantallas React utilizadas en la web. No usa server.url ni carga una web remota como pantalla de inicio. El catálogo de módulos se incluye en el bundle, por lo que explorar la demo no depende del servidor web.

## Estado real

Se generó el proyecto Xcode con Swift Package Manager y se comprobó la compilación del bundle móvil en Linux. No se ejecutó Xcode ni Codemagic: no se afirma que exista IPA validada. La app actual permite explorar las pantallas demo; autenticación nativa, Keychain, deep links, APNs y RevenueCat siguen pendientes de implementación. No contiene secretos ni pagos externos. Ícono y marca son provisionales hasta integrar los logotipos oficiales.

## Flujos Codemagic

- `ios-simulador`: instala desde lockfile, compila React, sincroniza Capacitor, revisa TypeScript y compila la app para simulador sin certificados.
- `ios-firmada`: mismo bundle, aplica perfiles configurados en Codemagic y genera archivo e IPA. No publica automáticamente a TestFlight o App Store.

El identificador provisional es `app.broquer.mobile`. Confirmarlo antes de la primera publicación y mantenerlo igual en capacitor.config.ts, proyecto Xcode, codemagic.yaml y App Store Connect. El repositorio de Sites no otorga por sí solo acceso a Codemagic: al configurar, se necesitará conectar una copia del mismo código en un proveedor Git compatible.

## Configuración manual, al final

1. Conectar ese repositorio a Codemagic y ejecutar ios-simulador.
2. Confirmar identificador, equipo Apple Developer y registro de app.
3. Cargar certificados y perfiles de distribución en Codemagic; ejecutar ios-firmada.
4. Configurar dominios/deep links, APNs y servicios reales cuando estén implementados.
5. Validar en un iPhone: sesión, cierre y borrado de caché, teclado, safe areas, enlaces, permisos, accesibilidad y regreso del segundo plano. Completar privacidad, eliminación de cuenta y metadatos antes de revisión de Apple.

Comandos locales: `pnpm mobile:build`, `pnpm mobile:sync`, `pnpm mobile:open` (el último requiere macOS/Xcode).

Referencias: https://capacitorjs.com/docs/ios y https://docs.codemagic.io/yaml-quick-start/building-an-ionic-app/.
