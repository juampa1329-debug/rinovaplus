# Clientes e Inbox persistentes en la copia SQL local

Fecha: 2026-10-15. Rama: `codex/integracion-coolify`. Alcance autorizado: persistencia local bajo [ADR-006](../decisions/ADR-006-local-crm-persistence.md), conservación del core y retirada de datos de demostración de la UI. Sin commit, push, despliegue externo ni envíos a proveedores.

## Resultado funcional

Clientes, conversaciones y mensajes locales se guardan en `crm.Contact`, `crm.Conversation`, `crm.Message` y `crm.Operation`. SQL es la fuente única; los UUID de contacto, conversación y mensaje son distintos. La API `/api/local/crm` confirma solo después del commit, aplica una revisión global, rechaza conflictos con 409 y conserva la identidad de operación al reintentar. La creación de contacto y conversación, el mensaje y su auditoría son transaccionales. No hay reset destructivo ni semillas en la UI activa.

La navegación conserva borradores; guardar o enviar limpia únicamente el texto confirmado por el servidor. Error o conflicto conserva la edición. Los catálogos de lectura proporcionan programas reales; no se inventan ofertas ni jornadas académicas. Formulario, revisión, tareas, comentarios sociales y análisis pendientes muestran su disponibilidad real. La apariencia V6, preferencias y configuración IA se conservan.

El endpoint legado `/api/local/clients` mantiene fixtures de compatibilidad separados. La UI utiliza exclusivamente `/api/local/crm`; esos fixtures no alimentan el modo SQL ni actúan como fallback. Los componentes históricos no montados y las pruebas conservan su contexto anterior; no representan capacidades activas.

## Evidencia comprobada

| Capa | Resultado y límite |
|---|---|
| Preparación y migración | Backup COPY_ONLY/CHECKSUM, restauración real y CHECKDB comprobados. Cuatro tablas creadas con contrato ADR-006-v1; ocho INSERT automáticos de auditoría DDL autorizados. Trigger conservado; restantes conteos y metadatos core preservados. [Informe](crm-local-migration.md). |
| Backend con SQL real | **46/46** comprobaciones HTTP/SQL: creación/edición, reintento sin duplicar, conflictos/concurrencia, rollback parcial, mensaje y persistencia desde nueva conexión y tras reinicio. Metadatos/conteos de las 722 tablas core y lector restringido preservados. |
| Suite backend | **1552 aprobadas y un fallo** de inventario de rutas, corregido para separar el namespace local. Después **306/306** en el archivo de contratos; no se presenta como otra suite completa. `pip check`, Ruff y exportación canónica correctos. |
| Frontend | Suite completa previa **152/152**. Cambio final de estado de error: **8/8** enfocadas, lint/tipos/build correctos. Corrección posterior de tres textos visibles: **22/22** existentes en 4,09 s, lint/tipos/build correctos; no se repitió la suite completa. |
| Docker funcional | **29 comprobaciones**, más **cuatro** de reinicio/preservación. Linux AMD64, UID 10001, un backend loopback, puerto 4173 limitado a 127.0.0.1, TLS estricto y catálogo real de 228 programas. Volumen IA idéntico; `.env` ausente de imagen y montajes. |
| Navegador | Creación con programa real, edición de ciudad, conflicto 409 entre pestañas con borrador conservado, mensaje local, recarga desde otra pestaña y navegación con borrador. Escritorio 1440 y móvil 390 × 844 sin desbordamiento horizontal; selección y regreso a bandeja correctos. Diez rutas sin datos de demostración visibles. |
| Lectura posterior independiente | HTTP y SQL desde nueva conexión coinciden: **dos contactos, dos conversaciones, dos mensajes, nueve operaciones confirmadas y revisión máxima 11**. Ciudad, programa y mensaje del recorrido presentes. Los conteos son evidencia del corte, no valores esperados para futuras operaciones. |

El primer ensayo real detectó una transacción anidada: pyodbc con `autocommit=False` ya mantiene la transacción; el `BEGIN` adicional permitía responder 201 sin persistir al cerrar. Se eliminó ese `BEGIN`. Un observador independiente confirmó la terminación de la transacción y las pruebas reales posteriores comprobaron durabilidad. Un error de reinicio del harness por disponibilidad del puerto se corrigió en el harness, sin modificar el producto.

## Certificado, configuración y conservación

El modo `local_sql_copy` valida DBSIIE, SQLEXPRESS, máquina esperada y huella del contrato; no ejecuta DDL al arrancar. El lector restringido existente sigue rechazando SA. Docker monta solo el certificado público y combina ese PEM con las CA del sistema en un archivo temporal de modo 0600. Conserva `Encrypt=Yes`, `TrustServerCertificate=No` y nombre TLS validado. El control negativo sin confianza adicional falla; con el PEM público pasa.

El proyecto Docker existente conserva el volumen `crm-cbn-integration-20261014_ai-state` y sus bytes. Credenciales privadas permanecen en el entorno de runtime, sin valores en artefactos, navegador o imagen. Outbound IA permanece desactivado. [Configuración y overlay](../configuration.md).

## Corrección final de texto y evidencia local

El navegador detectó dos referencias de texto heredadas en Ajustes. Se reemplazaron por «mensajes de prueba» y conexión/envío pendientes; se ajustó también «texto de prueba» en Asistente. El freeze de **97 archivos runtime** cambió únicamente en esos tres archivos frontend; backend idéntico. La imagen funcional anterior es evidencia anterior al copy, no la imagen final.

**Imagen final comprobada:** `sha256:579892fb17936bdc7a38fbdae0291371aead37fdc8809516697a0eb7bd2b7b43`, bundle Docker `index-CMY5gYy9.js`. Los tres textos nuevos están presentes y los anteriores ausentes. Se conservaron dos contactos, dos conversaciones, dos mensajes, revisión 11 y los valores comprobados; los bytes del volumen IA y el freeze de 97 archivos permanecieron idénticos. No se afirma comparación criptográfica SQL para esta última recreación. Evidencia PASS: `.local/sql-crm-runtime-20261015/docker-final-copy.json`. La primera aserción del harness esperaba incorrectamente el nombre del bundle Windows; se corrigió el harness sin cambiar el producto.

Evidencia local ignorada bajo `.local/sql-crm-runtime-20261015/`:

- `http-result.json`, `transaction-observer-diagnosis.json` y `backend-suite.log`.
- `frontend-suite.log`, `source-freeze-final.json` y `source-freeze-before-copy.json`.
- `docker-runtime-before-restart.json`, `docker-runtime-after-restart.json` y `docker-negative-tls.json`.
- `browser/inbox-desktop.jpg` y `browser/inbox-mobile.jpg`.

## Límites

La prueba acredita operación privada sobre la copia local, no producción ni SQL remoto. No hubo envíos Meta, solicitudes a proveedores IA, escrituras de negocio core, túneles, dominio público o despliegue Oracle. Auth/RBAC y aceptación compartida continúan pendientes. Solo Linux AMD64 está comprobado; ARM64 no. Readiness global mantiene 503: no equivale al estado de la conexión SQL local, comprobada mediante sus operaciones reales. Los respaldos y restauración se conservan; no se eliminaron datos confirmados para cerrar la prueba.
