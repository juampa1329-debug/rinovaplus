## P15 cerrada en su alcance inicial; P16 retomada — 2026-11-18

P15: **7/7 unidades aceptadas, 100% en el alcance inicial documentado**. Oracle SPF/DKIM Active y SMTP TLS verificados; el titular confirmó activación, recuperación, diseño final y copia del aviso operativo en el buzón de supervisión. Ocho correos reales aceptados una vez cada uno; siete al buzón de supervisión con recepción confirmada. El aviso al antiguo correo administrador sólo tiene aceptación SMTP: el titular ya no accede a ese buzón. No se enviarán nuevas pruebas allí ni se cambia su identificador de acceso sin un recorrido específico.

Backend a3f85e6 saludable en Coolify, nueve consumidores frescos. Selectores de plantilla crítica publicados y renderizado nativo de ambos enlaces comprobado con rollback, sin SMTP. Transporte revisión2, plantilla institucional revisión5. Usuario de ensayo inactivo, sin sesiones/desafíos; regla operativa revisión4 desactivada y sin destinatarios. Pasan347 backend seleccionadas (47 correo),33 frontend, tipos/ESLint/build;15 regresiones PG separadas. Escaneo amplio de estilo y advertencia de bundle conservan sus límites históricos.

Recuperación aislada closed-reviewed: siete tablas con huellas iguales, seis envelopes autenticados y dos recursos SHA; sin CONNECT del runtime, sesiones ni correo ejecutable. El corte precede la última alerta y su copia: no acredita recuperar efectos posteriores. Informes iniciales de auditoría diario/semanal y recibos OCI registrados manualmente. OPS-05 continúa pendiente de conexión automática al monitor de respaldos/infraestructura y destinatario administrador accesible; no se declara alertado todo Coolify. OPS01–06 y custodia externa/RPO-RTO conservan sus límites aceptados. Evidencia: artifacts/live/p15-mail-validation-20261118.json; manual: docs/adaptation/P15_ORACLE_OPERATOR_RUNBOOK.md.

General original P0–P11:100% cada una,56/56 criterios y279/279 hitos; P12 auxiliar:100% en PostgreSQL/Meta aceptado. Adicionales sin nuevo peso: P13 Académico/agentes por programa parcial0/4; P14 entrenamiento comercial plan; P15 correos100%7/7; **P16 API académica/financiera SIIE retomada,0/5**, contrato recibido, adaptador en construcción y datos reales pendientes; P17 TikTok diferida0/5; P18 seguridad planificada0/8. La API entregada no expone matrícula/estudiantes ni saldos y marca ofertas422 no cotizables; no se inventan datos. Los cortes inferiores son historia.

# P15 · Oracle Email Delivery y operación de correo

Corte de implementación: 18 de noviembre de 2026. Fase abierta; el código y SMTP aceptado no prueban entrega ni sustituyen la aceptación de sus siete unidades.

## Oracle y DNS

Tenancy institucional: cbnrinovaplus. Región: US East (Ashburn), `us-ashburn-1`.
Dominio registrado: `rinovaplus.com`. Remitente aprobado registrado: `notificaciones@rinovaplus.com`.
La autorización humana de generar DKIM y aprobar ese remitente queda separada de la verificación DNS.

| Tipo | Nombre en la zona rinovaplus.com | Valor |
|---|---|---|
| CNAME | `rinova20261118._domainkey` | `rinova20261118.rinovaplus.com.dkim.iad1.oracleemaildelivery.com` |
| TXT | `@` | `v=spf1 include:rp.oracleemaildelivery.com ~all` |

TTL automático o una hora; CNAME sólo DNS, sin proxy. Si existe SPF, incorporar el include en ese único registro preservando otros remitentes y su terminador; nunca duplicarlo. El DMARC observado es `p=quarantine`, con alineación relajada; conservarlo. La propagación y el estado DKIM Signing de Oracle deben verificarse antes de la aceptación. No es necesario mover los nameservers a Oracle ni cambiar MX para enviar.

