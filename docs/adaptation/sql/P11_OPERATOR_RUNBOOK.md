# Operación local CRM CBN

Alcance: Docker local, SQL Server 2019 (motor 15, compatibilidad 150), perfil P11 cerrado. No acredita puesta online, mapeo completo DBSIIE, RPO/RTO institucionales ni aprobación de producción. El operador humano de esta copia es el propietario del equipo; las credenciales de administración SQL se mantienen en el montaje privado del helper y nunca se entregan al runtime.

## Acceso y supervisión

La aplicación acumulada usa `http://127.0.0.1:4178`. El perfil humano propietario y su contraseña se conservan privadamente en `.local/p11-es/ACCESS.txt`; no copiar a documentación, logs o tickets. El perfil SQL se monta sólo en lectura, con TLS y comprobación de CA y nombre. La aplicación se ejecuta como UID 10001, raíz de sólo lectura, sin capacidades Linux, con volumen de archivos propio.

En Ajustes → Operación, propietario/administrador con `users.manage` consulta SQL, frescura de los ocho consumidores, totales completos de colas y último respaldo con restauración comprobada. El panel no acepta escrituras. Canales puede administrarse con el módulo de procesamiento pausado; la pausa sigue bloqueando efectos. Inbox deshabilitado bloquea también Comentarios.

`GET /health/live` confirma únicamente que HTTP responde. `GET /health/ready` exige una nueva validación íntegra de SQL y comprobaciones recientes y sin fallos de todos los consumidores; devuelve 503 si alguna falla. No devuelve nombres de servidor, usuarios SQL ni errores internos. El healthcheck Docker usa readiness cada 45 segundos, con 90 segundos iniciales y tres fallos antes de marcar unhealthy. No activa productores ni repara drift.

Las etapas se marcan correctas sólo cuando el consumidor termina, incluso si no había trabajo. A los 180 segundos sin éxito pasan a vencidas. Un fallo de campañas no queda oculto por otro consumidor. Esto observa comprobaciones; no promete entrega de mensajes ni aceptación de proveedores.

P11 ejecuta una vez la cadena completa de verificadores P5–P10 dentro de cada transacción nueva, conservando además los controles P3/P4, modelo, identidad, TLS y permisos. No hay caché de validaciones entre peticiones. El proxy propio admite 90 segundos para APIs generales, que pueden encadenar varias transacciones con esperas acotadas; los límites SQL y los locks conservan sus valores. Este ajuste no constituye una garantía de rendimiento institucional.

## Fallos y continuidad

1. Revisar el estado y los códigos de error sanitizados del contenedor. Un 503 de almacenamiento/auditoría conserva el cierre de seguridad; no desactivar TLS, locks, validaciones ni permisos para recuperarlo.
2. Comprobar disponibilidad Docker/SQL, espacio y certificados. Un fallo de esquema, diario, ACL, identidad o contexto requiere intervención del operador; no existe caché que permita seguir con una validación antigua.
3. Pausar la cuenta/campaña/flujo afectados. No reenviar una operación incierta. Revisar aceptación, recibos, intento y epoch antes de autorizar cualquier nuevo efecto.
4. Reiniciar sólo el contenedor P11 si procede. Readiness y recorrido funcional deben volver a pasar; liveness aislado no basta.
5. Registrar incidente, hora, ámbito, evidencia y decisión. Los logs excluyen cuerpos, query strings, contraseñas, tokens y errores SQL completos.

## Respaldo y recuperación

Un respaldo SQL no contiene archivos privados ni claves. El conjunto recuperable incluye: backup nativo COPY_ONLY/CHECKSUM/VERIFYONLY; perfil cifrado y su clave de custodia por mecanismo privado; las versiones cifradas en SQL; todos los blobs UUID referenciados por SQL; receta e imagen fijadas; diarios y recibos. Los archivos se verifican por hash y por los mismos lectores SQL que utiliza la aplicación.

El ejecutor autorizado está en `backend/tools/qualify_p11_recovery.py`. Opera únicamente sobre perfiles propios emitidos por `prepare_p11_operations.py`, exige una etiqueta nueva, restaura a otra base P11 y no sobrescribe ninguna existente. Para repetir el procedimiento local, el operador detiene temporalmente sólo el preview P11, captura sus archivos actuales en una raíz privada nueva y llama `recover(source_label='final', label='<etiqueta-nueva>', media_root='<raíz-privada>')` dentro del helper desde `/tmp/p2-code/backend`. Los parámetros deben provenir del inventario privado y revisarse antes de ejecutarlos. No reejecutar etiquetas pobladas ni calificadores sobre el preview.

La restauración compara las 185 tablas antes de invalidar autoridad copiada, ejecuta CHECKDB, autentica todas las versiones de secretos y verifica los blobs. Después revoca sesiones, desafíos y OAuth copiados; pausa modelos, cuentas, campañas y flujos; cancela trabajo no iniciado y conserva trabajo incierto. Una comprobación adicional verifica 171 tablas estables, incluidas las 30 académicas; las restantes contienen las pausas y revocaciones intencionales. Nunca se reanudan efectos externos automáticamente.

Sólo al superar la recuperación se emite un recibo HMAC con propósito separado, ligado a base/institución/principal/perfil/release y backup UUID. Otra identidad restaurada no puede reutilizar ese recibo. La aplicación lee una copia de ese recibo en `operations/latest-receipt.json`, en su propio volumen; no lee la credencial del operador ni puede ejecutar el respaldo. Recibos ausentes, alterados, futuros o con más de 24 horas se distinguen de los válidos. El umbral es una alerta local, no un RPO institucional aprobado.

## Retención y autoridad

Se conservan todas las bases, imágenes, perfiles, volúmenes, respaldos y evidencias anteriores por instrucción humana. No hay borrado automático ni tarea programada creada. El operador debe inventariar espacio y evidencias verificadas; cualquier futura eliminación exige ámbito y política institucional explícitos. No eliminar el último respaldo restaurado comprobado, claves necesarias, evidencias inmutables ni efectos inciertos. La periodicidad, custodios suplentes, almacenamiento fuera del equipo, RPO/RTO y retención definitivos quedan en P12.

Administración usa cuentas humanas individuales, roles, confirmación reciente para acciones sensibles y MFA disponible. No compartir la cuenta SQL del runtime para administración. La cuenta de despliegue tiene privilegios separados y no está disponible en la API. Cambiar contraseñas/custodia exige verificar antes qué secretos y perfiles dependen de la clave; no rotar ciegamente la clave de cifrado que protege versiones históricas.

## Reversión

Conservar primero P11, su base, perfil, volumen y evidencia. Detener su contenedor en 4178, preservar su nombre y arrancar únicamente el P10 retenido (`crm-cbn-preview-p10-preserved`) en ese puerto. No arrancar ambos a la vez ni mezclar colas. No se degrada la base P11 ni se borran modelos o diarios. Volver a P11 requiere detener de nuevo P10, conservar ambas identidades y comprobar readiness, blobs y configuración. El ensayo de reversión debe guardar recibos de ambos lados y dejar finalmente P11 como aplicación principal.

## Entrega online

P12 requiere servidor, DNS/HTTPS, SQL/mapeos completos, proxy/orígenes/cookies seguras, apps de proveedor, custodios, política operativa y aprobación humana de la puesta en servicio. Los dominios `.example`, secretos de fixture y datos sintéticos nunca se convierten en credenciales ni evidencia de producción.
