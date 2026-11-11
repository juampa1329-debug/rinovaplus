# Sprint5 — campañas y seguimiento local

Fecha: 2026-10-20. Carpeta única `E:\Nuevos_Proyectos\CRM_CBN`, rama `codex/integracion-coolify`, aplicación local en `http://127.0.0.1:4173/#/campaigns`.

El propietario autorizó implementar endpoints, workers y pantalla sobre el proyecto existente, sin copias, tests ni envíos reales. Se reutilizaron SQL Server, la identidad externa, el almacén de credenciales cifradas, el bloqueo transaccional y los componentes Glass existentes. No se añadieron dependencias, un segundo transporte ni un almacén de secretos.

## Implementación de fuentes

- `backend/app/modules/campaigns/router.py`: contratos tipados, CRUD/configuración y operaciones manuales idempotentes por UUID.
- `service.py`: SQL parametrizado, revisiones CAS, segmentos de la oferta vigente, plantillas versionadas por cuenta y evaluación/preparación durable.
- `evidence.py` y `domain/scoring.py`: recibos autenticados persistidos, respuesta confirmada al último entrante y rúbricas independientes de riesgo/interés observable.
- `workers.py`: evaluación periódica y ejecuciones manuales con lease, recuperación y resultados persistidos. No ejecuta llamadas de envío ni migraciones al arrancar.
- `transport.py` y las dos fronteras del dispatcher existente: bloqueo incondicional de campañas. `activate`, `start` y `send` devuelven423; no existe ajuste de activación.
- `frontend/src/modules/campaigns/CampaignsPanel.tsx` y `campaigns.css`: Resumen, Riesgo, Reglas, Plantillas y Difusiones; borradores sin plantilla, consulta de audiencia, pausa, preparación y estados de ejecución.
- Composición en `main.py`/`App.tsx`, guarda local de rutas y proxies existentes. No se modificó la operación de Admisiones/Inbox/IA para poblar campañas.

Los endpoints usan la misma guarda local host/origen/cabecera del CRM, sin afirmar autenticación multiusuario de producción. Las llamadas de sincronización consultan Meta sólo mediante acción explícita del operador; los polls de pantalla son GET locales.

## SQL aplicado explícitamente por el coordinador

El coordinador leyó `018_campaigns.sql` y `backend/tools/migrate_campaigns.py`, verificó destino `local_sql_copy` y TLS y ejecutó el runner, con salida0. La migración crea nueve tablas únicamente en `crm_marketing`: ChurnAssessment, MessageTemplate, ContactConsent, RemarketingRule, AccountCadence, Campaign, CampaignRecipient, EvaluationRun y Policy. No se agregaron contactos, mensajes ni plantillas de ejemplo.

La ejecución aislada reutilizó el bundle de certificados del runtime mediante `SSL_CERT_FILE=/tmp/crm-ca-bundle.pem`; no se desactivó TLS. Una conexión nueva posterior confirmó Contact2/Conversation2/Message8/outbound_queue0/ProspectMemory1, iguales al punto previo a la migración.

La auditoría DDL normal ya autorizada por ADR-006 permaneció activa: SIAuditoriaCambios51565→51584 (+19). El trigger siguió habilitado con SHA256 idéntico `e869f0e38a2971a21672e04171488a7010c7fc327805b40b6daab3db464e508e`. No se desactivó ni alteró el trigger y no hubo escrituras de negocio core. 018 aplicada queda preservada; cualquier evolución SQL requiere una migración nueva explícita.

## Fronteras del indicador

La ecuación y ejemplos35/70/80 están en [el contrato](../contracts/sprint-5-campaign-model.md). No son probabilidades calibradas. Sin identidad externa exacta, entrante autenticado, respuesta positiva verificada o peso explícito de etapa, el riesgo es NULL/«No evaluable». El cálculo no transforma CreatedAt/UpdatedAt/QueueCreatedAt ni el POST aceptado en una confirmación del proveedor.

El interés observable toma señales explícitas del último entrante autenticado y se devuelve como `ComputedLeadScore`, independiente de `ConversationProfile.LeadScore` manual. No se generan señales con un LLM. Una solicitud de documentos de matrícula o un año no constituye evidencia de costo; sin respuesta monetaria confirmada no se aplica el mínimo80.

El enlace al último entrante debe existir en ResponseJob o replyToMessageId. Los envíos humanos históricos sin ese vínculo no se puntúan por suposición. La duración histórica dentro de etapa no existe en el CRM y permanece desconocida; las reglas se describen como etapa actual más inactividad de respuesta confirmada. El cooldown controla preparaciones locales, no acredita una fecha de envío.

