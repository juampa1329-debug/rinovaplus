# Revisión de logos y acceso institucional

25 de noviembre de 2026. Cambio del colaborador: `Feature/nuevos-logos`, commit `1b6653a`. Se aplicó sobre la rama actual de producción con la corrección del informe `3a238a8`, mediante cherry-pick `53912f1`; no se sustituyó producción por `main` ni se retiraron funciones posteriores.

Estado: [pull request #1](https://github.com/juampa1329-debug/rinovaplus/pull/1) creado, revisado e integrado sin conflictos en `60dceb6`. El frontend de Coolify `yf0ecqdevkoecjnfsthmzfeu` terminó Success/Running en 44 segundos. El backend conserva `3a238a8`, pues el diseño no cambia su código ni su Dockerfile de producción. El PR no registró comprobaciones CI; la evidencia aprobada es local y la comprobación nativa posterior.

## Alcance y ajustes

Logo y favicons renovados, acceso claro/oscuro/sistema, animación con pausa y adaptación móvil. Los Dockerfiles que compilan frontend incluyen los recursos públicos; Coolify mantiene su Dockerfile de backend sin cambios de diseño. Se comprobaron los archivos gráficos estáticos, la compilación institucional y la carga del logo.

La revisión detectó un error de ESLint por restablecer la visibilidad de contraseña desde un efecto. El restablecimiento ahora ocurre al cambiar de modo, recibir un desafío MFA o completar el acceso. La animación comprueba las APIs disponibles para evitar excepciones en entornos sin `matchMedia` o control SMIL. Los contratos de login, MFA, recuperación y activación conservan sus rutas y datos.

Las pruebas de marca se actualizan al texto del nuevo diseño. La comprobación de limpieza del token en el enlace de activación espera el efecto que modifica la URL, en lugar de asumir que ya ocurrió al aparecer el encabezado.

## Comprobaciones

- 62 pruebas frontend focalizadas de acceso, MFA, recuperación/activación, visibilidad de contraseña, temas, pausa, movimiento reducido, pantalla compacta, correo, campañas y coordinación de lecturas pasan. Incluyen las 38 ya usadas en el arreglo del informe; no son cantidades disjuntas.
- Tipos y ESLint acotado pasan. Compilación con `vite.workspace.config.ts` aprobada; se conserva la advertencia histórica de tamaño del bundle.
- Vista nativa local del build real a 1280×720 y 390×844: login, recuperación y temas visibles; sin desbordamiento horizontal. Logo cargado, campos obligatorios y autocompletado conservados. La vista usó un servidor local de sólo lectura con estado de sesión sintético, sin credenciales reales ni escrituras; se cerró al terminar y se restableció el viewport.
- No se ejecutó aquí la suite frontend completa. Los dos fallos heredados de Inbox se documentan en [la incidencia del informe](BROADCAST_REPORT_TIMEOUT_20261125.md), sin ocultarlos ni modificar sus expectativas.

Comprobación productiva: sesión institucional conservada al recargar, formulario público de activación visible con sus campos obligatorios, logo cargado y sin desbordamiento horizontal. No se introdujeron credenciales ni se creó/cambió una cuenta en esa comprobación. El informe de campañas, sus cien filas, filtros y gráficos también funcionó con los recursos publicados. Evidencia agregada: `artifacts/live/broadcast-report-branding-webhook-20261125.json`.

No hay nuevas aceptaciones de fases, mensajes, campañas, cambios de modelos, escrituras SIIE, DDL ni servicios productivos nuevos.
