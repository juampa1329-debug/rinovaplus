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