## Aceptación manual

El coordinador recorrió la pantalla real y confirmó:

- Recalcular creó una ejecución completada con dos conversaciones evaluadas, ambas desconocidas por falta de identidad externa real; no se fabricaron indicadores numéricos.
- Crear y renombrar una regla sin plantilla, deshabilitada, persistió. La evaluación manual de esa regla terminó con assessed2/unknown2/eligible0.
- Guardar la difusión «Admisiones 2026-B», con período activo y etapa Nuevo, sin plantilla, permitió consultar y preparar audiencia. La preparación terminó matched0/prepared0; se mostraron dos contactos sin identidad externa.
- Pausar el borrador funcionó. Una llamada real al endpoint activate respondió HTTP423; no se habilitó transporte.
- Después de recargar completamente, Resumen recuperó una campaña, una regla y las cuatro ejecuciones completadas. Difusiones → Ver audiencia conservó «Admisiones 2026-B» pausada, cero identidades coincidentes y dos contactos sin identidad. Detalle mostró Enviados0/Entregados0/Leídos0/Fallidos0 con la aclaración «Estados actuales · envíos bloqueados». Los ceros derivan de la agregación vacía real; no son eventos simulados ni totales acumulados. Capturas revisadas: `sprint5-summary-persisted.png` y `sprint5-audience-metrics-persisted.png`.
- La primera sincronización explícita de Meta respondió HTTP502 sin causa visible. Se confirmó por lectura GET al WABA correcto y `detail=ProviderFailure.code`; ese primer502 no se atribuyó por suposición a credenciales. Tras traducir códigos seguros, una segunda sincronización explícita en navegador confirmó `meta_access_token_expired` (normalización existente de Graph190/subcódigo463). La UI indicó actualizar el token desde Canales, sin mostrarlo ni cambiarlo automáticamente. No hay plantillas sincronizadas ficticias ni una aceptación positiva de catálogo con credencial vigente. Captura: `sprint5-meta-token-expired.png`, en la carpeta de visualizaciones autorizada de esta sesión.

También se corrigió la notificación de ejecución: el driver devuelve RunId en mayúsculas y el comando devuelve UUID minúsculo; el seguimiento compara ambos normalizados. El aviso de cola se establece antes de refrescar y no puede sobrescribir después el estado terminal de un trabajo rápido. El coordinador confirmó en navegador el aviso «Evaluación completada» usando la ejecución real ya terminada, sin crear un trabajo ficticio adicional. No se ejecutaron tests, lint, typecheck, builds o scripts de demostración.

Las tres capturas mencionadas están en `C:\Users\Developer_PC\.codex\visualizations\2026\10\19\01a1562a-952c-7913-a6cf-c6abf669e15e`. La pestaña de entrega quedó en Campañas → Difusiones, con la campaña pausada y sus métricas actuales. No se probó eliminación de la regla usada ni se fabricó un destinatario elegible para demostrar envíos.

## Preservación final, conexión SQL nueva

El coordinador confirmó Contact2/Conversation2/Message8/outbound_queue0/ProspectMemory1, iguales al punto inicial de esta unidad. Marketing quedó con Campaign1 pausada, RemarketingRule1 deshabilitada, CampaignRecipient0, ChurnAssessment6 (todas unknown), MessageTemplate0, ContactConsent0 y EvaluationRun4 completadas (dos de riesgo, una de regla y una preparación), con máximo un intento observado. No se insertaron mensajes, identidades, grants ni receptores de ejemplo para aparentar una audiencia.

La configuración IA permanece en revisión28 con SHA256 canónico idéntico `b2ae4ecfb88b6243fe23be4ec1e331fb636d96de406f18c0860ba964dd2c8bdc`; no se guardaron nuevos modelos, claves ni ajustes del proveedor. El trigger DDL siguió activo con el mismo hash. Estos recuentos acreditan la preservación local observada, sin afirmar un inventario exhaustivo de todas las tablas institucionales.

## Límites conectados

No se activan envíos reales, grants de consentimiento, identidades externas ni documentos sintéticos. Una audiencia vacía es un resultado legítimo. Preparar persiste receptores bloqueados y evidencia; no inserta `crm.Message` ni `crm_channels.outbound_queue`.

Quedan fuera de esta entrega local la habilitación de transporte, reservas operativas de cadencia, reconciliación real de estados inciertos, gestión conectada de opt-in/opt-out y calibración institucional de las rúbricas. Las plantillas requieren credenciales vigentes y aprobación comprobada en Meta. El módulo no promete evitar todas las restricciones de la plataforma.
