# P11 · Operación de RinovaPlus en PostgreSQL

Corte de revisión: 18 de noviembre de 2026. El propietario confirmó «Aceptar PostgreSQL actual como entorno definitivo». Este documento prepara la aceptación de P11/P12 en ese alcance; conserva la exigencia y evidencia histórica SQL Server 2019 sin atribuirle pruebas nuevas ni modificar releases/checkers/grafos o el denominador original. La aceptación final de puesta en servicio se registra por separado después de las pruebas desplegadas.

## Entorno y responsabilidades

Aplicación pública: https://app.rinovaplus.com. Coolify: https://coolify.rinovaplus.com. Recursos existentes: backend RinovaPlus, RinovaPlus Frontend y RinovaPlus PostgreSQL 16.16. Base activa `rinovaplus`, 155 tablas CRM mapeadas y dos de migración. SIIE académico permanece separado y diferido en P16. El runtime usa `rinovaplus_app` sin superusuario, CREATE DATABASE ni CREATE ROLE; el recurso PostgreSQL no publica un puerto externo. El custodio de la instancia y de las claves debe ser el propietario/operador autorizado de CBN; no compartir contraseñas o claves por chat ni guardarlas en Git.

Las colas de este recorrido se ejecutan en PostgreSQL con las rutinas de reserva y los ocho consumidores existentes. No se utiliza Redis. No se añade un segundo dispatcher ni un productor legado. Instalar Redis por sí solo no cambiaría este contrato. Las cuentas de acceso humanas se administran en Ajustes → Usuarios y Roles y permisos, por separado de los agentes IA.

## Comprobaciones realizadas

- Usuario de prueba autorizado `p11-supervision@example.invalid`, rol Consulta, sin contraseña: creado y desactivado sin activar ni transmitir el código. Cero sesiones abiertas. La comprobación final muestra Active=0, AuthVersion=2 y cero desafíos elegibles. El registro de invitación anterior se conserva hasta vencer, pero no conserva una autorización vigente. Verificar también la versión al reconciliar, no sólo ConsumedAt.
- Respaldo MVCC exportado y manifiesto desde la misma instantánea: restaurado con `pg_restore --exit-on-error` en `rinovaplus_p11_restore_20261118_b`. Coinciden conteos y huellas de las 157 tablas. SHA-256 del dump: `f26e643af65dbda097776160d24def9e84564d3ddd995576763d6dc27e14c730`. SHA-256 del manifiesto: `464964b97d9553af39f503d4b206c767967a513c9482a73aa93f9a9d7cd61cc7`. El manifiesto usa conteo y MD5 del contenido JSON ordenado de cada tabla; no se presenta como un control criptográfico contra manipulación intencional. El dump completo tiene SHA-256.
- La copia restaurada no admite CONNECT del rol runtime. No se cambió la base activa ni se arrancaron workers sobre la copia. Los datos y las claves cifradas no se publicaron en el repositorio.
- Los 19 archivos de Inbox fueron archivados, extraídos en otra raíz privada y comparados por nombre, tamaño y SHA-256. Se autenticaron 1 versión de secreto Access y 76 versiones C10; cero Ads. No se imprimieron los valores ni se rotó la clave.
- El primer script de ensayo perdió las barras de comandos psql al transmitirse y falló antes de generar el dump y crear la base. Se conservó el directorio fallido `p11-ops-20261118-a`; el ensayo corregido utiliza `...-b`, String.raw y ON_ERROR_STOP en la llamada. No se cuenta el intento fallido como restauración.
- Las pruebas locales seleccionadas pasan: 117 backend, 16 frontend, tipos, lint de archivos modificados y build workspace. La advertencia previa de bundle grande permanece. No equivalen a auditoría externa ni a replay integral SQL histórico; veinte archivos históricos siguen ausentes.

## Copias y supervisión

Coolify tiene una programación para la base `rinovaplus` a las **03:00 de Bogotá** (`0 8 * * *`, zona UTC), y otra para el volumen `nwbyrdvtsfclmm6zyffjqjqp-rinovaplus-data` a las **03:05 de Bogotá** (`5 8 * * *`, UTC). Ambas conservan copias sin borrado automático y tienen aviso de copia faltante configurado a dos días. Las ejecuciones manuales iniciales de Coolify terminaron en Success: base 2,14 MB y volumen 6,02 MB. El aviso configurado no acredita una entrega por correo; el destino y preferencias se desarrollarán en P15.

Las copias actuales son locales al servidor. No hay un destino S3 externo validado. No cubren por sí solas la pérdida completa del servidor ni la pérdida de CRM_SECURITY_KEY. Las dos agendas son independientes, no una copia atómica DB+volumen; antes de recuperar hay que conciliar sus fechas y todos los archivos referenciados. El archivo de volumen se crea manteniendo la aplicación en ejecución; una recuperación no se declara válida por el mero éxito de ese trabajo. Conservar espacio suficiente y revisar crecimiento porque la retención no elimina copias.

Ajustes → Operación muestra motor/version reales, ocho etapas, conteos globales, URL configurada y un recibo fechado de restauración. El recibo PostgreSQL está ligado por HMAC a base, institución, principal y perfil. Es inválido si no coincide, fue alterado o es futuro; después de 24 horas muestra que requiere actualización. No re-hashea continuamente archivos ni sustituye un nuevo ensayo. Su firma se emite sólo tras el ensayo verificado, sin API de backup/restore ni cambios de permisos del runtime.

