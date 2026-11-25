# Inbox: contención de almacenamiento · 24 de noviembre de 2026

El aviso «No se pudo validar el acceso a la información» no distingue un problema de permisos de una espera de bloqueo. En el incidente se observaron errores PostgreSQL `55P03`, carga vacía de mensajes/contexto y un cambio de control fallido. La recarga posterior permitió atender el hilo, pero no acreditó una solución de la contención.

## Corrección

El trabajador de seguimientos acumulaba la validación de todas las ejecuciones futuras y las etapas de mantenimiento en una transacción con bloqueo institucional exclusivo. Ahora libera ese bloqueo entre contactos y entre observación, detección de inactividad y disparadores. Reconsulta cada ejecución actual bajo su propia transacción antes de validarla; si ya salió del estado activo se omite. Se siguen revisando esperas futuras, se detienen cambios de modo/respuesta/interés y se conserva la validación final antes de preparar o enviar.

La consulta de inactividad añade un filtro temprano de última entrada anterior al corte. Es una condición necesaria de la cláusula HAVING original: no elimina destinatarios que antes fueran válidos. Se mantienen recibos reales, contexto y exclusiones, sin acortar la espera configurada.

No cambian el bloqueo institucional, los permisos, el aislamiento de lecturas ni los timeouts. El registro sanitario identifica etapa, modo y duración con datos acotados, sin cuerpos SQL, mensajes de excepción ni credenciales. Sólo un `55P03` al adquirir el bloqueo antes del trabajo se comunica como `storage_busy`; los errores posteriores conservan su tratamiento y no se consideran seguros para repetir.

El frontend de Inbox y Agentes distingue servidor ocupado de identidad/clave. Una consulta GET concurrente se agrupa y se recupera una sola vez tras un segundo únicamente para `storage_busy`; respeta la pausa HTTP429. No se repiten POST/PUT, fallos de autorización, errores genéricos503 ni efectos inciertos del proveedor. Si falla de nuevo se muestra el aviso y se conserva el borrador.

## Validación local

- 106 pruebas backend seleccionadas: liberación entre doce contactos, relectura de estado concurrente, parada ante cambio Humano, separación de tareas, bloqueo de lectura/escritura conservado, clasificación antes/después del cuerpo, consulta PostgreSQL y reglas de seguimientos/bajas.
- 21 frontend seleccionadas: recuperación de ambos clientes, deduplicación, una sola repetición GET, cero repetición de envíos, permisos y pausa429 conservados; operaciones y paginación Inbox.
- Ruff seleccionado, tipos, ESLint y compilación institucional pasan. Advertencia histórica de tamaño de bundle conservada.

Publicación y observación real posteriores se registrarán al verificar Coolify. Estas pruebas no acreditan por sí solas que desaparezca toda contención futura ni una carga máxima institucional. No se reenvían mensajes de clientes para ensayar.

## Publicación y comprobación nativa

653411f publicado: backend `vkkldoyuggtjjlkxwqlwrsw4`, Success/Running, 5m34s; frontend `h1mhsciuydngvbsri7rl0lcm`, Success/Running, 1m05s. Se comprobó la versión nueva desde la interfaz, sin acceso directo a SQL ni credenciales.

Cinco cargas satisfactorias en tres hilos reales: 21, 27 y 29 mensajes en sus respectivos tramos; apartado de agentes y ficha CRM disponibles, cero alertas en las comprobaciones. En el caso original se guardó Humano y se restauró IA; una recarga posterior confirmó IA y el mismo historial, incluida la orientación previamente Entregada. No se envió ningún mensaje nuevo para probar la corrección ni se repitió el envío antiguo Sin confirmar.

El diagnóstico nuevo confirma que las esperas son al adquirir el bloqueo institucional (`institution_lock`), no fallos de clave/modelo. La muestra nativa de registros conserva cuatro55P03 a00:14:27–28UTC del25Nov durante el rollout; se reconocen, no se borran ni se afirma cero errores desde el arranque. Después de las comprobaciones y de actualizar los registros, no aparecieron errores nuevos de ese tipo en la muestra. También se conservan avisos de transacciones lentas (máximo observado3432ms); esta observación acotada no sustituye una prueba de carga institucional ni garantiza ausencia perpetua de contención.

Evidencia agregada sin nominales: `artifacts/live/inbox-storage-contention-20261124.json`. El roadmap y la auditoría académica se actualizan en el mismo repositorio, conservando las aceptaciones de fases.
