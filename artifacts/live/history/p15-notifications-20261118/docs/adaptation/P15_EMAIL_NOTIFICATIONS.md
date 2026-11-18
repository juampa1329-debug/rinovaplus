# P15 · Correos y notificaciones configurables

Plan autorizado el 18 de noviembre de 2026. **0% implementado, 0/7 unidades aceptadas.** No añade peso a los 56 criterios/279 hitos originales ni bloquea la revisión operativa actual P11. Las invitaciones y recuperación actuales por código conservan su contrato hasta integrar el correo. No se configuró proveedor ni se enviaron correos.

## Alcance

El administrador decide qué eventos notificar, a quiénes, por qué medio y con qué frecuencia. Se incluyen correos de seguridad, cambios del producto y operación, fallos/recuperación de modelos e informes. El catálogo de eventos será extensible y validado; no se afirmará que todo cambio del sistema está cubierto sin instrumentarlo y probarlo. Las preferencias nunca sustituyen permisos de acceso a los datos.

### P15.1 · Transporte y remitentes

Configurar SMTP o API de proveedor, remitente/dominio verificado, TLS, secretos sólo de runtime, prueba controlada y diagnóstico. Revisar SPF/DKIM/DMARC cuando corresponda al dominio. No declarar entrega por aceptar la cola.

### P15.2 · Reglas y destinatarios

Administración por evento, severidad, canal, cuenta y módulo; usuarios, roles o grupos autorizados. Destinatarios explícitos, preferencias individuales y política institucional para avisos críticos de seguridad. Quién puede configurar, ver y recibir cada dato se comprueba en servidor.

### P15.3 · Eventos de producto y seguridad

Alta/invitación de usuario, recuperación de contraseña, cambio de acceso, nueva conexión/canal, nuevo agente o proveedor/modelo, indisponibilidad/fallo y recuperación de modelos, fallos de colas/webhooks y otros eventos registrados. Enlaces de un solo uso, caducidad, rate limit y respuestas que no revelen si existe una cuenta.

### P15.4 · Editor y biblioteca de correo

Crear y versionar plantillas, subir/editar HTML, vista previa y envío de prueba revisado. Variables permitidas con escape, datos ausentes visibles, borrador/publicación/reversión. Biblioteca de logos, encabezados, pie, colores de marca y firma visual por remitente; inspección de archivos y recursos embebidos. Sin JavaScript, formularios ejecutables ni URLs inseguras. Firma visual no equivale a firma electrónica certificada.

### P15.5 · Cola, trazabilidad y fiabilidad

Outbox persistente en PostgreSQL, claves de idempotencia, deduplicación, reintentos con espera, caducidad, supresión y cola de fallos. Recibos de entrega/rebote cuando los soporte el proveedor, correlación, auditoría y pausa. Conservar efectos inciertos sin duplicar; ningún secreto o contenido privado en logs.

### P15.6 · Informes y agenda

Informes diarios, semanales o con frecuencia elegida; hora local y zona IANA. Períodos y filtros explícitos, agregados autorizados, destinatarios revisados, sin afirmar aperturas no observadas. Evitar datos personales innecesarios; definir qué módulos y KPIs incluye cada informe.

### P15.7 · Aceptación y operación

Probar invitación/recuperación sin enumeración, permisos, plantillas maliciosas/variables, destinatarios, DST, duplicados, caídas de proveedor, reintentos/recibos y pausa/reversión. Pruebas reales sólo a destinatarios autorizados. Documentar custodios, límites, costos, retención y recuperación.

## Paneles previstos

Ajustes → Notificaciones: transporte/remitentes, reglas/eventos y destinatarios, biblioteca de plantillas y marca, programación de informes e historial de entregas/fallos. Cada regla tendrá vista previa de destinatarios y contenido antes de activarse. Las opciones de usuarios y roles se reutilizan; no se añaden tenants ni billing.

## Numeración y dependencias

P15 es esta fase nueva. SIIE pasa de P15 a [P16](P16_SIIE_INTEGRATION.md), diferida con su base técnica conservada y 0/5 unidades aceptadas. TikTok pasa de P16 a [P17](P17_TIKTOK_PLAN.md), diferida y 0/5 unidades aceptadas. Los recibos anteriores conservan sus etiquetas históricas y no ganan aceptación por el cambio de número.

Antes de ejecutar: elegir dominio/remitente/proveedor y custodios, documentar eventos y datos permitidos por destinatario, preparar diseños y aprobar las pruebas reales. La subida de HTML requiere sanitización y aislamiento de la vista previa. Logos y firmas visuales se guardan como recursos privados inspeccionados. Una firma electrónica con validez jurídica, si se solicita, exige contrato y aceptación propios.
