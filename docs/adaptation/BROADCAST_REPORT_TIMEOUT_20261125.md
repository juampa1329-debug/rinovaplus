# Informe de campañas: consulta agotada y revisión de diseño

Fecha: 25 de noviembre de 2026. Estado: corrección urgente `3a238a8` publicada y comprobada nativamente. Los cambios de diseño se revisaron por separado y se integraron mediante el [pull request #1](https://github.com/juampa1329-debug/rinovaplus/pull/1).

## Causa comprobada

El informe de una campaña PRE-ICFES produjo HTTP 503. Coolify registró SQLSTATE `57014` y una consulta de unos ocho segundos (`statement_id=2a63e69f31ec`, `source=rows:40`). La huella coincide con la consulta paginada anterior de `Broadcasts.report`, calculada después de la traducción PostgreSQL. También se observaron esperas `55P03` al adquirir el bloqueo institucional de escritura. No es una prueba de falta de saldo, tokens ni fallo de SIIE.

La proyección anterior ejecutaba dos agregaciones correlacionadas de eventos por destinatario, con extracción repetida del JSON. La nueva proyección selecciona primero los destinatarios y cuentas de la campaña, extrae los eventos procesados por cuenta y agrega recibos y respuestas por destinatario. En PostgreSQL se materializan explícitamente las proyecciones compartidas para evitar que el optimizador vuelva a evaluar el JSON en cada unión.

Se conservan filtros, páginas de cien, CSV completo, gráficos y fechas observadas. Una respuesta sigue exigiendo `context.id` exacto y autor/cuenta/institución coincidentes. La aceptación no se convierte en entrega o lectura. No cambian envíos, reintentos, cuotas, bloqueos ni los tiempos de seguridad de la base de datos. El error clasificado de almacenamiento ahora explica la consulta fallida sin presentarla como un fallo de acceso.

## Validación local

- 220 pruebas backend focalizadas de campañas pasan. Los datos SQL sintéticos comprueban aislamiento, recibos, respuestas, filtros, páginas, gráficos y CSV mediante el servicio real.
- La regresión con cien destinatarios y seiscientos eventos comprueba que las lecturas JSON no crezcan como destinatarios por eventos. Las variantes SQL se traducen y analizan con `pglast`; SQLite ejecuta las uniones con funciones escalares equivalentes. Esto no sustituye la medición de PostgreSQL productivo.
- 38 pruebas frontend de campañas, transporte y coordinación de lecturas pasan; tipos, ESLint acotado, Ruff y compilación institucional pasan. Permanece la advertencia histórica de tamaño de bundle.
- La selección amplia frontend obtuvo 83 aprobadas y dos fallos de `institutionWorkspace.test.tsx`. Ambos se reprodujeron con el archivo API de `HEAD` anterior: expectativa de «saldo insuficiente» en el modal y expectativa antigua de error de acceso al conservar borradores. No se modificaron esas pruebas para ocultarlos ni se declara la suite completa verde.

## Publicación y comprobación real

Backend `fqjn8amupeyndfepgnumulut` Success/Running, 4m19s. Después del guardado del secreto por el titular, su redeploy `qfxumzfcnwhmjsgziiwq7fg4` quedó en cola y completó Success en 6m02s, incluyendo espera. Frontend inicial `3a238a8` Success44s; frontend del diseño `60dceb6`, despliegue `yf0ecqdevkoecjnfsthmzfeu`, Success44s.

El informe PRE-ICFES cargó cien filas sin alertas. El filtro Entregado mostró 67; al quitarlo volvió a cien. Los gráficos mostraron 100 destinatarios, 90 entregas observadas, 23 lecturas, 38 respuestas atribuidas y ocho fallidos. Son resultados existentes de la campaña; no se reintentaron ni se enviaron mensajes para esta comprobación. La consulta agregada nueva tiene huella `a83fe065b4da` y se observó con 419–435ms de ejecución SQL y 1,276–1,321ms de transacción en la muestra. La consulta paginada nueva tiene otra huella; no se presenta ese tiempo como medición de toda la pantalla ni como SLA.

Los nueve procesos estaban Al día a las 17:14:11 de Bogotá. La muestra conserva esperas `55P03` y otra consulta del listado de Inbox (`e7639d094565`, `listing:901`) de 4,3–4,6 segundos. No se atribuye esa consulta al informe ni se declara resuelta la contención completa. Evidencia agregada: `artifacts/live/broadcast-report-branding-webhook-20261125.json`.

El diseño del colaborador procede de `Feature/nuevos-logos`, commit `1b6653a`; se aplicó sobre producción actual, se corrigió y probó antes del PR. No se sustituyó producción por `main` ni por una copia antigua de esa rama.

## Firma SIIE

Se generó un secreto dedicado y se entregó al titular en un archivo privado fuera del repositorio. Su valor no se incluye en código, evidencia ni Markdown. El titular lo guardó en Coolify y desplegó. El panel confirmó el secreto configurado. Tras autorización puntual, se habilitó la recepción firmada, con Calificación y envíos finales desactivados; se confirmó al recargar. Continúa sin eventos verificados en este corte. El emisor debe usar el mismo texto y enviar o reintentar su primer evento firmado. El [contrato único](SIIE_WEBHOOK_CONTRACT_V1.md) explica dónde guardarlo y el HMAC. Se conserva la API key existente; P23 sigue 0/9, con piloto real y volante/PDF pendientes.
