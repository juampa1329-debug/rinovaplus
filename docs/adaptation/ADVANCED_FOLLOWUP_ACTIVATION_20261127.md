# Tres seguimientos por avance activados — 27 de noviembre de 2026

El titular autorizó expresamente: «Sí, activa también los tres seguimientos de interés confirmado, formulario enviado y formulario por verificar, dejando excluidos a los que pidieron no recibir mensajes». Esta autorización posterior resuelve el alcance que la revisión automática había rechazado en el corte de artifacts/live/followup-automation-20261127.json. Los estados históricos de borrador y el rechazo anterior se conservan; ya no son el estado actual de estos tres recorridos.

## Estado comprobado en RinovaPlus

Las tres plantillas CRM de Juan Pablo están Activas v1. Formulario enviado y formulario completado por verificar se activaron ahora; interés confirmado ya estaba habilitada en la biblioteca. No son nuevas plantillas aprobadas por Meta: se usan como respuesta solicitada dentro de la ventana real de24h.

Los tres flujos existentes están Activos v3, con nombres operativos «CBN · Seguimiento por avance · [caso] · 8h». Se retiró «Revisar antes de activar» y el objetivo que todavía decía «Borrador sin activadores». El cambio de nombre/objetivo creó v3; cada flujo conserva el mismo mensaje único y filtro de avance de su borrador v2, sin espera interna adicional.

Los tres activadores existentes están Activos v2, vinculados explícitamente a la v3 del flujo correspondiente. Se comprobaron nativamente evento de inactividad desde envío confirmado, espera480min, cooldown1440min y filtros concretos:

| Caso | Prioridad | Flujo | Activador |
|---|---:|---|---|
| Interés confirmado | 30 | Activo v3 | Activo v2 |
| Formulario enviado | 20 | Activo v3 | Activo v2 |
| Formulario completado por verificar | 10 | Activo v3 | Activo v2 |

Ocho comprobaciones de configuración pasaron antes de las activaciones: dos plantillas, tres flujos y tres activadores. Una reautenticación con credencial guardada se completó nativamente y se dejó vacío el segundo campo, conforme a la autorización previa del titular; no se extrajeron credenciales. Las listas finales mostraron los tres activadores y los tres flujos activos. El flujo general y su activador siguen Activos v3, sin duplicados nuevos.

## Guardas y alcance

Se conservaron sólo conversaciones reales, cuenta WhatsApp CBN, modo IA, salida ante respuesta/cambio relevante, silencio21:00–08:00 América/Bogotá, avance exacto y atención solicitada dentro24h. No se cambió consentimiento, cadencia ni ningún registro de baja. No hay reactivación general para estos avances ni confirmación automática de matrícula por la declaración de haber completado un formulario.

backend/app/institutional/contact_preference.py conserva la preferencia canónica y los alias. backend/app/institutional/campaigns.py incorpora no_contact entre los motivos de exclusión; backend/app/institutional/campaign_runtime.py vuelve a comprobar esos motivos al inscribir y antes de ejecutar. La lista CRM→No contactar se actualizó nativamente y mostró25filas sin alerta: tamaño de la primera página, no total de bajas. Es una comprobación de configuración y lectura, no un nuevo ensayo productivo enviando a una baja.

La consulta ampliada «Ver audiencia» de interés confirmado terminó con «signal timed out». No se deduce de ella un número de destinatarios elegibles ni una prueba completa de exclusión en toda la audiencia. Las comprobaciones de configuración y los estados Activos sí se verificaron. No se reintentó esa consulta global ni se dispararon inscripciones manuales para suplirla. No se afirma entrega nueva de los tres mensajes sólo por su activación; los próximos envíos dependen de las condiciones de cada conversación.

No hubo cambios de código de aplicación, DDL, seeds, servicios, modelos, escriturasSIIE, consentimientos nuevos, extensión de autorizaciones, reintentos inciertos ni nuevas aceptaciones de fases. No se repitió la suite por una operación de configuración; la verificación nueva fue nativa. Este resultado se incorpora al grafo de continuidad, separado de conversaciones privadas, sin nombres ni teléfonos de prospectos.
