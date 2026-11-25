# Informe de campañas: consulta agotada y revisión de diseño

Fecha: 25 de noviembre de 2026. Estado: corrección preparada; pull request, publicación y comprobación productiva pendientes.

## Causa comprobada

El informe de una campaña PRE-ICFES produjo HTTP 503. Coolify registró SQLSTATE `57014` y una consulta de unos ocho segundos (`statement_id=2a63e69f31ec`, `source=rows:40`). La huella coincide con la consulta paginada anterior de `Broadcasts.report`, calculada después de la traducción PostgreSQL. También se observaron esperas `55P03` al adquirir el bloqueo institucional de escritura. No es una prueba de falta de saldo, tokens ni fallo de SIIE.

La proyección anterior ejecutaba dos agregaciones correlacionadas de eventos por destinatario, con extracción repetida del JSON. La nueva proyección selecciona primero los destinatarios y cuentas de la campaña, extrae los eventos procesados por cuenta y agrega recibos y respuestas por destinatario. En PostgreSQL se materializan explícitamente las proyecciones compartidas para evitar que el optimizador vuelva a evaluar el JSON en cada unión.

Se conservan filtros, páginas de cien, CSV completo, gráficos y fechas observadas. Una respuesta sigue exigiendo `context.id` exacto y autor/cuenta/institución coincidentes. La aceptación no se convierte en entrega o lectura. No cambian envíos, reintentos, cuotas, bloqueos ni los tiempos de seguridad de la base de datos. El error clasificado de almacenamiento ahora explica la consulta fallida sin presentarla como un fallo de acceso.

## Validación local

- 220 pruebas backend focalizadas de campañas pasan. Los datos SQL sintéticos comprueban aislamiento, recibos, respuestas, filtros, páginas, gráficos y CSV mediante el servicio real.
- La regresión con cien destinatarios y seiscientos eventos comprueba que las lecturas JSON no crezcan como destinatarios por eventos. Las variantes SQL se traducen y analizan con `pglast`; SQLite ejecuta las uniones con funciones escalares equivalentes. Esto no sustituye la medición de PostgreSQL productivo.
- 38 pruebas frontend de campañas, transporte y coordinación de lecturas pasan; tipos, ESLint acotado, Ruff y compilación institucional pasan. Permanece la advertencia histórica de tamaño de bundle.
- La selección amplia frontend obtuvo 83 aprobadas y dos fallos de `institutionWorkspace.test.tsx`. Ambos se reprodujeron con el archivo API de `HEAD` anterior: expectativa de «saldo insuficiente» en el modal y expectativa antigua de error de acceso al conservar borradores. No se modificaron esas pruebas para ocultarlos ni se declara la suite completa verde.

## Pendientes de publicación

Abrir/revisar el pull request contra `deploy/coolify-rinovaplus`, integrar sin perder cambios concurrentes, comprobar backend/frontend en Coolify y abrir el informe, sus filtros y gráficos de forma nativa. Revisar los procesos y la muestra posterior de logs. No atribuir al arreglo una garantía de SLA o ausencia perpetua de errores.

El diseño del colaborador está en `Feature/nuevos-logos`, commit `1b6653a`. Se revisa por separado antes de integrarlo; este arreglo no sustituye producción por `main` ni por una copia antigua de esa rama.

## Firma SIIE

Se generó un secreto dedicado y se entregó al titular en un archivo privado fuera del repositorio. Su valor no se incluye en código, evidencia ni Markdown. El mismo texto debe guardarse en la configuración privada del emisor SIIE y en `SIIE_WEBHOOK_SECRET` Runtime del backend; el guardado en Coolify y la activación del receptor siguen pendientes. El [contrato único](SIIE_WEBHOOK_CONTRACT_V1.md) explica ambas opciones de almacenamiento y el cálculo HMAC. Se conserva la API key existente y P23 sigue sin nuevas aceptaciones.