Documentación primaria: [inicio de Email Delivery](https://docs.oracle.com/en-us/iaas/Content/Email/Reference/gettingstarted.htm), [SPF regional](https://docs.oracle.com/en-us/iaas/Content/Email/Tasks/configurespf.htm), [credenciales SMTP](https://docs.oracle.com/en-us/iaas/Content/Identity/access/working-with-smtp-credentials.htm).

## Secretos y dos interruptores

Oracle → My profile → Saved passwords → SMTP credentials → Generate credentials. Descripción sugerida: `RinovaPlus P15 - Correos institucionales`. El propietario genera y guarda la credencial nueva directamente, sin pasarla por el chat, Git, capturas ni logs. Es un usuario/contraseña SMTP generado por Oracle; no es la contraseña de inicio de sesión.

Coolify → backend RinovaPlus → Environment Variables → Production, sólo Runtime, Build time desactivado:

| Variable | Uso |
|---|---|
| `CRM_SMTP_HOST` | `smtp.email.us-ashburn-1.oci.oraclecloud.com` |
| `CRM_SMTP_USERNAME` | Usuario SMTP generado por Oracle |
| `CRM_SMTP_PASSWORD` | Contraseña SMTP generada por Oracle |
| `CRM_EMAIL_SCHEMA_ENABLED` | `1` únicamente después de aplicar la migración |
| `CRM_EMAIL_ENABLED` | `1` permite al consumidor intentar envíos; `0` los pausa |

La aplicación exige STARTTLS con certificado y hostname verificados, puerto 587 y endpoint Oracle admitido. No acepta un host arbitrario del formulario. Además, Ajustes → Correos y notificaciones → Envío debe tener salida habilitada. Ambos interruptores deben permitirla. Las reglas nuevas están apagadas hasta revisión. No hay un borrado de la cola al pausar.

El límite diario configurable cuenta correos distintos con intento en el día UTC, no aperturas. Hay como máximo cinco intentos ante rechazos transitorios definitivos; el proveedor conserva sus propios cupos. No se afirma coste cero ni cupo ilimitado. El propietario debe revisar los límites y precios de su tenancy antes de activar reglas o informes masivos; el piloto se limita al destinatario autorizado y muestras sin datos personales del CRM.

## PostgreSQL

Aplicar manualmente `backend/sql/p15_notifications.sql` como operador, tras respaldo. No hay DDL de arranque. El schema `rinova_notify` contiene siete tablas, fuera del catálogo congelado de 155 tablas CRM. El runtime recibe USAGE y CRUD acotado: sin CREATE, sin DELETE, sin actualización del historial, recibos o recursos. Conserva validación del perfil/identidad PostgreSQL y la clave AES-GCM existente. El outbox cifra asunto/HTML y los enlaces de acceso, ligados a base, institución e ID. Nunca imprimir contenido descifrado.

Respaldo previo aplicado en producción: `/var/lib/postgresql/data/p15-20261118/before-p15.dump`. No publicar ni copiar ese archivo a Git. La prueba SQL de instalación insertó un mensaje sintético, rechazó su duplicado por clave, lo reclamó una vez y terminó con ROLLBACK; cero registros de correo conservados por ese ensayo. No ejecutó proveedores.

## Recorridos y permisos

Administrar transporte, reglas, grupos, plantillas, recursos, informes e historial exige `users.manage`; configurar o enviar exige confirmación reciente. Todos los writes pasan por CSRF. Usuarios y roles mantienen su autoridad actual; un grupo de correo no concede permisos nuevos.

Los destinatarios de reglas e informes son usuarios activos con el permiso del evento. Se comprueban nuevamente al despachar, incluyendo correo actual y preferencias. Las preferencias propias están en Mi perfil. Invitaciones y recuperaciones sólo van al titular afectado, expiran en una hora y conservan el requisito de autenticador. El login ofrece «Olvidé mi contraseña» con resultado genérico para cuentas presentes/ausentes; límite por IP y cuenta. Usuarios permite revisar y enviar activación a una cuenta pendiente, sin devolver su código en la respuesta del envío.

HTML admite una lista cerrada de etiquetas, atributos, CSS y variables escapadas; no scripts, formularios, handlers, iframes, URLs de credenciales ni imágenes externas de seguimiento. La preview se aísla en iframe sin permisos y sin referrer. Los logos/firmas se inspeccionan, convierten a PNG sin metadatos y se incrustan como CID. Máximo 1 MB/recurso, 2048 píxeles, 20 MB/biblioteca y 2 MB/correo preparado. La firma es visual, no una firma electrónica certificada. Publicar/recuperar crea una nueva revisión, preservando historial.

Eventos instrumentados inicialmente: usuarios creados/editados, acceso canjeado, canal creado, configuración guardada, agente nuevo y transición de fallo/recuperación del proveedor del simulador y la IA automática, envío por canales y proyección de webhooks. Las reglas operan sobre eventos futuros. La integración real de esos avisos debe probarse antes de aceptar P15.3; no afirmar que cualquier evento de cualquier módulo ya está conectado.

Informes iniciales: diario/semanal, hora IANA local y día semanal; total de eventos de auditoría en el período completo anterior, sin cuerpos de conversaciones ni datos académicos. Sólo gestión de usuarios puede recibir ese agregado. Se deduplica por agenda/revisión/instante. En saltos DST avanza por el hueco; en horas duplicadas utiliza una sola ocurrencia. No hay recuperación masiva de períodos perdidos al activar una agenda.

## Estados y diagnóstico

| Estado | Significado y acción |
|---|---|
| En cola / reintento | Pendiente con próxima fecha. Puede cancelarse antes de reclamarlo. |
| Enviando | Reclamado, con lease de cinco minutos. No duplicar manualmente. |
| Aceptado por Oracle | SMTP devolvió 250 tras DATA; no prueba entrega al buzón. |
| Resultado por confirmar | Se perdió la respuesta tras DATA o se interrumpió el consumidor. Revisar logs Oracle; nunca reenvío automático. |
| Fallido | Rechazo permanente, caducidad, payload inválido o intentos agotados. Corregir causa y revisar antes de un envío nuevo. |
| Suprimido | Destinatario revocado/inactivo/sin permiso/correo cambiado/preferencia desactivada o rebote previo. |
| Entregado al proveedor del buzón / rebotado | Recibo observado en Oracle y registrado expresamente por operador. No significa leído. |

Activar Outbound Accepted y Outbound Relayed en Oracle antes del piloto. [Registros de correo](https://docs.oracle.com/en-us/iaas/Content/Email/Reference/log-guide.htm) y [validación de entrega](https://docs.oracle.com/en-us/iaas/Content/Email/Reference/gettingstarted_topic-Validate_email.htm). Los logs no son retroactivos. Correlacionar `Message-ID`/ID del correo y destinatario; registrar el ID de log, acción y fecha en `notifications/receipts` con autoridad reciente. La fuente queda `operator_observation`: no se simula un webhook ni una sincronización automática de OCI. No cargar todos los logs ni cuerpos privados en el CRM. Entrega aceptada por el proveedor receptor y confirmación humana del buzón son pruebas diferentes; no se infieren aperturas.

## Pausa, reversión y recuperación

Pausar con el interruptor de Envío o `CRM_EMAIL_ENABLED=0`; conserva cola, intentos y resultados inciertos. Desactivar reglas detiene la creación futura; para correos ya preparados se revisa/cancela su fila o se pausa todo el transporte. Recuperar una plantilla histórica carga un borrador y requiere guardarlo como nueva versión.

Antes de revertir código, apagar ambos flags de correo, conservar schema/datos/clave e imagen actual. La versión anterior ignora el schema adicional; no aplicar DROP ni borrar historial. No ejecutar semillas/preparadores antiguos sobre esta base poblada.

El respaldo de PostgreSQL incluye documentos, assets y outbox de P15; el dump previo a P15 y el recibo P11 de 157 tablas/19 archivos no cubren este dominio nuevo. Se necesita un respaldo fresco y restauración aislada, sin CONNECT del runtime ni workers. Autenticar los payloads con su binding original sólo desde el operador. Antes de usar una base restaurada, pausar productores/transporte y conservar como `uncertain/restored_requires_review` las filas queued/retry/sending: un envío pudo haberse aceptado después del corte del respaldo. No reenviar automáticamente por haber restaurado. Custodia externa, retención/espacio y RPO/RTO siguen en OPS/P18.

## Aceptación pendiente

Guardar resultados reales por unidad en `tasks/p15-notifications-progress.json`: DNS y SMTP, destinatarios/permisos/preferencias, invitación/recuperación/2FA, HTML/recursos/versión, persistencia/fallos/reintentos/recibos/pausa, agenda/informe y recuperación/operación. La prueba real requiere confirmación del buzón autorizado y evidencia de Oracle. OPS-05 sólo cierra al demostrar alertas efectivamente entregadas. No usar código ni cantidad de tests como sustituto de esta aceptación.


## Verificación real del 18 de noviembre

El titular confirmó recepción, activación con ingreso y recuperación con nuevo ingreso. El usuario Consulta de ensayo fue desactivado; cero sesiones y desafíos vigentes. Cinco correos transaccionales autorizados, sin campañas activas por estas pruebas. La plantilla institucional está limpia y publicada en revisión4; el HTML importado queda como ejemplo en borrador y las dos imágenes sintéticas se conservan identificadas en biblioteca privada.

El remitente de una prueba manual queda ligado a su usuario administrador para volver a validar su acceso antes de SMTP. Una supresión local por revocación/preferencia/correo cambiado sólo afecta al elemento; un rebote permanente observado conserva el bloqueo a la dirección. Los recibos se registran manualmente desde Historial con ID/fecha de Oracle, sin afirmar integración automática OCI.

Informes iniciales: intervalos móviles explícitos de24h o7×24h terminados en el instante programado; se muestra el rango UTC. La hora de disparo usa zona IANA y reglas DST. El total es de auditoría, no un informe financiero ni todos los KPIs del CRM. El límite de recuperación por cuenta es3/h y el de dirección de conexión5/15min; tras el proxy actual la dirección de conexión puede ser compartida. El tratamiento de IP real con proxies de confianza queda en P18, sin confiar en encabezados arbitrarios del cliente.

La matriz de ejecución nativa usa PostgreSQL real con rollback, bajo el bloqueo de la institución. SMTP se reemplaza sólo en el proceso de ensayo, no en el servicio. Los scripts guardados en artifacts/live/p15-*-rollback-20261118.py son evidencia del ensayo controlado; no ejecutarlos como preparadores ni resembrar la base. El primer informe falló por CreatedAt y se corrigió a OccurredAt; el intento ampliado de supresión detectó el guard manual que se reforzó. Se conservan los intentos y resultados en p15-mail-validation-20261118.json.


En Envío se puede elegir una plantilla publicada para invitación y otra para recuperación. Ambas deben incluir {{enlace}}. Si después se archiva una plantilla asignada, el acceso usa un diseño seguro de respaldo; no se revela al solicitante si una cuenta existe por una diferencia de configuración. Los diseños de respaldo y nuevos usan tipografía compatible con correo. Las reglas y agendas conservan su propia selección y permanecen desactivadas hasta revisión humana.
