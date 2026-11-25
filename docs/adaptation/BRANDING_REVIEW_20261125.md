# Revisión de logos y acceso institucional

25 de noviembre de 2026. Cambio del colaborador: `Feature/nuevos-logos`, commit `1b6653a`. Se aplicó sobre la rama actual de producción con la corrección del informe `3a238a8`, mediante cherry-pick `53912f1`; no se sustituyó producción por `main` ni se retiraron funciones posteriores.

Estado: revisión local completada, rama preparada para pull request. Diseño todavía no publicado. La sesión GitHub del navegador requiere autenticación del titular para crear el PR.

## Alcance y ajustes

Logo y favicons renovados, acceso claro/oscuro/sistema, animación con pausa y adaptación móvil. Los Dockerfiles que compilan frontend incluyen los recursos públicos; Coolify mantiene su Dockerfile de backend sin cambios de diseño. Se comprobaron los archivos gráficos estáticos, la compilación institucional y la carga del logo.

La revisión detectó un error de ESLint por restablecer la visibilidad de contraseña desde un efecto. El restablecimiento ahora ocurre al cambiar de modo, recibir un desafío MFA o completar el acceso. La animación comprueba las APIs disponibles para evitar excepciones en entornos sin `matchMedia` o control SMIL. Los contratos de login, MFA, recuperación y activación conservan sus rutas y datos.

Las pruebas de marca se actualizan al texto del nuevo diseño. La comprobación de limpieza del token en el enlace de activación espera el efecto que modifica la URL, en lugar de asumir que ya ocurrió al aparecer el encabezado.

## Comprobaciones

- 62 pruebas frontend focalizadas de acceso, MFA, recuperación/activación, visibilidad de contraseña, temas, pausa, movimiento reducido, pantalla compacta, correo, campañas y coordinación de lecturas pasan. Incluyen las 38 ya usadas en el arreglo del informe; no son cantidades disjuntas.
- Tipos y ESLint acotado pasan. Compilación con `vite.workspace.config.ts` aprobada; se conserva la advertencia histórica de tamaño del bundle.
- Vista nativa local del build real a 1280×720 y 390×844: login, recuperación y temas visibles; sin desbordamiento horizontal. Logo cargado, campos obligatorios y autocompletado conservados. La vista usó un servidor local de sólo lectura con estado de sesión sintético, sin credenciales reales ni escrituras; se cerró al terminar y se restableció el viewport.
- No se ejecutó aquí la suite frontend completa. Los dos fallos heredados de Inbox se documentan en [la incidencia del informe](BROADCAST_REPORT_TIMEOUT_20261125.md), sin ocultarlos ni modificar sus expectativas.

Antes de integrar: crear el pull request contra `deploy/coolify-rinovaplus`, comprobar que no hayan entrado cambios concurrentes y completar la revisión. Después, verificar Coolify y el acceso publicado. No hay nuevas aceptaciones de fases, mensajes, campañas, cambios de modelos, escrituras SIIE, DDL ni servicios productivos nuevos.
