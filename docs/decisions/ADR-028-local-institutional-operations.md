# ADR-028: operación local verificable y puesta online separada

2026-10-28. Decisión: P11 trabaja sobre otra restauración de P10 en SQL Server 2019, con identidad, usuario, perfil, volumen e imagen propios. Las 185 tablas y diarios anteriores conservan su contrato; no se añade DDL de dominio. La cuenta de aplicación sigue sin autoridad sobre las 30 tablas académicas, DDL, respaldo, restauración ni administración de servidor.

El panel de operación es sólo lectura, exige `users.manage` y valida SQL nuevamente. Liveness, readiness, frescura por consumidor, conteos completos y recibos de restauración expresan señales diferentes. Un recibo HMAC acredita la declaración del operador ligada a su perfil/base/institución/release; se emite después del ensayo SQL+archivos, no sustituye ese ensayo ni revalida continuamente el archivo `.bak`.

P11 evalúa una vez la cadena completa de verificadores P5–P10 dentro de cada nueva transacción y conserva controles P3/P4 y la comprobación íntegra de modelo/identidad/ACL. No usa caché entre peticiones ni debilita TLS o locks. El proxy P11 dispone de 90 segundos para APIs que pueden encadenar varias transacciones acotadas. No se extiende esa configuración a perfiles previos.

Los recursos UI se ligan a ruta, CSRF, secuencia y ciclo de vida. Una respuesta tardía no puede reemplazar otra sección. Los errores al actualizar datos ya cargados se muestran conservando el borrador. Una credencial que aún se consulta no aparece como ausente. Comentarios utiliza el estado del módulo Inbox. Se preserva Glass y se usan sus tokens para la navegación clara/oscura.

El usuario confirmó que todavía no dispone de URL y solicitó una fase adicional. P12 agrupa servidor/dominio/HTTPS, proveedores, mapeos y aceptación institucional pendientes. No añade peso ni duplica hitos: permanecen 56 criterios y 279 hitos. El sprint local puede cerrarse al 100% de su alcance; la fase P11 original conserva sus puertas externas y su porcentaje parcial. Todas las copias, imágenes, perfiles, respaldos y evidencias anteriores se preservan. Retención local significa conservarlos; la política institucional definitiva queda pendiente.