## Recuperación real: procedimiento para el custodio

1. Identificar la incidencia y conservar logs, colas, recibos y secretos cifrados. Anotar imagen/commit activos y las copias exactas. No escoger una base por nombre o fecha parecidos ni borrar copias anteriores.
2. Detener escrituras/productores CRM bajo control del operador antes de promover una restauración. Conservar los eventos que entregue el proveedor. No habilitar envío, campañas o respuestas IA sobre una copia recuperada hasta reconciliar sus efectos con Meta.
3. Verificar SHA-256 del archivo de base y restaurar en una base **nueva y aislada** del mismo servicio, sin CONNECT para el runtime. Verificar catálogo, restricciones, conteos y manifiesto del respaldo. El nombre activo `rinovaplus` y su URL no se sustituyen durante el ensayo.
4. Restaurar los archivos en una raíz privada nueva. Rechazar enlaces/rutas inseguras y comparar cada archivo referenciado por hash y tamaño. Conservar las copias y originales. El respaldo SQL no incluye los archivos.
5. Recuperar la clave de cifrado desde su custodia autorizada y autenticar los secretos sin mostrarlos. Revocar las sesiones y autorizaciones OAuth pendientes copiadas antes de abrir una recuperación como producción; revisar cuentas, agentes, campañas, consentimientos y cupos. No interpretar el éxito de descifrado como verificación actual de Meta.
6. Reconciliar cada envío pendiente, aceptado o incierto con los recibos/proveedor. Un mensaje enviado después del punto del respaldo puede reaparecer pendiente en una recuperación: **no reenviarlo automáticamente**. Los casos inciertos se mantienen retenidos hasta revisión, sin fabricar entregas.
7. Con aprobación del custodio, preparar el cambio al nombre/base y volumen definitivos con las escrituras detenidas; conservar los originales para reversión. La identidad del perfil exige la base definitiva, por lo que una copia de ensayo no se conecta al runtime cambiando sólo una variable.
8. Arrancar, comprobar `/health/ready`, las ocho etapas, login/roles, acceso a adjuntos y colas. Habilitar productores por cuenta de forma revisada. Emitir el recibo de restauración después de verificar base, archivos y claves. Documentar fecha, alcance, discrepancias y decisión humana.

No se ha fijado un SLA/RTO institucional ni se promete un RPO por la duración de estas pruebas. La agenda diaria es una configuración, no una garantía de pérdida máxima de datos. Una prueba de recuperación local o de reversión de interfaz tampoco acredita recuperar un servidor destruido. El cierre debe dejar aceptados explícitamente estos límites o completar antes la copia externa y su custodia.

## Reversión de despliegue

Para un defecto de interfaz compatible, seleccionar la imagen frontend anterior identificada en Coolify, comprobar el sitio y volver a la imagen revisada. Conserva DB y volumen. Una reversión del backend exige pausar/revisar productores y compatibilidad de datos; no copiar una base anterior sobre escrituras nuevas. Las pruebas de reversión ejecutadas se documentan con sus imágenes concretas en la evidencia de aceptación.

Al corte, la imagen activa es `9d8d608fa69efe526b1016f893c4f753ec812f97`; Coolify conserva `19866a7a66ae033bf25437f1228ee14bafa1f276`. La revisión automática rechazó el cambio temporal por requerir autorización explícita para esa mutación de producción. No se cambió la imagen y no se presenta como ensayo ejecutado. La autorización específica está pendiente.

Hay tres operaciones históricas inciertas de generación `comment_auto_gemini`, conservadas sin reintento automático. No son tres mensajes pendientes de salida; al corte se observaron cero SendJob pending/running. Las cuarentenas y fallos históricos permanecen visibles. El negocio siguió procesando sus eventos durante la revisión.

Evidencia actual: [revisión PostgreSQL](../../artifacts/live/p11-postgres-review-20261118.json). El backend `9d8d608` terminó saludable en Coolify y la interfaz mostró PostgreSQL 16.16, ocho procesos al día y el recibo verificado con 19 archivos. Este corte conserva general 98,04% y P11 72,50% hasta la aceptación institucional de los cinco hitos pendientes.

## Fases adicionales vigentes

P13: piloto de fichas/agentes por programa, 0/4 aceptados. P14: mejora de aprendizaje, en planificación. P15: correos/notificaciones/plantillas HTML/marca/informes, 0/7 aceptados. P16 SIIE y P17 TikTok: diferidas, 0/5 cada una. P18: auditoría y endurecimiento de tokens, IP/rate limit, 2FA, CAPTCHA e inyecciones, 0/8 aceptados. Estas fases no aportan peso al porcentaje de P0–P11 ni acreditan capacidad por estar planificadas.

Referencias operativas consultadas: [respaldos de Coolify](https://coolify.io/docs/databases/backups), [pg_dump 16](https://www.postgresql.org/docs/16/app-pgdump.html) y [pg_restore 16](https://www.postgresql.org/docs/16/app-pgrestore.html). La ejecución y sus resultados se registran aparte de la documentación del proveedor.
