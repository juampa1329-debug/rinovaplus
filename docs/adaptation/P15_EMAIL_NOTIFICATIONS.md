## P15: entrega real y corrección de activación — 2026-11-18

Oracle confirma SPF y firma DKIM activos. Tres correos controlados a cbnaudiovisuales@gmail.com fueron aceptados en un intento por envío; el titular confirmó su recepción. El log de Oracle acredita relay de la invitación a Gmail con SMTP 250 y TLS. El usuario de prueba Consulta continúa pendiente de activación; el titular reportó un error de validación y el backend registró ValueError. Se corrige la clasificación de contraseña rechazada (422 explicativo), se refuerza la ruta de activación sin exponer el token al servidor y se diferencia «Activar mi cuenta» de la muestra. No afirmar resuelto hasta repetir el recorrido real.

Pasan 333 pruebas backend seleccionadas (35 de correo); nuevas regresiones de enlaces y múltiples plantillas. La copia P15 aislada conserva las siete tablas nuevas, incluida la imagen y los tres envelopes cifrados, con huellas iguales al snapshot; runtime sin CONNECT y sin consumidor en esa copia. No sustituye la recuperación P11 ni valida copia externa/custodia. Se corrige crear otro registro y recuperar versiones como borrador/pausadas. Historial incorpora observación manual de recibos Oracle, diferenciada de un webhook automático.

P15 permanece 0/7 aceptadas, en validación. General original P0–P11:100%; P12 auxiliar:100% en alcance aceptado. P13 Académico/agentes por programa:parcial (0/4); P14 entrenamiento comercial:plan; P15 correos/notificaciones:pruebas (0/7); P16 API SIIE:diferida (0/5); P17 TikTok:diferida (0/5); P18 seguridad:plan (0/8). No alterar el denominador original ni cerrar OPS-05 por una muestra transaccional.

## P15 en implementación y pruebas — 2026-11-18

Ajustes → Correos y notificaciones incorpora transporte Oracle SMTP/TLS, reglas por evento y destinatarios, grupos, preferencias propias, versiones de HTML y recursos de marca inspeccionados, informes diarios/semanales y outbox cifrado en PostgreSQL. Recuperación por correo sin enumeración y activación revisada desde Usuarios reutilizan códigos de un uso/una hora y conservan 2FA. El consumidor SMTP es independiente de mensajería. SMTP aceptado no equivale a entrega; resultados inciertos no se reenvían automáticamente. Los recibos de Oracle se registran como observación de operador, no como webhook automático.

**P15 sigue abierta: 0/7 unidades aceptadas.** Hay implementación parcial con pruebas; no se declara 100% ni entrega real todavía. Pendientes: propagación/verificación DKIM/SPF, prueba real de SMTP/recibos/invitación/recuperación, validar la cobertura instrumentada de eventos de colas/webhooks y modelo automático, revisión de informes y ensayo de recuperación P15. Oracle: dominio y remitente registrados en Ashburn; credenciales guardadas por el propietario en Coolify, sin valores en el repositorio. Migración manual aplicada: 7 tablas nativas separadas, 155 tablas CRM intactas, runtime sin CREATE ni DELETE; prueba de deduplicación/reclamación con rollback, cero correos persistidos por ese ensayo.

Pasan 330 pruebas backend seleccionadas (33 nuevas P15), 27 frontend seleccionadas, tipos/lint modificado y build de workspace. Backend 1c302ef desplegado saludable con 9 consumidores; autenticación SMTP/TLS verificada sin envío. Plantilla publicada, preview y recurso privado probados en UI. SPF público correcto; DKIM y entrega real pendientes de validar. El ajuste siguiente corrige framing CRLF de SMTP, enlace en texto plano, pausa visual y restauración de sesión sin destello de login. Advertencia previa de bundle grande conservada. Evidencia y manual: `tasks/p15-notifications-progress.json`, `docs/adaptation/P15_ORACLE_OPERATOR_RUNBOOK.md`. Preimágenes: `artifacts/live/history/p15-notifications-20261118/`.

General original P0–P11:100%; P12 auxiliar:100% en el alcance PostgreSQL/Meta aceptado. Las fases adicionales conservan seguimiento separado: P13 Académico/agentes por programa (parcial,0/4), P14 entrenamiento comercial (plan), P15 correos/notificaciones (en pruebas,0/7), P16 API académica/financiera SIIE (diferida,0/5), P17 TikTok (diferida,0/5), P18 seguridad/ciberseguridad (plan,0/8). OPS-05 no se cierra sin alertas realmente entregadas. Los cortes inferiores conservan su evidencia histórica.

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
