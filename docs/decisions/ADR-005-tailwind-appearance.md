# ADR-005 — Tailwind y apariencia del diseño local

**Fecha:** 2026-10-14, America/Bogota. **Estado:** aceptado para tecnología y alcance local por instrucción explícita del propietario; resultado visual pendiente de revisión humana.

## Decisión y autorización

El propietario solicitó usar «talwin para los estilos y animaciones», aplicar las skills de diseño registradas y habilitar modo claro y oscuro. Se interpreta la tecnología nombrada como Tailwind CSS. La instrucción autoriza incorporarlo y refinar el prototipo existente, sin ampliar capacidades de negocio.

Tailwind CSS **4.3.3** y **@tailwindcss/vite 4.3.3** quedan fijados en manifiesto y lockfile. Se conservan React y Vite. Se importan tema y utilidades sin Preflight para preservar controles y contratos CSS. Los tokens semánticos compartidos alimentan utilidades y componentes; no se añade biblioteca de componentes, animación, fuentes ni iconos externos.

## Apariencia y movimiento

- Identidad textual CRM CBN, acento verde institucional y español neutral de preview conservados.
- Navegación clara integrada y superficies oscuras diferenciadas; filas, jerarquía e iconos SVG consistentes.
- Selector visible Claro/Oscuro/Sistema. Sistema sigue el navegador; elección guardada exclusivamente en `localStorage` bajo `crm-cbn-appearance`. Con storage bloqueado funciona durante la pestaña. Ningún cliente, mensaje o borrador se persiste.
- Bootstrap en el encabezado aplica apariencia antes de React para evitar el fondo inicial incorrecto; colores nativos y meta theme-color acompañan el tema.
- Transiciones de 150–160 ms y feedback de pulsación; sin coreografía inicial ni movimiento de datos. Movimiento reducido y hover limitado a puntero fino.

## Alternativa y tradeoff

CSS exclusivamente manual evitaría una dependencia de build, pero no cumpliría la tecnología solicitada. Un kit completo introduciría mayor superficie de regresión. La adopción incremental usa Tailwind en shell, navegación, botones y componentes compartidos, conservando CSS específico del layout. Tailwind no añade runtime de animación. Requiere navegadores modernos; compatibilidad histórica queda fuera de este corte local.

## Verificación, reversión y límites

Normalización y `npm run check` aprobados: formato, lint, tipos, **64 tests en 7 archivos** y build. Las cuatro pruebas nuevas comprueban preferencia inválida/sistema, persistencia/remount, cambios OS con override manual y storage denegado. La prueba de shell existente adapta solo el nombre del nuevo control Oscuro. Detector Impeccable una vez: `[]`, exit 0. Navegador IAB comprobado por el coordinador en escritorio 1440×960, tablet emulada 768×1024 y móvil emulado 390×844: temas, persistencia al recargar, teclado/foco, navegación móvil, Inbox, Clientes, Ajustes y validación de formulario. Sin overflow horizontal en las vistas medidas ni corrección de código necesaria. Seis capturas locales y 38/38 hashes frontend intactos; detalle en [avance A-018](../progress.md). Aceptación visual humana pendiente; no teléfono físico, producción o certificación de accesibilidad.

Reversión: restaurar el conjunto frontend de esta unidad y retirar las dos dependencias del manifiesto/lock; limpiar opcionalmente solo `crm-cbn-appearance`. Sin migración ni dato remoto. No DB, API, backend, autenticación, modelo, envío, Git/publicación o despliegue. P-003/P-015 conservan aprobación visual definitiva pendiente.

Referencias: [Vite](https://tailwindcss.com/docs/installation/using-vite), [omisión de Preflight](https://tailwindcss.com/docs/preflight), [modo oscuro](https://tailwindcss.com/docs/dark-mode).
