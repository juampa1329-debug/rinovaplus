# Matriz de paridad Scentra y CRM CBN

Fecha: 2026-10-25. 57 hallazgos de inspección estática. Ninguno certifica SQL, navegador del producto o proveedor en este equipo. Cada etapa del roadmap conserva sus aceptaciones propias.

Los estados describen la fuente actual. «Parcial» no significa fallido ni operativo en producción; «por preservar» identifica trabajo útil. Los fragmentos JSON conservan toda la evidencia, la aceptación y relaciones revisadas. Tabla generada por `backend/tools/adaptation_graphs.py`; editar los fragmentos y regenerar.

| ID | Capacidad | Estado de fuente | Etapa |
|---|---|---|---|
| ai_agents_hierarchy | Constructor y ejecución de agentes con jerarquía educativa | parcial con capacidades educativas propias | P5 |
| ai_collective_memory | Memoria colectiva institucional editable y reutilizada | parcial sin paridad de persistencia | P6 |
| ai_applicant_memory | Memoria del aspirante con evidencia y separación por conversación | implementada en codigo con validacion conectada por verificar | P6 |
| ai_institutional_dna | ADN institucional y memoria de marca | parcial sin perfil institucional equivalente | P6 |
| ai_knowledge_retrieval | Conocimiento institucional publicado y recuperación relevante | parcial con adaptador sql ya existente | P6 |
| ai_feedback | Correcciones humanas, resultados y candidatos de mejora | parcial | P10 |
| ai_training_governance | Packs de entrenamiento, evaluaciones, promoción y reversión | ausente en composicion inspeccionada | P10 |
| ai_ml_pipeline | Aprendizaje predictivo entrenado y registro de modelos | ausente como entrenamiento real del destino | P10 |
| ai_no_billing_policy | Políticas institucionales y presupuestos de IA sin planes comerciales | adaptacion transversal necesaria | P2 |
| ai_execution_governance | Ejecución, selección por perfil, fallback y acciones asistidas | parcial ya implementada en codigo | P5 |
| foundation_users | Usuarios institucionales, sesiones y autorización por roles | ausente en composicion activa | P2 |
| foundation_settings | Ajustes coherentes de módulos, IA/modelos, canales, webhooks y usuarios | parcial en fuente | P2 |
| foundation_sql_dialect | Persistencia SQL Server 2019 y migraciones sobre la base existente | riesgo verificado en fuente | P1 |
| foundation_runtime | Despliegue institucional Linux con Docker y SQL externo o en red privada | riesgo verificado en fuente | P1 |
| foundation_delivery | Aceptación por capas, trazabilidad y operación continua | pendiente de revalidacion | P11 |
| inbox_01 | Inbox operativo con filtros, mensajes paginados, ficha y control humano | parcial en fuente | P3 |
| inbox_02 | Comentarios sociales dentro del Inbox | parcial en fuente | P4 |
| inbox_03 | Ficha CRM, etapas, etiquetas y campos personalizados compartidos | parcial en fuente | P3 |
| inbox_04 | Listado CRM escalable y filtros en servidor | parcial en fuente | P3 |
| inbox_05 | Tareas y responsables humanos/IA | parcial en fuente | P3 |
| inbox_06 | Mensajes externos, multimedia y estados de entrega | parcial en fuente | P4 |
| inbox_07 | Mini CRM conversacional y predicciones con evidencia | parcial en fuente | P10 |
| inbox_08 | Identidad educativa, actividad y unificación reversible existentes | existente por preservar | P3 |
| inbox_09 | Contrato de destino SQL Server 2019 en Linux | riesgo verificado en fuente | P1 |
| inbox_information_design | Ficha CRM única y editable con diagnóstico compacto en Inbox y CRM | brecha ux verificada en fuente | P3 |
| inbox_churn_surface | Riesgo de abandono conectado al mini CRM y CRM con procedencia diferenciada | parcial backend y superficie desconectada | P3 |
| marketing_campaign_builder | Campañas CRM, plantillas CRM y segmentos guardados | parcial | P8 |
| marketing_triggers_flows | Activadores y flujos de remarketing de varios pasos | parcial | P8 |
| marketing_campaign_governance | Preflight, quiet hours, simulación, versiones y pruebas A/B | ausente como equivalencia | P8 |
| marketing_broadcast_transport | Mensajería masiva y ejecución de destinatarios | parcial bloqueado por codigo | P7 |
| marketing_meta_templates | Catálogo y administración de plantillas WhatsApp de Meta | parcial | P7 |
| marketing_broadcast_reporting | Reportes, exportación, destinatarios y reintento de fallidos | parcial | P7 |
| marketing_ads | Anuncios: cuentas, campañas, leads y conversión al Inbox | ausente en composicion activa | P9 |
| marketing_social_comments | Comentarios sociales, respuestas, reacciones e IA asistida | parcial backend existente ui pendiente | P4 |
| marketing_receipt_ingestion | Recepción durable, firma y procesamiento de webhooks | base existente a extender | P4 |
| marketing_no_billing | Independencia de planes sin perder controles operativos | decision confirmada con trabajo de adaptacion | P2 |
| channels_sql2019_parity_contract | Contrato versionado para conservar campos/acciones Scentra en Canales, con identidad multicuenta explícita y persistencia SQL2019 | definido verificado offline | P1 |
| channels_parity_schema_rehearsal | Release de 24 tablas Canales multicuenta con historial, catálogo completo y ensayo físico preservando SIIE/C5/C9 | implementado verificado en restauracion | P1 |
| channels_parity_mapping_repositories | Correspondencias B011 y repositorios/API C12 independientes, con claves verificadas y permisos mínimos | implementado verificado en api aislada | P1 |
| phase_progress_p0 | Reporte de criterios canónicos aceptados en P0 | reported exact accepted criteria | P0 |
| phase_progress_p1 | Reporte de criterios canónicos aceptados en P1 | reported exact accepted criteria | P1 |
| phase_progress_p2 | Reporte de criterios canónicos aceptados en P2 | reported exact accepted criteria | P2 |
| phase_progress_p3 | Reporte de criterios canónicos aceptados en P3 | reported exact accepted criteria | P3 |
| phase_progress_p4 | Reporte de criterios canónicos aceptados en P4 | reported exact accepted criteria | P4 |
| phase_progress_p5 | Reporte de criterios canónicos aceptados en P5 | reported exact accepted criteria | P5 |
| phase_progress_p6 | Reporte de criterios canónicos aceptados en P6 | reported exact accepted criteria | P6 |
| phase_progress_p7 | Reporte de criterios canónicos aceptados en P7 | reported exact accepted criteria | P7 |
| phase_progress_p8 | Reporte de criterios canónicos aceptados en P8 | reported exact accepted criteria | P8 |
| phase_progress_p9 | Reporte de criterios canónicos aceptados en P9 | reported exact accepted criteria | P9 |
| phase_progress_p10 | Reporte de criterios canónicos aceptados en P10 | reported exact accepted criteria | P10 |
| phase_progress_p11 | Reporte de criterios canónicos aceptados en P11 | reported exact accepted criteria | P11 |
| general_preview_runtime_contract | Preview general independiente y receta autónoma con persistencia,salud y recuperación local de P1.4 | implementado verificado en preview local P1 4 | P1 |
| foundation_extension_contract | Contrato de extensión por objetos que preserve CRM poblado y SIIE | diseño revisado no implementado | P1 |
| foundation_extension_rehearsal | Ensayo versionado de extensión CRM que preserve SIIE, CRM poblado e historia | ensayado en restauraciones no runtime | P1 |
| channels_repository_contract | Repositorios de Canales con perfil propio, guard mutable y API local acotada | ensayado en repositorios y api local | P1 |
| channels_scentra_parity | Funciones y organización de Canales iguales a Scentra, con persistencia SQL Server y estilo CBN | parcial sin paridad completa | P4 |
| channels_capability_ui | UI Glass de Canales por capacidades con perfil propio y lectura de credenciales limitada a columnas | implementado verificado en ui aislada | P1 |

## Agentes, ADN institucional, memoria, conocimiento y aprendizaje evaluado

Evidencia estructurada: [ai-memory.json](fragments/ai-memory.json).

### ai_agents_hierarchy — Constructor y ejecución de agentes con jerarquía educativa

**Diferencia:** El destino ya incorpora instrucciones, objetivos, reglas, plantillas, modelos, ámbitos de memoria y restricciones heredadas. Su jerarquía orientador/programa/etapa es un requisito propio que no debe reemplazarse por el registro general del SaaS. Por decisión vigente del propietario del 2026-10-21, guardar una configuración válida deja el perfil disponible en la misma transacción; el diagnóstico es opcional y no existe aprobación humana adicional del perfil. ApprovedVersion es un sello técnico SQL. La paridad debe verificarse por acción y estado conservando esa excepción explícita frente a Scentra, sin reinstalar su aprobación obligatoria.

**Aceptación:** Tabla de equivalencias del constructor y de cada acción; crear/editar/replay/409; guardar perfil válido lo deja disponible en la misma transacción sin aprobación humana adicional; diagnóstico opcional; guardar un perfil pausado conserva la pausa; archivo/restauración y fuentes vigentes; una sola propiedad de respuesta; padre/programa/etapa preservados. Ensayo en copia SQL autorizada y reversión de configuración/versiones. La revisión de fuentes y la aprobación de acciones sensibles se tratan por sus contratos propios, no como aprobación obligatoria de perfil.

**Scentra:** [../saas-version/backend/app_saas/agents/service.py:1028](../../../saas-version/backend/app_saas/agents/service.py#L1028), [../saas-version/backend/app_saas/agents/router.py:240](../../../saas-version/backend/app_saas/agents/router.py#L240).
**CRM CBN:** [backend/app/modules/agents/domain.py:32](../../backend/app/modules/agents/domain.py#L32), [backend/app/modules/agents/domain.py:231](../../backend/app/modules/agents/domain.py#L231), [backend/app/modules/agents/service.py:296](../../backend/app/modules/agents/service.py#L296), [backend/migrations/019_admissions_agents.sql:20](../../backend/migrations/019_admissions_agents.sql#L20), [docs/contracts/admissions-agents.md:37](../../docs/contracts/admissions-agents.md#L37), [backend/app/modules/agents/service.py:625](../../backend/app/modules/agents/service.py#L625).

### ai_collective_memory — Memoria colectiva institucional editable y reutilizada

**Diferencia:** El ámbito collective actual incorpora políticas y la instrucción de usar fuentes públicas autorizadas; no equivale al CRUD de recuerdos colectivos tipados de Scentra con título, contenido, ámbito, confianza, visibilidad, caducidad y auditoría. Diseñar persistencia institucional sin compartir conversaciones ni hechos privados de otros aspirantes.

**Aceptación:** Migración aditiva SQL Server 2019, API/UI de alta/listado/archivo o eliminación según contrato y consumo real en prompts; ámbitos institución/programa/etapa y vigencia; autorización y trazabilidad; rechazar contenido privado fuera de alcance; restauración/rollback probado.

**Scentra:** [../saas-version/backend/app_saas/agents/service.py:1696](../../../saas-version/backend/app_saas/agents/service.py#L1696), [../saas-version/backend/app_saas/agents/service.py:1716](../../../saas-version/backend/app_saas/agents/service.py#L1716), [../saas-version/backend/app_saas/agents/service.py:1931](../../../saas-version/backend/app_saas/agents/service.py#L1931), [../saas-version/backend/app_saas/agents/router.py:247](../../../saas-version/backend/app_saas/agents/router.py#L247).
**CRM CBN:** [backend/app/modules/agents/runtime.py:101](../../backend/app/modules/agents/runtime.py#L101), [backend/app/modules/agents/domain.py:16](../../backend/app/modules/agents/domain.py#L16).

### ai_applicant_memory — Memoria del aspirante con evidencia y separación por conversación

**Diferencia:** El destino posee ProspectMemory y exige UUID/cita de mensaje entrante para hechos declarados; esto debe conservarse. Archivos/importación/exportación de memorias de agentes del SaaS son una capacidad distinta y no se acreditan por la memoria contextual. No se ha conectado la DB ni probado el runtime en esta auditoría.

**Aceptación:** Pruebas de persistencia, corrección, reinicio, caducidad, cambio de programa y ausencia de mezcla entre aspirantes; importación/exportación de memoria sólo con permisos y formato validado si se incorpora, sin restaurar instrucciones o datos ajenos silenciosamente.

**Scentra:** [../saas-version/backend/app_saas/agents/service.py:3468](../../../saas-version/backend/app_saas/agents/service.py#L3468), [../saas-version/backend/app_saas/agents/service.py:3641](../../../saas-version/backend/app_saas/agents/service.py#L3641).
**CRM CBN:** [backend/migrations/017_ai_admissions.sql:37](../../backend/migrations/017_ai_admissions.sql#L37), [backend/app/modules/ai/application/admissions_prompt.py:21](../../backend/app/modules/ai/application/admissions_prompt.py#L21), [backend/app/modules/agents/runtime.py:114](../../backend/app/modules/agents/runtime.py#L114).

### ai_institutional_dna — ADN institucional y memoria de marca

**Diferencia:** El destino tiene prompt global, tono/reglas por agente y políticas académicas. No se identificó un módulo activo equivalente al perfil Brand Brain con voz, públicos, límites, evidencias, briefs y control de versiones/gobierno. ADN debe descomponerse en perfil institucional y comportamiento medible; catálogo, precios y requisitos académicos conservan autoridad SIIE.

**Aceptación:** Contrato explícito de campos ADN aplicables a educación; perfil institucional versionado con fuentes, revisión y auditoría; composición determinista con restricciones de agentes sin sobrescribir SIIE; lectura del perfil efectivo y rollback de versión probado.

**Scentra:** [../saas-version/backend/app_saas/brand_brain/router.py:61](../../../saas-version/backend/app_saas/brand_brain/router.py#L61), [../saas-version/backend/app_saas/brand_brain/router.py:207](../../../saas-version/backend/app_saas/brand_brain/router.py#L207), [../saas-version/backend/app_saas/brand_brain/router.py:458](../../../saas-version/backend/app_saas/brand_brain/router.py#L458).
**CRM CBN:** [backend/app/modules/ai/domain/models.py:126](../../backend/app/modules/ai/domain/models.py#L126), [backend/app/modules/agents/domain.py:32](../../backend/app/modules/agents/domain.py#L32), [backend/app/modules/agents/runtime.py:95](../../backend/app/modules/agents/runtime.py#L95).

### ai_knowledge_retrieval — Conocimiento institucional publicado y recuperación relevante

**Diferencia:** Scentra usa entre sus mecanismos vectores dispersos en vector_json y puntuación de fragmentos; no corresponde asumir pgvector o embeddings densos como requisito de esa implementación. El destino ya mantiene documentos/fragmentos/términos y búsqueda léxica de documentos publicados, con alcance de programa/etapa. Evaluar relevancia con preguntas educativas antes de elegir otro índice. SQL Server 2019 no debe recibir JSONB ni sintaxis PostgreSQL.

**Aceptación:** Conjunto revisado de preguntas y fuentes, procedencia de fragmento/revisión/página, recuperación sólo publicada/vigente/en alcance, abstención ante ausencia y conservación de SQL como fuente primaria. Comparar precisión y coste contra implementación vigente; migraciones e índices compatibles con 2019.

**Scentra:** [../saas-version/backend/app_saas/knowledge/router.py:231](../../../saas-version/backend/app_saas/knowledge/router.py#L231), [../saas-version/backend/app_saas/knowledge/router.py:1632](../../../saas-version/backend/app_saas/knowledge/router.py#L1632), [../saas-version/backend/app_saas/knowledge/router.py:2107](../../../saas-version/backend/app_saas/knowledge/router.py#L2107).
**CRM CBN:** [backend/app/modules/knowledge/service.py:62](../../backend/app/modules/knowledge/service.py#L62), [backend/app/modules/knowledge/service.py:94](../../backend/app/modules/knowledge/service.py#L94), [backend/app/modules/agents/service.py:246](../../backend/app/modules/agents/service.py#L246), [backend/migrations/017_ai_admissions.sql:19](../../backend/migrations/017_ai_admissions.sql#L19).

### ai_feedback — Correcciones humanas, resultados y candidatos de mejora

**Diferencia:** Existen correcciones de análisis y planes/operaciones de estrategia, pero ello no demuestra un circuito equivalente de feedback/candidatos/packs ni un conjunto de entrenamiento. Separar declaración humana, evaluación del resultado, modificación de instrucciones y actualización de pesos de un modelo.

**Aceptación:** Contrato de resultado objetivo y origen autorizado; eventos inmutables/versionados; corrección no reescribe evidencia original; dataset revisado deduplicado con exclusión de datos sensibles y particiones temporales; trazabilidad desde feedback a candidato.

**Scentra:** [../saas-version/backend/app_saas/training/feedback_service.py:602](../../../saas-version/backend/app_saas/training/feedback_service.py#L602), [../saas-version/backend/app_saas/training/feedback_service.py:734](../../../saas-version/backend/app_saas/training/feedback_service.py#L734), [../saas-version/backend/app_saas/intelligence/service.py:2905](../../../saas-version/backend/app_saas/intelligence/service.py#L2905).
**CRM CBN:** [backend/app/modules/conversation_analysis/api/router.py:310](../../backend/app/modules/conversation_analysis/api/router.py#L310), [backend/migrations/005_conversation_analysis.sql:248](../../backend/migrations/005_conversation_analysis.sql#L248), [backend/migrations/009_conversation_strategy.sql:28](../../backend/migrations/009_conversation_strategy.sql#L28).

### ai_training_governance — Packs de entrenamiento, evaluaciones, promoción y reversión

**Diferencia:** El historial y A/B de configuración de agentes no sustituyen los packs, casos, ejecuciones de evaluación, promoción y rollback de Scentra. No se identificó un módulo activo destino que implemente ese ciclo completo. La planificación debe distinguir evaluación de prompts/RAG de entrenamiento ML.

**Aceptación:** Casos educativos reproducibles con criterios aprobados; ejecución guarda versión de prompt/fuentes/modelo/dataset y resultado; promoción sólo de una versión evaluada, historial y reversión a versión previa; no autoentrenamiento o despliegue de pesos al guardar un recuerdo.

**Scentra:** [../saas-version/backend/app_saas/training/service.py:340](../../../saas-version/backend/app_saas/training/service.py#L340), [../saas-version/backend/app_saas/training/eval_service.py:407](../../../saas-version/backend/app_saas/training/eval_service.py#L407), [../saas-version/backend/app_saas/training/eval_service.py:780](../../../saas-version/backend/app_saas/training/eval_service.py#L780), [../saas-version/backend/app_saas/training/eval_service.py:1041](../../../saas-version/backend/app_saas/training/eval_service.py#L1041), [../saas-version/backend/app_saas/training/eval_service.py:1138](../../../saas-version/backend/app_saas/training/eval_service.py#L1138).
**CRM CBN:** [backend/app/main.py:39](../../backend/app/main.py#L39), [backend/app/modules/agents/runtime.py:31](../../backend/app/modules/agents/runtime.py#L31).

### ai_ml_pipeline — Aprendizaje predictivo entrenado y registro de modelos

**Diferencia:** Scentra contiene entrenamiento .fit con scikit-learn y opciones LightGBM/XGBoost sobre datos sintéticos o autoetiquetados, además de reglas baseline. No se verificó una red neuronal. El score determinista de abandono o un LLM de análisis de CRM CBN no acredita un modelo entrenado ni precisión predictiva. El port requerirá extracción de características/etiquetas SQL Server y artefactos derivados, sin una nueva DB transaccional ni activar entrenamiento en esta etapa.

**Aceptación:** Definir objetivo educativo medible y etiquetas verificadas; conjunto temporal independiente sin fuga; baseline, métricas y umbral de aceptación aprobados; modelo versionado con artefacto/hash/procedencia y shadow sin envíos; promoción y rollback; métricas sintéticas o autoetiquetadas no se presentan como resultado institucional real.

**Scentra:** [../saas-version/backend/app_saas/ml_service/pipeline.py:200](../../../saas-version/backend/app_saas/ml_service/pipeline.py#L200), [../saas-version/backend/app_saas/ml_service/pipeline.py:223](../../../saas-version/backend/app_saas/ml_service/pipeline.py#L223), [../saas-version/backend/app_saas/ml_service/pipeline.py:244](../../../saas-version/backend/app_saas/ml_service/pipeline.py#L244), [../saas-version/backend/app_saas/ml_service/pipeline.py:329](../../../saas-version/backend/app_saas/ml_service/pipeline.py#L329), [../saas-version/backend/app_saas/ml_service/pipeline.py:373](../../../saas-version/backend/app_saas/ml_service/pipeline.py#L373), [../saas-version/backend/app_saas/intelligence/service.py:2521](../../../saas-version/backend/app_saas/intelligence/service.py#L2521).
**CRM CBN:** [backend/app/modules/campaigns/domain/scoring.py:73](../../backend/app/modules/campaigns/domain/scoring.py#L73), [backend/app/modules/conversation_analysis/application/runtime.py:80](../../backend/app/modules/conversation_analysis/application/runtime.py#L80).

### ai_no_billing_policy — Políticas institucionales y presupuestos de IA sin planes comerciales

**Diferencia:** La fuente combina permisos funcionales con tenant operativo y límites de plan. La copia educativa excluye planes/cobros, pero conserva autorización institucional, cuotas de tokens, topes USD operativos, alarmas/corte y trazabilidad de consumo. El destino ya etiqueta su estimación como not_billing y la reserva por jerarquía. No eliminar estos controles por quitar billing.

**Aceptación:** Matriz de cada import/llamada de billing reutilizada por módulos elegidos y reemplazo explícito por política institucional; usuarios sin permiso no ejecutan; agotamiento detiene consumo; no tablas de suscripción/facturación ni interfaz de pagos; pruebas de concurrencia/reserva/liquidación y costes inciertos.

**Scentra:** [../saas-version/backend/app_saas/agents/service.py:24](../../../saas-version/backend/app_saas/agents/service.py#L24), [../saas-version/backend/app_saas/agents/service.py:1565](../../../saas-version/backend/app_saas/agents/service.py#L1565), [../saas-version/backend/app_saas/intelligence/service.py:1058](../../../saas-version/backend/app_saas/intelligence/service.py#L1058).
**CRM CBN:** [backend/app/modules/agents/domain.py:46](../../backend/app/modules/agents/domain.py#L46), [backend/app/modules/agents/runtime.py:133](../../backend/app/modules/agents/runtime.py#L133), [backend/app/modules/agents/runtime.py:147](../../backend/app/modules/agents/runtime.py#L147).

### ai_execution_governance — Ejecución, selección por perfil, fallback y acciones asistidas

**Diferencia:** El destino incluye experimentos deterministas, proveedor/modelo por perfil, reservas/liquidación, historial, acciones borrador/aprobación y control humano. La aprobación de acciones sensibles es independiente del guardado de perfiles: por decisión vigente del propietario, guardar un perfil válido lo deja disponible sin aprobación humana adicional y con diagnóstico opcional. La evidencia histórica describe aceptaciones parciales de SQL/UI/proveedor, pero esta auditoría es estática; revisar completitud de las herramientas expuestas y revalidación antes de ejecutarlas. No se atribuye a la sesión actual ninguna ejecución de pruebas ni estado de gates globales.

**Aceptación:** Cada herramienta del constructor enlaza a ejecutor real o se mantiene deshabilitada con causa; conflictos de versión, takeover humano, recuperación de lease, reinicio y fallback no producen respuestas duplicadas; escenarios por programa/etapa en SQL Server 2019 y reversión sin pérdida de memoria/historial. Se conserva guardar y utilizar sin aprobación adicional de perfil; permisos, fuentes y acciones sensibles mantienen controles propios.

**Scentra:** [../saas-version/backend/app_saas/agents/router.py:240](../../../saas-version/backend/app_saas/agents/router.py#L240), [../saas-version/backend/app_saas/agents/service.py:1854](../../../saas-version/backend/app_saas/agents/service.py#L1854).
**CRM CBN:** [backend/app/modules/agents/runtime.py:50](../../backend/app/modules/agents/runtime.py#L50), [backend/app/modules/agents/generation.py:74](../../backend/app/modules/agents/generation.py#L74), [backend/app/modules/agents/operations.py:82](../../backend/app/modules/agents/operations.py#L82), [backend/migrations/020_agent_execution.sql:12](../../backend/migrations/020_agent_execution.sql#L12).

## Fundación institucional, datos y operación

Evidencia estructurada: [foundation.json](fragments/foundation.json).

### foundation_users — Usuarios institucionales, sesiones y autorización por roles

**Diferencia:** Usuarios, Perfil y Seguridad muestran identidad pendiente; los contratos de auth son propuestas/stubs, no sesiones institucionales. Conservar la separación entre sesión, empleado SIIE y agente IA.

**Aceptación:** Inicio/cierre y revocación de sesión; usuarios/roles y permisos reales en servidor; pruebas negativas de acceso; sin panel comercial multiempresa ni datos de empleados copiados como autoridad.

**Scentra:** [../saas-version/backend/app_saas/shared/security.py:222](../../../saas-version/backend/app_saas/shared/security.py#L222), [../saas-version/backend/app_saas/auth/router.py:139](../../../saas-version/backend/app_saas/auth/router.py#L139).
**CRM CBN:** [frontend/src/features/Settings.tsx:83](../../frontend/src/features/Settings.tsx#L83), [backend/app/contracts.py:49](../../backend/app/contracts.py#L49).

### foundation_settings — Ajustes coherentes de módulos, IA/modelos, canales, webhooks y usuarios

**Diferencia:** Reutilizar ajustes IA y canales existentes; completar configuración institucional y módulos sin trasladar selección de plan. Inventariar capacidades reales por proveedor, sin convertir un catálogo en soporte operativo.

**Aceptación:** Cada ajuste tiene propietario, validación, persistencia, permisos, efecto documentado y feedback; claves de sólo escritura; activar módulo no activa proveedor ni gasta presupuesto por sí solo; estilo Glass conservado.

**Scentra:** [../saas-version/frontend/src/App.jsx:182](../../../saas-version/frontend/src/App.jsx#L182), [../saas-version/backend/app_saas/config.py:30](../../../saas-version/backend/app_saas/config.py#L30).
**CRM CBN:** [frontend/src/features/Settings.tsx:9](../../frontend/src/features/Settings.tsx#L9), [frontend/src/features/ChannelSettings.tsx:60](../../frontend/src/features/ChannelSettings.tsx#L60), [frontend/src/modules/ai/components/AiSettingsPanel.tsx:195](../../frontend/src/modules/ai/components/AiSettingsPanel.tsx#L195).

### foundation_sql_dialect — Persistencia SQL Server 2019 y migraciones sobre la base existente

**Diferencia:** P1.1 inventarió 19 SQL/68 declaraciones y P1.2 implementó contrato de destino/TLS offline. P1.3 definió secuencia de 18 unidades nuevas propuestas, diario atómico/adopción/reconciliación, drift por modelo final y recuperación acotada a CRM. No hay SQL institucional, runner ni snapshots finales implementados ni conexión/DDL; los históricos permanecen intactos y la aceptación SQL sigue pendiente. El intento SQL-R1 no pudo autenticar porSSL/TLS; la captura histórica no acredita el estado actual.

**Aceptación:** Inventario tabla/columna/FK/índice; T-SQL 2019; JSON NVARCHAR con ISJSON; destino y contrato verificados sin suponer instancia Windows; migración nueva explícita, repetición y drift ensayados en copia restaurable; cero DDL al arranque.

**Scentra:** [../saas-version/backend/app_saas/db.py:35](../../../saas-version/backend/app_saas/db.py#L35), [../saas-version/backend/requirements.txt:4](../../../saas-version/backend/requirements.txt#L4).
**CRM CBN:** [backend/app/sql_target.py:241](../../backend/app/sql_target.py#L241), [backend/app/sql_workspace.py:161](../../backend/app/sql_workspace.py#L161), [backend/migrations/015_inbox_unified.sql:3](../../backend/migrations/015_inbox_unified.sql#L3), [docs/adaptation/sql/P1_3_MIGRATION_PLAN.md:3](../../docs/adaptation/sql/P1_3_MIGRATION_PLAN.md#L3), [docs/adaptation/sql/migration-plan.json:1](../../docs/adaptation/sql/migration-plan.json#L1).

### foundation_runtime — Despliegue institucional Linux con Docker y SQL externo o en red privada

**Diferencia:** P1.2 prepara perfil SQL/identidad/TLS y bloquea workspace institucional. P1.3 define migrador separado, locks, mantenimiento y respaldo/restauración, sin implementar transporte ni activar producto. Compose sigue siendo desarrollo local. P1.4 debe definir imagen, CA, secretos/estado y operación; implementación y aceptación conectada permanecen pendientes. SQL-R1 autorizó inspección local de metadatos, pero tres conexiones TLS fallaron08001 antes de autenticación/SELECT; destino Windows actual frente aDocker anterior pendiente. No hay aceptación conectada ni esquema observado nuevo.

**Aceptación:** Imagen reproducible; API/worker/media/secretos persistentes; SQL por DNS/TCP y TLS válido; readiness por capacidad; reinicio/recuperación y restauración probados; acceso compartido sólo con auth. No publicar puertos de DB innecesarios.

**Scentra:** [../saas-version/docker-compose.saas.yml:1](../../../saas-version/docker-compose.saas.yml#L1).
**CRM CBN:** [compose.yaml:1](../../compose.yaml#L1), [backend/app/config.py:41](../../backend/app/config.py#L41), [backend/app/sql_target.py:200](../../backend/app/sql_target.py#L200), [docs/decisions/ADR-012-sql-target-contract.md:9](../../docs/decisions/ADR-012-sql-target-contract.md#L9), [docs/adaptation/sql/SQL_R1_REVIEW.md:3](../../docs/adaptation/sql/SQL_R1_REVIEW.md#L3).

### foundation_delivery — Aceptación por capas, trazabilidad y operación continua

**Diferencia:** Documentación histórica mezcla cortes demo, SQL local y activación real. Registrar por requisito qué se verificó en fuente, pruebas, SQL, navegador o proveedor; el grafo no prueba operación ni equivale a memoria conversacional completa.

**Aceptación:** Cada etapa cierra con evidencia saneada, riesgos, reversión, archivos/hashes y siguiente paso. SQL, proveedor, IA y UI se aceptan por separado; no declarar éxito global si falta una capa requerida.

**Scentra:** [../saas-version/backend/app_saas/main.py:99](../../../saas-version/backend/app_saas/main.py#L99), [../saas-version/backend/app_saas/workers/runner.py:1](../../../saas-version/backend/app_saas/workers/runner.py#L1).
**CRM CBN:** [backend/app/main.py:42](../../backend/app/main.py#L42), [README.md:31](../../README.md#L31), [docs/roadmap.md:5](../../docs/roadmap.md#L5).

## Inbox, comentarios sociales, mini CRM y CRM

Evidencia estructurada: [inbox-crm.json](fragments/inbox-crm.json).

### inbox_01 — Inbox operativo con filtros, mensajes paginados, ficha y control humano

**Diferencia:** Existe base activa y SQL Server para conservar. La equivalencia debe probar cada filtro, lectura, borrador y transición; el nombre Inbox ni la aceptación histórica demuestran paridad con Scentra. El montaje destino usa /api/local/crm/inbox, no el router SaaS importado.

**Aceptación:** Matriz de filtros acumulables y paginación comprobada; seleccionar/navegar no cambia de contacto ni pierde borrador; actualización obsoleta produce conflicto; tomar control humano invalida trabajo IA pendiente; conservar Glass en escritorio y móvil.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:2688](../../../saas-version/backend/app_saas/crm/router.py#L2688), [../saas-version/backend/app_saas/crm/router.py:2857](../../../saas-version/backend/app_saas/crm/router.py#L2857), [../saas-version/backend/app_saas/crm/router.py:3802](../../../saas-version/backend/app_saas/crm/router.py#L3802).
**CRM CBN:** [backend/app/modules/inbox/application/service.py:388](../../backend/app/modules/inbox/application/service.py#L388), [frontend/src/modules/inbox/pages/Inbox.tsx:376](../../frontend/src/modules/inbox/pages/Inbox.tsx#L376), [backend/app/sql_workspace.py:229](../../backend/app/sql_workspace.py#L229).

### inbox_02 — Comentarios sociales dentro del Inbox

**Diferencia:** La pestaña presenta Comentarios no conectados aunque ya existen GET /api/v1/social-comments, POST /{id}/reply, persistencia e ingesta. Scentra añade reacciones, generación IA y ajustes de comentarios. Conectar/reutilizar lo existente antes de duplicar tablas/colas; determinar por canal qué acciones reales corresponden.

**Aceptación:** UI Glass carga/pagina/filtra comentarios reales, distingue vacío/error/no configurado, responde pública/privadamente sólo donde el adaptador lo permite y refleja cola/resultado; idempotencia y comentario retirado comprobados; reacción/IA se habilitan sólo con implementación y autorización verificadas.

**Scentra:** [../saas-version/backend/app_saas/social/router.py:49](../../../saas-version/backend/app_saas/social/router.py#L49), [../saas-version/backend/app_saas/social/router.py:78](../../../saas-version/backend/app_saas/social/router.py#L78), [../saas-version/backend/app_saas/social/router.py:87](../../../saas-version/backend/app_saas/social/router.py#L87), [../saas-version/backend/app_saas/social/router.py:95](../../../saas-version/backend/app_saas/social/router.py#L95).
**CRM CBN:** [frontend/src/modules/inbox/pages/Inbox.tsx:1108](../../frontend/src/modules/inbox/pages/Inbox.tsx#L1108), [backend/app/modules/channels/router.py:295](../../backend/app/modules/channels/router.py#L295), [backend/app/modules/channels/workers.py:348](../../backend/app/modules/channels/workers.py#L348), [backend/migrations/011_channels.sql:60](../../backend/migrations/011_channels.sql#L60).

### inbox_03 — Ficha CRM, etapas, etiquetas y campos personalizados compartidos

**Diferencia:** Ya hay catálogo SQL compartido con etapas/probabilidad opcional/activos, etiquetas activas e inactivas y campos tipados. Scentra usa pipeline y etiquetas relacionales con contratos propios. No reemplazar etapas oficiales SIIE ni convertir etiquetas textuales existentes a identificadores sin mapeo/migración explícitos.

**Aceptación:** Inventario campo a campo; crear/desactivar/editar definiciones conserva valores históricos; Clientes y mini CRM muestran el mismo catálogo y validación; cambios incompatibles tienen migración forward y ensayo de reversión sin alterar SIIE.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:1081](../../../saas-version/backend/app_saas/crm/router.py#L1081), [../saas-version/backend/app_saas/crm/router.py:1255](../../../saas-version/backend/app_saas/crm/router.py#L1255), [../saas-version/backend/app_saas/crm/router.py:2446](../../../saas-version/backend/app_saas/crm/router.py#L2446), [../saas-version/frontend/src/CrmPanel.jsx:648](../../../saas-version/frontend/src/CrmPanel.jsx#L648).
**CRM CBN:** [backend/app/modules/crm_configuration/application/service.py:28](../../backend/app/modules/crm_configuration/application/service.py#L28), [backend/app/modules/crm_configuration/application/service.py:76](../../backend/app/modules/crm_configuration/application/service.py#L76), [backend/app/modules/crm_configuration/application/service.py:171](../../backend/app/modules/crm_configuration/application/service.py#L171), [backend/migrations/006_crm_configuration.sql:21](../../backend/migrations/006_crm_configuration.sql#L21), [frontend/src/modules/clients/pages/Clients.tsx:622](../../frontend/src/modules/clients/pages/Clients.tsx#L622).

### inbox_04 — Listado CRM escalable y filtros en servidor

**Diferencia:** El endpoint activo de Clientes llama a store.read(), carga el snapshot completo y filtra en Python; no ofrece paginación SQL como el Inbox. Una base institucional amplia no debe depender de transferir todo el workspace por búsqueda.

**Aceptación:** Contrato de listado SQL acotado con filtros antes de paginar; preservar alias de unificación, detalle, grupos y selección compartida con Inbox; mediciones con volumen no productivo y descarte de respuestas obsoletas; mantener compatibilidad del snapshot donde siga siendo necesario.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:998](../../../saas-version/backend/app_saas/crm/router.py#L998).
**CRM CBN:** [backend/app/modules/clients/api/router.py:44](../../backend/app/modules/clients/api/router.py#L44), [backend/app/sql_workspace.py:317](../../backend/app/sql_workspace.py#L317), [frontend/src/modules/clients/pages/Clients.tsx:257](../../frontend/src/modules/clients/pages/Clients.tsx#L257).

### inbox_05 — Tareas y responsables humanos/IA

**Diferencia:** Hay tareas SQL por conversación, asignaciones independientes humano/IA, directorio de empleados y SLA configurable. No se encontró en el transporte activo una lista global equivalente a GET /crm/tasks. La pertenencia al equipo no sustituye autenticación/RBAC; el runtime debe conservar un solo dueño de respuesta.

**Aceptación:** CRUD/idempotencia/conflictos y reasignación a empleados/agentes elegibles; SLA no configurado distinto de vencido; listado transversal y filtros sólo si son parte de la equivalencia aceptada; pruebas de doble ejecución y toma humana concurrente con salida IA.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:2934](../../../saas-version/backend/app_saas/crm/router.py#L2934), [../saas-version/backend/app_saas/crm/router.py:2990](../../../saas-version/backend/app_saas/crm/router.py#L2990), [../saas-version/backend/app_saas/crm/router.py:3044](../../../saas-version/backend/app_saas/crm/router.py#L3044), [../saas-version/backend/app_saas/crm/router.py:3827](../../../saas-version/backend/app_saas/crm/router.py#L3827).
**CRM CBN:** [backend/app/modules/inbox/application/operations.py:639](../../backend/app/modules/inbox/application/operations.py#L639), [backend/app/modules/inbox/application/operations.py:682](../../backend/app/modules/inbox/application/operations.py#L682), [backend/app/modules/inbox/application/operations.py:690](../../backend/app/modules/inbox/application/operations.py#L690), [backend/app/modules/inbox/application/operations.py:703](../../backend/app/modules/inbox/application/operations.py#L703), [backend/migrations/003_local_inbox.sql:39](../../backend/migrations/003_local_inbox.sql#L39).

### inbox_06 — Mensajes externos, multimedia y estados de entrega

**Diferencia:** El compositor distingue guardar local y enviar externo por identidad, y existe dispatcher durable/outbox y multimedia; no describirlo como totalmente inexistente por documentación histórica. Falta aceptación actual por canal de flujo íntegro, recibos firmados, incertidumbre, reintentos y handoff. No crear otra cola para replicar Scentra.

**Aceptación:** Enviar sólo a identidad seleccionada; adjuntos/audio/imagen/documento según capacidades; guardar local no envía; replay no duplica; caída entre POST y recibo produce estado incierto reconciliable; recibido/entregado/leído corresponden a evidencia del proveedor; rollback de código conserva outbox y mensajes.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:3432](../../../saas-version/backend/app_saas/crm/router.py#L3432), [../saas-version/backend/app_saas/crm/router.py:3769](../../../saas-version/backend/app_saas/crm/router.py#L3769).
**CRM CBN:** [frontend/src/modules/inbox/pages/Inbox.tsx:333](../../frontend/src/modules/inbox/pages/Inbox.tsx#L333), [backend/app/modules/inbox/application/service.py:473](../../backend/app/modules/inbox/application/service.py#L473), [backend/app/modules/inbox/application/media.py:139](../../backend/app/modules/inbox/application/media.py#L139), [backend/app/modules/channels/workers.py:612](../../backend/app/modules/channels/workers.py#L612), [backend/migrations/015_inbox_unified.sql:22](../../backend/migrations/015_inbox_unified.sql#L22), [backend/migrations/016_inbox_media.sql:9](../../backend/migrations/016_inbox_media.sql#L9).

### inbox_07 — Mini CRM conversacional y predicciones con evidencia

**Diferencia:** MiniCrm ya compone análisis conversacional, estrategia y actividad; hay puntuación/temperatura manuales separadas. Debe mapearse el comportamiento útil de Scentra conservando procedencia y nulabilidad; las reglas heurísticas y el análisis configurado/desactivado no son por sí mismos aprendizaje neuronal ni probabilidad calibrada.

**Aceptación:** Mostrar fuente/fecha/estado de análisis y conservar corrección humana; ausencia de predicción no se vuelve cero; score manual no se sobrescribe con derivado; resumen/intención/objeciones/siguiente acción enlazan evidencia del hilo y respetan privacidad entre aspirantes.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:731](../../../saas-version/backend/app_saas/crm/router.py#L731), [../saas-version/backend/app_saas/crm/router.py:3214](../../../saas-version/backend/app_saas/crm/router.py#L3214), [../saas-version/backend/app_saas/crm/router.py:3319](../../../saas-version/backend/app_saas/crm/router.py#L3319).
**CRM CBN:** [frontend/src/features/MiniCrm.tsx:5](../../frontend/src/features/MiniCrm.tsx#L5), [backend/app/sql_workspace.py:79](../../backend/app/sql_workspace.py#L79), [backend/migrations/015_inbox_unified.sql:11](../../backend/migrations/015_inbox_unified.sql#L11).

### inbox_08 — Identidad educativa, actividad y unificación reversible existentes

**Diferencia:** CRM CBN tiene identidad declarada/candidatos SIIE y unificación lógica reversible que no deben perderse al copiar el merge de Scentra. Los contactos, hilos y memorias originales mantienen autoridad; coincidencia documental no autoriza matrícula ni fusión de identidades académicas.

**Aceptación:** Ensayar comparar/unir/deshacer con cambios posteriores y conflictos; conservar trazabilidad, histórico, origen y redacción IA; métricas no dependen de filtros del historial; ninguna migración mueve/borrar core SIIE ni reasigna mensajes originales.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:2036](../../../saas-version/backend/app_saas/crm/router.py#L2036), [../saas-version/backend/app_saas/crm/router.py:2122](../../../saas-version/backend/app_saas/crm/router.py#L2122).
**CRM CBN:** [backend/app/modules/contacts/api/router.py:283](../../backend/app/modules/contacts/api/router.py#L283), [backend/app/modules/contacts/application/activity.py:274](../../backend/app/modules/contacts/application/activity.py#L274), [backend/app/modules/contacts/application/merge.py:519](../../backend/app/modules/contacts/application/merge.py#L519), [backend/app/modules/contacts/application/merge.py:523](../../backend/app/modules/contacts/application/merge.py#L523), [backend/migrations/007_institutional_identity.sql:21](../../backend/migrations/007_institutional_identity.sql#L21), [backend/migrations/008_contact_merge.sql:21](../../backend/migrations/008_contact_merge.sql#L21).

### inbox_09 — Contrato de destino SQL Server 2019 en Linux

**Diferencia:** verify_target y migración 015 fijan el destino local a instancia SQLEXPRESS. El nuevo objetivo Linux/Docker requiere contrato de entorno explícito y verificado; quitar el guard de seguridad sin sustituto no es una adaptación válida. No se consultó la base para comprobar versión, edición ni compatibilidad.

**Aceptación:** Documentar servidor/base y huella autorizados, SQL Server 2019/compatibilidad; guard rechaza sistema/producción equivocada y acepta sólo el destino configurado; comprobar cada migración en restauración no productiva con respaldo/replay/rechazo de drift; nada de DDL al arrancar.

**Scentra:** [../saas-version/backend/app_saas/db.py:15](../../../saas-version/backend/app_saas/db.py#L15).
**CRM CBN:** [backend/app/sql_workspace.py:161](../../backend/app/sql_workspace.py#L161), [backend/migrations/015_inbox_unified.sql:3](../../backend/migrations/015_inbox_unified.sql#L3).

### inbox_information_design — Ficha CRM única y editable con diagnóstico compacto en Inbox y CRM

**Diferencia:** La ficha Inbox muestra teléfono, programa, jornada, etiquetas, tipo, intereses, campos y notas en un bloque de lectura arriba y repite su edición abajo en Ficha compartida y campos del contacto, abierto por defecto. Entre ambos se intercalan análisis, estrategia, evaluación manual, unificación y estado operativo. MiniCrm apila secciones completas; Clientes añade el mismo mini CRM a un formulario ya extenso. Esto explica la duplicación y exceso de texto señalado por el usuario. Tomar Scentra como referencia de jerarquía y acciones conservando Glass, sin copiar literalmente sus propias repeticiones ni sus valores predictivos de reserva.

**Aceptación:** P3 entrega una sola ficha del contacto con edición en el mismo lugar para campos CRM autorizados, sin duplicado de todos los valores en bloque lectura más formulario inferior; datos oficiales SIIE permanecen identificados y de lectura. Un único borrador/guardar/descartar preserva validación, conflictos, selección de ficha principal y conversación de origen. Orden: identidad/etapa y acciones frecuentes, campos operativos, diagnóstico breve no repetido, actividad/detalles. Explicaciones largas, procedencia técnica, metodología, auditoría y unificación pasan a ayuda contextual o secciones plegables sin ocultar errores ni estado pendiente. Reutilizar estructura entre Inbox y Clientes, conservar Glass y probar teclado/foco, scroll, móvil y ausencia de pérdida de borradores. El diseño P3 reserva la superficie del diagnóstico; la inferencia y contrato final dependen de P10.

**Scentra:** [../saas-version/frontend/src/App.jsx:8695](../../../saas-version/frontend/src/App.jsx#L8695), [../saas-version/frontend/src/App.jsx:8730](../../../saas-version/frontend/src/App.jsx#L8730), [../saas-version/frontend/src/CrmPanel.jsx:534](../../../saas-version/frontend/src/CrmPanel.jsx#L534), [../saas-version/frontend/src/CrmPanel.jsx:546](../../../saas-version/frontend/src/CrmPanel.jsx#L546).
**CRM CBN:** [frontend/src/modules/inbox/pages/Inbox.tsx:992](../../frontend/src/modules/inbox/pages/Inbox.tsx#L992), [frontend/src/modules/inbox/pages/Inbox.tsx:1036](../../frontend/src/modules/inbox/pages/Inbox.tsx#L1036), [frontend/src/modules/inbox/pages/Inbox.tsx:1066](../../frontend/src/modules/inbox/pages/Inbox.tsx#L1066), [frontend/src/modules/inbox/components/InboxContactEditor.tsx:92](../../frontend/src/modules/inbox/components/InboxContactEditor.tsx#L92), [frontend/src/modules/inbox/components/InboxAssessment.tsx:56](../../frontend/src/modules/inbox/components/InboxAssessment.tsx#L56), [frontend/src/features/MiniCrm.tsx:14](../../frontend/src/features/MiniCrm.tsx#L14), [frontend/src/modules/clients/pages/Clients.tsx:527](../../frontend/src/modules/clients/pages/Clients.tsx#L527), [frontend/src/modules/clients/pages/Clients.tsx:622](../../frontend/src/modules/clients/pages/Clients.tsx#L622).

### inbox_churn_surface — Riesgo de abandono conectado al mini CRM y CRM con procedencia diferenciada

**Diferencia:** No falta todo el churn: campañas ya consulta crm_marketing.ChurnAssessment y expone GET /api/v1/crm/predictions; Campañas muestra riesgo por rúbrica versionada con motivos/fecha y valor desconocido sin evidencia. El mini CRM compartido muestra además una estimación cualitativa de abandono de ConversationStrategy, mientras InboxAssessment edita puntaje/temperatura manuales. La ficha no consume una evaluación unificada por contacto/conversación del servicio de campañas y el usuario percibe que el abandono no está integrado. Son productos distintos: evaluación manual, rúbrica determinista de campañas, interpretación cualitativa y futura predicción aprendida; no sumarlos ni rotularlos como una misma probabilidad. La fuente Scentra también usa valores 0 y porcentajes de reserva que no deben trasladarse.

**Aceptación:** P10 define DTO de diagnóstico por conversación/contacto que reutiliza la última evaluación disponible, con estado evaluable/desconocido/no aplicable/obsoleto, tipo de cálculo (manual, regla, interpretación IA o modelo validado), valor nullable, motivos, evidencia, fecha, cobertura y versión. Mini CRM y CRM consumen el mismo diagnóstico compacto diseñado en P3, sin segunda copia del resumen ni necesidad de abrir Campañas; distinguen riesgo de abandono y temperatura/interés. Nunca mostrar 0 ni porcentaje/probabilidad por ausencia de dato; rúbrica 0–100 se identifica como indicador y no sobrescribe el valor manual. Para fichas unificadas, indicar hilo evaluado y no mezclar scores de otros orígenes sin regla explícita. Cambios de conversación no conservan resultados de otra ficha, contexto antiguo se marca y errores no producen scores. Recálculo actualiza diagnóstico y Campañas coherentemente con evidencia; activación de inferencia/modelo conserva su aceptación propia y no habilita envíos. Dependencia de diseño P3 y datos/contratos de P10.

**Scentra:** [../saas-version/backend/app_saas/crm/router.py:731](../../../saas-version/backend/app_saas/crm/router.py#L731), [../saas-version/frontend/src/App.jsx:3078](../../../saas-version/frontend/src/App.jsx#L3078), [../saas-version/frontend/src/App.jsx:8717](../../../saas-version/frontend/src/App.jsx#L8717), [../saas-version/frontend/src/App.jsx:8813](../../../saas-version/frontend/src/App.jsx#L8813).
**CRM CBN:** [backend/app/modules/campaigns/service.py:81](../../backend/app/modules/campaigns/service.py#L81), [backend/app/modules/campaigns/router.py:82](../../backend/app/modules/campaigns/router.py#L82), [backend/migrations/018_campaigns.sql:16](../../backend/migrations/018_campaigns.sql#L16), [frontend/src/modules/campaigns/CampaignsPanel.tsx:122](../../frontend/src/modules/campaigns/CampaignsPanel.tsx#L122), [frontend/src/modules/conversation-strategy/pages/ConversationStrategy.tsx:184](../../frontend/src/modules/conversation-strategy/pages/ConversationStrategy.tsx#L184), [frontend/src/modules/inbox/components/InboxAssessment.tsx:15](../../frontend/src/modules/inbox/components/InboxAssessment.tsx#L15), [backend/app/modules/inbox/application/service.py:301](../../backend/app/modules/inbox/application/service.py#L301), [frontend/src/features/MiniCrm.tsx:20](../../frontend/src/features/MiniCrm.tsx#L20), [frontend/src/modules/clients/pages/Clients.tsx:622](../../frontend/src/modules/clients/pages/Clients.tsx#L622).

## Marketing, campañas, anuncios y comentarios sociales

Evidencia estructurada: [marketing.json](fragments/marketing.json).

### marketing_campaign_builder — Campañas CRM, plantillas CRM y segmentos guardados

**Diferencia:** El destino compone un módulo real de campañas, pero su modelo actual agrupa reglas, predicciones y difusiones. El segmento vive dentro de Campaign y la plantilla es de Meta; no equivalen al catálogo separado de plantillas CRM, segmentos persistidos y campañas CRM de Scentra.

**Aceptación:** Inventariar DTO y tablas existentes; añadir primero plantillas CRM y segmentos persistidos reutilizables mediante migración SQL Server 2019 nueva. Verificar crear/editar/preview/revisión/paginación, filtros de programa-período-jornada, conflictos y conservación de borradores. Mantener tokens y componentes Glass; no copiar colores ni crear una segunda autoridad de contactos.

**Scentra:** [../saas-version/backend/app_saas/campaigns/router.py:750](../../../saas-version/backend/app_saas/campaigns/router.py#L750), [../saas-version/backend/app_saas/campaigns/router.py:863](../../../saas-version/backend/app_saas/campaigns/router.py#L863), [../saas-version/backend/app_saas/campaigns/router.py:955](../../../saas-version/backend/app_saas/campaigns/router.py#L955), [../saas-version/frontend/src/CampaignsPanel.jsx:47](../../../saas-version/frontend/src/CampaignsPanel.jsx#L47).
**CRM CBN:** [backend/app/modules/campaigns/router.py:67](../../backend/app/modules/campaigns/router.py#L67), [backend/app/modules/campaigns/service.py:215](../../backend/app/modules/campaigns/service.py#L215), [frontend/src/modules/campaigns/CampaignsPanel.tsx:12](../../frontend/src/modules/campaigns/CampaignsPanel.tsx#L12).

### marketing_triggers_flows — Activadores y flujos de remarketing de varios pasos

**Diferencia:** RemarketingRule evalúa etapa/inactividad/riesgo/cooldown y prepara destinatarios. No implementa el constructor general de condiciones/acciones, simulación/copia/versiones ni inscripciones con progreso por pasos y esperas de los flujos de Scentra.

**Aceptación:** Separar reglas actuales de activadores y flujos; definir contratos tipados sin SQL libre. Añadir inscripciones y cursores de paso durables, replay, pausa/cancelación, espera persistida, expiración de lease, exclusión por respuesta/control humano y reanudación segura. Comparar ejemplos de Scentra con eventos educativos sintéticos; no activar envíos para demostrar el constructor.

**Scentra:** [../saas-version/backend/app_saas/campaigns/router.py:1213](../../../saas-version/backend/app_saas/campaigns/router.py#L1213), [../saas-version/backend/app_saas/campaigns/router.py:1634](../../../saas-version/backend/app_saas/campaigns/router.py#L1634), [../saas-version/backend/app_saas/campaigns/router.py:1743](../../../saas-version/backend/app_saas/campaigns/router.py#L1743), [../saas-version/backend/app_saas/workers/remarketing.py:132](../../../saas-version/backend/app_saas/workers/remarketing.py#L132), [../saas-version/backend/app_saas/workers/triggers.py:39](../../../saas-version/backend/app_saas/workers/triggers.py#L39).
**CRM CBN:** [backend/app/modules/campaigns/router.py:37](../../backend/app/modules/campaigns/router.py#L37), [backend/app/modules/campaigns/service.py:181](../../backend/app/modules/campaigns/service.py#L181), [backend/app/modules/campaigns/service.py:342](../../backend/app/modules/campaigns/service.py#L342).

### marketing_campaign_governance — Preflight, quiet hours, simulación, versiones y pruebas A/B

**Diferencia:** La Policy destino configura pesos e intervalo de evaluación y usa revisiones CAS. Eso no cubre quiet hours, instantáneas inmutables de configuración, preflight versionado de campañas/activadores/flujos, simulación y atribución A/B.

**Aceptación:** Preservar revisiones CAS y añadir versiones/preflight antes de activación. Definir ventanas America/Bogota con persistencia UTC, incluidos cruces de medianoche; probar rechazos por configuración/plantilla obsoleta. Persistir asignación A/B estable y métricas con evidencia, nunca rellenar resultados vacíos.

**Scentra:** [../saas-version/backend/app_saas/campaigns/router.py:646](../../../saas-version/backend/app_saas/campaigns/router.py#L646), [../saas-version/backend/app_saas/campaigns/router.py:709](../../../saas-version/backend/app_saas/campaigns/router.py#L709), [../saas-version/backend/app_saas/campaigns/router.py:1058](../../../saas-version/backend/app_saas/campaigns/router.py#L1058), [../saas-version/backend/app_saas/campaigns/router.py:1277](../../../saas-version/backend/app_saas/campaigns/router.py#L1277), [../saas-version/migrations/037_saas_campaigns_phase7_enterprise.sql:12](../../../saas-version/migrations/037_saas_campaigns_phase7_enterprise.sql#L12).
**CRM CBN:** [backend/app/modules/campaigns/router.py:25](../../backend/app/modules/campaigns/router.py#L25), [backend/app/modules/campaigns/service.py:70](../../backend/app/modules/campaigns/service.py#L70), [backend/migrations/018_campaigns.sql:173](../../backend/migrations/018_campaigns.sql#L173).

### marketing_broadcast_transport — Mensajería masiva y ejecución de destinatarios

**Diferencia:** Crear borradores/audiencias/preparaciones está implementado, pero activate/start/send devuelven 423. La audiencia parte siempre de marketing_transport_disabled y el dispatcher rechaza campañas en dos fronteras. Ningún interruptor de configuración habilita la ejecución; retirar sólo el 423 no completa el transporte.

**Aceptación:** Implementar reserva transaccional por cuenta/cadencia, elegibilidad revalidada justo antes de encolar/enviar y enlace único a crm_channels.outbound_queue. Cubrir consentimiento/revocación, opt-out, plantilla aprobada vigente, identidad exacta, control humano, pausa, workers concurrentes, timeout incierto y reconciliación antes de reintentar. Habilitar únicamente en prueba controlada autorizada; rollback pausa nuevas reservas y conserva mensajes/recibos históricos.

**Scentra:** [../saas-version/backend/app_saas/broadcasts/router.py:1263](../../../saas-version/backend/app_saas/broadcasts/router.py#L1263), [../saas-version/backend/app_saas/broadcasts/router.py:1592](../../../saas-version/backend/app_saas/broadcasts/router.py#L1592).
**CRM CBN:** [backend/app/modules/campaigns/router.py:141](../../backend/app/modules/campaigns/router.py#L141), [backend/app/modules/campaigns/service.py:33](../../backend/app/modules/campaigns/service.py#L33), [backend/app/modules/campaigns/service.py:287](../../backend/app/modules/campaigns/service.py#L287), [backend/app/modules/campaigns/transport.py:6](../../backend/app/modules/campaigns/transport.py#L6), [backend/app/modules/channels/workers.py:443](../../backend/app/modules/channels/workers.py#L443), [backend/app/modules/channels/workers.py:630](../../backend/app/modules/channels/workers.py#L630).

### marketing_meta_templates — Catálogo y administración de plantillas WhatsApp de Meta

**Diferencia:** El destino ya sincroniza plantillas versionadas por cuenta/idioma y evita seleccionar versiones superadas. Faltan la creación/edición de plantillas del proveedor y sus controles/pantallas equivalentes a Scentra.

**Aceptación:** Conservar IDs y versiones existentes; mapear componentes/parámetros, ejemplos y estados con validación servidor. Separar guardado de borrador y envío a revisión del proveedor. Revisar documentación oficial vigente de Meta antes de llamadas y verificar cambios sólo en cuenta de prueba autorizada. No fabricar aprobación desde estado local.

**Scentra:** [../saas-version/backend/app_saas/broadcasts/router.py:857](../../../saas-version/backend/app_saas/broadcasts/router.py#L857), [../saas-version/backend/app_saas/broadcasts/router.py:934](../../../saas-version/backend/app_saas/broadcasts/router.py#L934), [../saas-version/backend/app_saas/broadcasts/router.py:1022](../../../saas-version/backend/app_saas/broadcasts/router.py#L1022).
**CRM CBN:** [backend/app/modules/campaigns/router.py:97](../../backend/app/modules/campaigns/router.py#L97), [backend/app/modules/campaigns/service.py:121](../../backend/app/modules/campaigns/service.py#L121), [backend/migrations/018_campaigns.sql:40](../../backend/migrations/018_campaigns.sql#L40).

### marketing_broadcast_reporting — Reportes, exportación, destinatarios y reintento de fallidos

**Diferencia:** El detalle destino muestra hasta 200 destinatarios y conteos agrupados, pero no equivale al reporte/exportación/filtros/paginación y reintento de Scentra. Estados del POST local no acreditan eventos firmados de entrega; debe conectarse la evidencia del dispatcher con CampaignRecipient.

**Aceptación:** Paginación y filtros estables por destinatario, conteos independientes de página y exportación autenticada protegida frente a fórmulas CSV. Distinguir queued/sent/delivered/read/failed/uncertain con IDs/fechas reales; reintentar sólo estados elegibles mediante idempotencia y consentimiento vigente, sin repetir uncertain sin reconciliar.

**Scentra:** [../saas-version/backend/app_saas/broadcasts/router.py:1462](../../../saas-version/backend/app_saas/broadcasts/router.py#L1462), [../saas-version/backend/app_saas/broadcasts/router.py:1518](../../../saas-version/backend/app_saas/broadcasts/router.py#L1518), [../saas-version/backend/app_saas/broadcasts/router.py:1592](../../../saas-version/backend/app_saas/broadcasts/router.py#L1592).
**CRM CBN:** [backend/app/modules/campaigns/service.py:242](../../backend/app/modules/campaigns/service.py#L242), [backend/app/modules/channels/workers.py:383](../../backend/app/modules/channels/workers.py#L383), [backend/app/modules/channels/workers.py:399](../../backend/app/modules/channels/workers.py#L399).

### marketing_ads — Anuncios: cuentas, campañas, leads y conversión al Inbox

**Diferencia:** No se encontró módulo/ruta/pantalla activa equivalente a Ads en el destino. El módulo campaigns es CRM/marketing, no un administrador de cuentas/campañas/leads publicitarios. La paridad inicial debe seguir el comportamiento real de ads/router.py de Scentra; no atribuirle compra/publicación autónoma de anuncios si no existe en ese módulo.

**Aceptación:** Diseñar tablas aisladas para cuentas/campañas/leads publicitarios, claves externas por proveedor/cuenta y mapeo educativo; importación replay-safe y conversión a contacto/conversación sin duplicar identidad. Añadir panel Glass y trazabilidad origen-anuncio-programa-Inbox. Separar administración local, sincronización y cualquier escritura real del proveedor; no asumir permisos/token/leadgen disponibles.

**Scentra:** [../saas-version/backend/app_saas/ads/router.py:364](../../../saas-version/backend/app_saas/ads/router.py#L364), [../saas-version/backend/app_saas/ads/router.py:386](../../../saas-version/backend/app_saas/ads/router.py#L386), [../saas-version/backend/app_saas/ads/router.py:476](../../../saas-version/backend/app_saas/ads/router.py#L476), [../saas-version/backend/app_saas/ads/router.py:655](../../../saas-version/backend/app_saas/ads/router.py#L655), [../saas-version/backend/app_saas/ads/router.py:721](../../../saas-version/backend/app_saas/ads/router.py#L721), [../saas-version/migrations/012_saas_ads_social.sql:4](../../../saas-version/migrations/012_saas_ads_social.sql#L4).
**CRM CBN:** [backend/app/main.py:39](../../backend/app/main.py#L39), [frontend/src/shared/navigation.ts:3](../../frontend/src/shared/navigation.ts#L3).

### marketing_social_comments — Comentarios sociales, respuestas, reacciones e IA asistida

**Diferencia:** Hay tabla crm_channels.social_comments, ingestión/deduplicación y endpoints activos GET /api/v1/social-comments y POST /{comment_id}/reply con outbox idempotente. Sin embargo Inbox muestra un aviso futuro y no consume esos endpoints. Faltan equivalencias de reacciones, generación de sugerencia IA, contexto de publicación, seguimiento/miniCRM y conversión a Inbox de Scentra.

**Aceptación:** Conectar primero listado/respuesta existentes al Inbox con carga/error/vacío/paginación y estados por envío. Añadir contexto/estado/última respuesta y enlace CRM de identidad explícita sin fusionar por teléfono. Incorporar reacciones y sugerencias IA con capacidad del proveedor verificada, revisión humana y deduplicación; mantener diferencias público/privado, restricciones por canal y callbacks firmados.

**Scentra:** [../saas-version/backend/app_saas/social/router.py:49](../../../saas-version/backend/app_saas/social/router.py#L49), [../saas-version/backend/app_saas/social/router.py:78](../../../saas-version/backend/app_saas/social/router.py#L78), [../saas-version/backend/app_saas/social/router.py:87](../../../saas-version/backend/app_saas/social/router.py#L87), [../saas-version/backend/app_saas/social/router.py:95](../../../saas-version/backend/app_saas/social/router.py#L95), [../saas-version/backend/app_saas/ads/router.py:886](../../../saas-version/backend/app_saas/ads/router.py#L886).
**CRM CBN:** [backend/app/modules/channels/router.py:295](../../backend/app/modules/channels/router.py#L295), [backend/app/modules/channels/workers.py:345](../../backend/app/modules/channels/workers.py#L345), [backend/migrations/011_channels.sql:60](../../backend/migrations/011_channels.sql#L60), [frontend/src/modules/inbox/pages/Inbox.tsx:1111](../../frontend/src/modules/inbox/pages/Inbox.tsx#L1111).

### marketing_receipt_ingestion — Recepción durable, firma y procesamiento de webhooks

**Diferencia:** La composición activa ya delega POST Meta/TikTok en recepción con firma, payload acotado, digest y evento SQL durable; workers reclaman con UPDLOCK/READPAST/ROWLOCK y modelan incertidumbre de envío. Parte de documentación histórica presenta esto como sólo verificación. Faltan aceptación en este entorno y extensión explícita para leads publicitarios; no sustituir todo el receptor con otro paralelo.

**Aceptación:** Inventariar contratos actuales y actualizar documentación histórica. Reutilizar receptor/outbox únicos; añadir normalizadores de leadgen y pruebas de cuenta/identidad/digest, reentrega, firma inválida, caída y recuperación. Probar dos workers en SQL Server 2019 con configuración real de aislamiento antes de certificar concurrencia; no elevar un test mock a aceptación conectada.

**Scentra:** [../saas-version/backend/app_saas/ads/router.py:920](../../../saas-version/backend/app_saas/ads/router.py#L920), [../saas-version/backend/app_saas/workers/ingest.py:1](../../../saas-version/backend/app_saas/workers/ingest.py#L1).
**CRM CBN:** [backend/app/modules/webhooks/api/router.py:137](../../backend/app/modules/webhooks/api/router.py#L137), [backend/app/modules/channels/receipts.py:26](../../backend/app/modules/channels/receipts.py#L26), [backend/app/modules/channels/workers.py:539](../../backend/app/modules/channels/workers.py#L539), [backend/app/modules/channels/workers.py:619](../../backend/app/modules/channels/workers.py#L619).

### marketing_no_billing — Independencia de planes sin perder controles operativos

**Diferencia:** El origen acopla módulos y workers a billing/entitlements/cuotas comerciales. La copia institucional no debe importar esas restricciones ni necesita planes ficticios activos. Sí necesita presupuestos, rate limits, cadencia, consentimiento y controles de permisos.

**Aceptación:** Rastrear cada import/control comercial al portar la función y reemplazar sólo el derecho de plan por configuración institucional explícita. Mantener validación, autorización, límites de proveedor/coste, idempotencia y rate limiting. Verificar que ninguna expiración/suscripción del SaaS pueda detener la instalación institucional y que retirar billing no habilite envíos por accidente.

**Scentra:** [../saas-version/backend/app_saas/campaigns/router.py:10](../../../saas-version/backend/app_saas/campaigns/router.py#L10), [../saas-version/backend/app_saas/broadcasts/router.py:18](../../../saas-version/backend/app_saas/broadcasts/router.py#L18), [../saas-version/backend/app_saas/ads/router.py:12](../../../saas-version/backend/app_saas/ads/router.py#L12), [../saas-version/backend/app_saas/workers/remarketing.py:9](../../../saas-version/backend/app_saas/workers/remarketing.py#L9), [../saas-version/backend/app_saas/workers/triggers.py:14](../../../saas-version/backend/app_saas/workers/triggers.py#L14).
**CRM CBN:** [backend/migrations/018_campaigns.sql:96](../../backend/migrations/018_campaigns.sql#L96), [backend/app/modules/campaigns/service.py:298](../../backend/app/modules/campaigns/service.py#L298), [backend/app/modules/channels/workers.py:481](../../backend/app/modules/channels/workers.py#L481).

## Contrato de paridad Canales y persistencia SQL Server2019 · SQL-C10

Evidencia estructurada: [sql-c10.json](fragments/sql-c10.json).

### channels_sql2019_parity_contract — Contrato versionado para conservar campos/acciones Scentra en Canales, con identidad multicuenta explícita y persistencia SQL2019

**Diferencia:** C9 sigue aceptada sólo para configuración/lectura local. La matriz completa, las24 tablas propuestas y sus78 FK/cinco unidades no están implementadas ni compiladas en SQL2019. OAuth real, secreto/rotación, registro de números, UI completa, ingreso firmado, B015/transporte y proveedores conservan sus puertas de aceptación. Varias cuentas WhatsApp es una ampliación humana CBN, sin afirmar que el backend fuente ya la soporta.

**Aceptación:** Modelo y matriz pinneados:115 contextos de campos/salidas y83 instancias de acciones con etiquetas/tipos/opciones/visibilidad/DTO/destino. PIN6 y current_password efímeros; tokens/secretos tipados AES-GCM con presencia/pistas. OAuth claim único, grant expirable y activos/tokens por sesión/operación/actor; identidad y rutas por IntegrationId. Correcciones revisadas y52 diseños negativos rechazados offline. Partición propuesta50+7+8+24, sin ALTER de tablas protegidas/FK académicas. Compilación/release/mapping/ensayo futuros requieren copia nueva, historia/drift, preservación y reversión; P2 y proveedores se aceptan aparte.

**Scentra:** [../saas-version/frontend/src/App.jsx:9634](../../../saas-version/frontend/src/App.jsx#L9634), [../saas-version/frontend/src/App.jsx:9726](../../../saas-version/frontend/src/App.jsx#L9726), [../saas-version/frontend/src/App.jsx:9793](../../../saas-version/frontend/src/App.jsx#L9793), [../saas-version/frontend/src/App.jsx:9987](../../../saas-version/frontend/src/App.jsx#L9987), [../saas-version/frontend/src/App.jsx:10145](../../../saas-version/frontend/src/App.jsx#L10145), [../saas-version/frontend/src/App.jsx:10350](../../../saas-version/frontend/src/App.jsx#L10350), [../saas-version/backend/app_saas/integrations/schemas.py:25](../../../saas-version/backend/app_saas/integrations/schemas.py#L25), [../saas-version/migrations/001_saas_core.sql:53](../../../saas-version/migrations/001_saas_core.sql#L53), [../saas-version/backend/app_saas/integrations/router.py:1006](../../../saas-version/backend/app_saas/integrations/router.py#L1006).
**CRM CBN:** [docs/adaptation/sql/channels-parity-contract.json:1](../../docs/adaptation/sql/channels-parity-contract.json#L1), [docs/adaptation/sql/channels-ui-parity-contract.json:1](../../docs/adaptation/sql/channels-ui-parity-contract.json#L1), [docs/adaptation/sql/SQL_C10_FIELD_MATRIX.md:1](../../docs/adaptation/sql/SQL_C10_FIELD_MATRIX.md#L1), [docs/adaptation/sql/SQL_C10_CONTRACT.md:1](../../docs/adaptation/sql/SQL_C10_CONTRACT.md#L1), [docs/decisions/ADR-022-channels-parity-contract.md:1](../../docs/decisions/ADR-022-channels-parity-contract.md#L1), [artifacts/sql-c10/source-oauth.json:1](../../artifacts/sql-c10/source-oauth.json#L1), [artifacts/sql-c10/source-tiktok.json:1](../../artifacts/sql-c10/source-tiktok.json#L1), [artifacts/sql-c10/source-webhooks-secrets.json:1](../../artifacts/sql-c10/source-webhooks-secrets.json#L1), [artifacts/sql-c10/review-oauth.json:1](../../artifacts/sql-c10/review-oauth.json#L1), [artifacts/sql-c10/review-tiktok.json:1](../../artifacts/sql-c10/review-tiktok.json#L1), [artifacts/sql-c10/review-webhooks.json:1](../../artifacts/sql-c10/review-webhooks.json#L1).

## Ensayo de esquema de paridad Canales en restauración independiente · SQL-C11

Evidencia estructurada: [sql-c11.json](fragments/sql-c11.json).

### channels_parity_schema_rehearsal — Release de 24 tablas Canales multicuenta con historial, catálogo completo y ensayo físico preservando SIIE/C5/C9

**Diferencia:** Faltan correspondencias y recifrado B011, repositorios, P2/roles, algoritmos OAuth/cuotas/HMAC/AEAD, UI y transporte/proveedores. El inventario de 23 filas heredadas no promovió cuentas ni descifró secretos. SQL2019 institucional sigue pendiente; 4173 C5 y 4175 C9 conservan perfiles y alcances.

**Aceptación:** Release f5200dad… pinneado: cinco unidades APPLIED y NOOP en TRIAL d30e2cb2; 89 tablas totales, 24 nuevas, 343 columnas, 78 FK y 79 CHECK revisados. 39 pruebas offline, 32 negativos y 4 positivos SQL y 21 escenarios de rollback/ACK/drift/recuperación publicados. Diario de 7 a 17 preserva las siete filas originales; Context nuevo tiene una fila. SIIE/C5/C9 mantienen catálogo y datos: 50 tablas y 44.180 filas académicas; 226 filas CRM heredadas = 203 foundation + 23 B011. Nuevas copias, tickets y actor WITHOUT LOGIN, sin CONTROL/db_owner/DML académico, DROP/REPLACE de fuentes ni redirección de runtime. No acepta flujos de servidor, UI o proveedores.

**Scentra:** [docs/adaptation/sql/channels-parity-contract.json:1](../../docs/adaptation/sql/channels-parity-contract.json#L1), [docs/adaptation/sql/channels-ui-parity-contract.json:1](../../docs/adaptation/sql/channels-ui-parity-contract.json#L1), [docs/adaptation/sql/SQL_C10_CONTRACT.md:1](../../docs/adaptation/sql/SQL_C10_CONTRACT.md#L1).
**CRM CBN:** [backend/migrations/cbn_channels_parity_v1/release.json:1](../../backend/migrations/cbn_channels_parity_v1/release.json#L1), [backend/migrations/cbn_channels_parity_v1/CBN-CHP001.sql:1](../../backend/migrations/cbn_channels_parity_v1/CBN-CHP001.sql#L1), [backend/migrations/cbn_channels_parity_v1/CBN-CHP002.sql:1](../../backend/migrations/cbn_channels_parity_v1/CBN-CHP002.sql#L1), [backend/migrations/cbn_channels_parity_v1/CBN-CHP003.sql:1](../../backend/migrations/cbn_channels_parity_v1/CBN-CHP003.sql#L1), [backend/migrations/cbn_channels_parity_v1/CBN-CHP004.sql:1](../../backend/migrations/cbn_channels_parity_v1/CBN-CHP004.sql#L1), [backend/migrations/cbn_channels_parity_v1/CBN-CHP005.sql:1](../../backend/migrations/cbn_channels_parity_v1/CBN-CHP005.sql#L1), [backend/migrations/cbn_channels_parity_v1/expected-shapes.json:1](../../backend/migrations/cbn_channels_parity_v1/expected-shapes.json#L1), [backend/migrations/cbn_channels_parity_v1/constraint-coverage.json:1](../../backend/migrations/cbn_channels_parity_v1/constraint-coverage.json#L1), [backend/migrations/cbn_channels_parity_v1/reviewed-checks.json:1](../../backend/migrations/cbn_channels_parity_v1/reviewed-checks.json#L1), [backend/tools/channels_parity_contract.py:1](../../backend/tools/channels_parity_contract.py#L1), [backend/tools/channels_parity_snapshot.py:1](../../backend/tools/channels_parity_snapshot.py#L1), [backend/tools/channels_parity.py:1](../../backend/tools/channels_parity.py#L1), [artifacts/sql-c11/constraints-result.json:1](../../artifacts/sql-c11/constraints-result.json#L1), [artifacts/sql-c11/faults-result.json:1](../../artifacts/sql-c11/faults-result.json#L1), [artifacts/sql-c11/legacy-readiness.json:1](../../artifacts/sql-c11/legacy-readiness.json#L1), [artifacts/sql-c11/offline-results.xml:1](../../artifacts/sql-c11/offline-results.xml#L1), [artifacts/sql-c11/preservation.json:1](../../artifacts/sql-c11/preservation.json#L1), [artifacts/sql-c11/reference-result.json:1](../../artifacts/sql-c11/reference-result.json#L1), [artifacts/sql-c11/release-check.json:1](../../artifacts/sql-c11/release-check.json#L1), [artifacts/sql-c11/trial-result.json:1](../../artifacts/sql-c11/trial-result.json#L1), [artifacts/sql-c11/review.json:1](../../artifacts/sql-c11/review.json#L1), [backend/tools/rehearse_channels_parity.py:186](../../backend/tools/rehearse_channels_parity.py#L186), [backend/tools/check_channels_parity.py:26](../../backend/tools/check_channels_parity.py#L26), [backend/tools/rehearse_channels_parity_faults.py:28](../../backend/tools/rehearse_channels_parity_faults.py#L28), [backend/tests/test_channels_parity_migrations.py:183](../../backend/tests/test_channels_parity_migrations.py#L183).

## Correspondencias y repositorios/API Canales aislados, con progreso por criterios · SQL-C12

Evidencia estructurada: [sql-c12.json](fragments/sql-c12.json).

### channels_parity_mapping_repositories — Correspondencias B011 y repositorios/API C12 independientes, con claves verificadas y permisos mínimos

**Diferencia:** C12 acepta importación y CRUD/lecturas locales; no UI completa, P2, OAuth, rotación operativa, HMAC público, cuotas, workers, proveedores o SQL2019 institucional. No hay listener nuevo en4176;4173 C5 y4175 C9 mantienen sus alcances.

**Aceptación:** 23 bindings,2 aplicaciones/integraciones importadas draft,2 secretos staged recifrados y cuarentena explícita de recibo/cola; NOOP sin duplicados y con claves/targets validados.47 SQL/API,15 fallos y2 rollbacks;42 nuevas+200 regresiones=242. Cuatro fuentes y65 tablas anteriores intactas; diario17. Perfil/login/ticket propios,68 GRANT y7 DENY runtime; no acceso a raw secrets/body o DML académico.

**Scentra:** [docs/adaptation/sql/channels-parity-contract.json:1](../../docs/adaptation/sql/channels-parity-contract.json#L1), [docs/adaptation/sql/SQL_C11_REVIEW.md:36](../../docs/adaptation/sql/SQL_C11_REVIEW.md#L36).
**CRM CBN:** [artifacts/sql-c12/connected-result.json:1](../../artifacts/sql-c12/connected-result.json#L1), [artifacts/sql-c12/preservation.json:1](../../artifacts/sql-c12/preservation.json#L1), [artifacts/sql-c12/offline-checks.json:1](../../artifacts/sql-c12/offline-checks.json#L1), [docs/adaptation/sql/SQL_C12_REVIEW.md:1](../../docs/adaptation/sql/SQL_C12_REVIEW.md#L1), [docs/decisions/ADR-024-channels-parity-repositories.md:1](../../docs/decisions/ADR-024-channels-parity-repositories.md#L1), [artifacts/sql-c12/review.json:1](../../artifacts/sql-c12/review.json#L1), [backend/app/parity_channels/api.py:1](../../backend/app/parity_channels/api.py#L1), [backend/app/parity_channels/guard.py:1](../../backend/app/parity_channels/guard.py#L1), [backend/app/parity_channels/profile.py:1](../../backend/app/parity_channels/profile.py#L1), [backend/app/parity_channels/policy.py:1](../../backend/app/parity_channels/policy.py#L1), [backend/app/parity_channels/repository.py:1](../../backend/app/parity_channels/repository.py#L1), [backend/app/parity_channels/catalog.py:1](../../backend/app/parity_channels/catalog.py#L1), [backend/tools/parity_mapping.py:1](../../backend/tools/parity_mapping.py#L1), [backend/tools/parity_data.py:1](../../backend/tools/parity_data.py#L1), [backend/tools/rehearse_parity_repositories.py:1](../../backend/tools/rehearse_parity_repositories.py#L1), [backend/tools/check_parity_repositories.py:1](../../backend/tools/check_parity_repositories.py#L1), [backend/tools/fault_parity_repositories.py:1](../../backend/tools/fault_parity_repositories.py#L1), [backend/tests/test_parity_channels.py:1](../../backend/tests/test_parity_channels.py#L1).

### phase_progress_p0 — Reporte de criterios canónicos aceptados en P0

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 5/5 criterios; 100.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p1 — Reporte de criterios canónicos aceptados en P1

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 3/5 criterios; 60.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p2 — Reporte de criterios canónicos aceptados en P2

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/5 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p3 — Reporte de criterios canónicos aceptados en P3

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/5 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p4 — Reporte de criterios canónicos aceptados en P4

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/5 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p5 — Reporte de criterios canónicos aceptados en P5

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/4 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p6 — Reporte de criterios canónicos aceptados en P6

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/5 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p7 — Reporte de criterios canónicos aceptados en P7

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/5 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p8 — Reporte de criterios canónicos aceptados en P8

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/4 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p9 — Reporte de criterios canónicos aceptados en P9

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/4 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p10 — Reporte de criterios canónicos aceptados en P10

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/5 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

### phase_progress_p11 — Reporte de criterios canónicos aceptados en P11

**Diferencia:** El porcentaje cuenta criterios completamente aceptados; no horas, esfuerzo o funcionalidad operativa. Parciales y cierres pendientes no suman crédito.

**Aceptación:** 0/4 criterios; 0.00%. Denominador global fijo56,8accepted; sin promedio global ni crédito por este reporte.

**Scentra:** [docs/SCENTRA_ADAPTATION_ROADMAP.md:1](../../docs/SCENTRA_ADAPTATION_ROADMAP.md#L1).
**CRM CBN:** [docs/adaptation/phase-progress-contract.json:1](../../docs/adaptation/phase-progress-contract.json#L1), [artifacts/sql-c12/progress-review.json:1](../../artifacts/sql-c12/progress-review.json#L1), [backend/tools/check_phase_progress.py:53](../../backend/tools/check_phase_progress.py#L53).

## Preview general separado,recuperación durable local y cierre P1.4 · SQL-C13

Evidencia estructurada: [sql-c13.json](fragments/sql-c13.json).

### general_preview_runtime_contract — Preview general independiente y receta autónoma con persistencia,salud y recuperación local de P1.4

**Diferencia:** P1.close pendiente de motor15/SQL2019 real,contratos/migraciones y reversión. Identidad institucionalP2,paridad funcional completa,OAuth/secretos operativos,proveedores,recepción pública y workers educativos/campañas conservan sus puertas. Canales aquí sólolectura;C9 mantiene su propia interfaz4175.

**Aceptación:** CopiaC13 1f10a824 desdeC12 conperfil/login/ticket propios yTLS;corefoundation editable yCanales seguro,14secciones conpendientes. Imagen oficial autónoma sinHMR/binds,UID10001/RO,volúmenes IA/media,perfil persistente ycompatibilidad imagenanterior.265backend/52frontend,25HTTP,15SQL,16Docker/worker;12observacionescompactas yentrega80. Cincofuentes y50tablas/44180filas académicas,diario17 intactos. P1.4accepted1;P1=4/5=80 y9/56criterios,no%horas/funcionalidad.

**Scentra:** .
**CRM CBN:** [backend/app/general_preview/api.py:1](../../backend/app/general_preview/api.py#L1), [backend/app/general_preview/store.py:1](../../backend/app/general_preview/store.py#L1), [backend/app/general_preview/worker.py:1](../../backend/app/general_preview/worker.py#L1), [backend/app/general_preview/health.py:1](../../backend/app/general_preview/health.py#L1), [backend/tools/prepare_general_preview.py:1](../../backend/tools/prepare_general_preview.py#L1), [backend/tools/check_general_http.py:1](../../backend/tools/check_general_http.py#L1), [backend/tools/audit_general_preview.py:1](../../backend/tools/audit_general_preview.py#L1), [backend/tools/check_general_progress.py:1](../../backend/tools/check_general_progress.py#L1), [backend/tests/test_general_preview.py:1](../../backend/tests/test_general_preview.py#L1), [frontend/src/general/GeneralPreview.tsx:1](../../frontend/src/general/GeneralPreview.tsx#L1), [frontend/src/general/main.tsx:1](../../frontend/src/general/main.tsx#L1), [frontend/src/general/general.test.tsx:1](../../frontend/src/general/general.test.tsx#L1), [frontend/src/general/general.css:1](../../frontend/src/general/general.css#L1), [frontend/general.html:1](../../frontend/general.html#L1), [frontend/vite.general.config.ts:1](../../frontend/vite.general.config.ts#L1), [docker/Dockerfile.general:1](../../docker/Dockerfile.general#L1), [docker/Dockerfile.general.dockerignore:1](../../docker/Dockerfile.general.dockerignore#L1), [docker/general-start.sh:1](../../docker/general-start.sh#L1), [docker/nginx.general.conf:1](../../docker/nginx.general.conf#L1), [compose.general.yaml:1](../../compose.general.yaml#L1), [docs/adaptation/sql/SQL_C13_REVIEW.md:1](../../docs/adaptation/sql/SQL_C13_REVIEW.md#L1), [docs/decisions/ADR-025-general-preview-and-docker-sprint.md:1](../../docs/decisions/ADR-025-general-preview-and-docker-sprint.md#L1), [docs/adaptation/sql/SQL_C13_BINDINGS.md:1](../../docs/adaptation/sql/SQL_C13_BINDINGS.md#L1), [docs/adaptation/sql/academic-bindings-c13.json:1](../../docs/adaptation/sql/academic-bindings-c13.json#L1), [artifacts/sql-c13/offline-checks.json:1](../../artifacts/sql-c13/offline-checks.json#L1), [artifacts/sql-c13/build-materials.json:1](../../artifacts/sql-c13/build-materials.json#L1), [artifacts/sql-c13/runtime-drill.json:1](../../artifacts/sql-c13/runtime-drill.json#L1), [artifacts/sql-c13/http-checks.json:1](../../artifacts/sql-c13/http-checks.json#L1), [artifacts/sql-c13/sql-audit.json:1](../../artifacts/sql-c13/sql-audit.json#L1), [artifacts/sql-c13/browser-checks.json:1](../../artifacts/sql-c13/browser-checks.json#L1), [artifacts/sql-c13/delivery.json:1](../../artifacts/sql-c13/delivery.json#L1), [artifacts/sql-c13/previews.json:1](../../artifacts/sql-c13/previews.json#L1), [artifacts/sql-c13/progress-review.json:1](../../artifacts/sql-c13/progress-review.json#L1), [artifacts/sql-c13/review.json:1](../../artifacts/sql-c13/review.json#L1).

## Repositorios CRM en restauraciÃƒÆ’Ã‚Â³n Ãƒâ€šÃ‚Â· SQL-C4

Evidencia estructurada: [sql-c4.json](fragments/sql-c4.json).

## Interfaz por capacidades en restauración · SQL-C5

Evidencia estructurada: [sql-c5.json](fragments/sql-c5.json).

## Diseño de extensión CRM y partición por objetos · SQL-C6

Evidencia estructurada: [sql-c6.json](fragments/sql-c6.json).

### foundation_extension_contract — Contrato de extensión por objetos que preserve CRM poblado y SIIE

**Diferencia:** El lector y guard aceptados sólo cubren siete tablas foundation y separan el resto por complemento de esquemas. Ampliar su lista o ignorar prefijos ocultaría objetos desconocidos y alteraría evidencia congelada; falta el contrato versionado de extensión y su ensayo.

**Aceptación:** Pendiente SQL-C7: lector/guard/migrador nuevos, partición exacta 50 académicas + 7 foundation + 8 extensión, preservación del CRM poblado y diario, permisos acotados, snapshots revisados antes de otra restauración de ensayo y pruebas de drift/concurrencia/recuperación. Runtime/UI se aceptarán aparte en C8. El verificador C6 sólo valida el diseño offline.

**Scentra:** .
**CRM CBN:** [backend/app/foundation.py:155](../../backend/app/foundation.py#L155), [backend/tools/foundation_snapshot.py:51](../../backend/tools/foundation_snapshot.py#L51), [docs/adaptation/sql/check_c6_plan.py:27](../../docs/adaptation/sql/check_c6_plan.py#L27).

## Extensión CRM ensayada con partición exacta e historia conservada · SQL-C7

Evidencia estructurada: [sql-c7.json](fragments/sql-c7.json).

### foundation_extension_rehearsal — Ensayo versionado de extensión CRM que preserve SIIE, CRM poblado e historia

**Diferencia:** El alcance estructural B011 está aceptado únicamente en restauraciones independientes. El lector administrativo C7 exige CONTROL y compara las 199 filas CRM previas; no es un guard para datos mutables ni una autorización para ampliar el perfil C5. Faltan consumidores, principal y guard de runtime propios en C8 y aceptación institucional en SQL2019.

**Aceptación:** C7 v2: APPLIED+NOOP en otra restauración del C5 poblado; partición exacta 50+7+8; ocho tablas nuevas vacías; prefijo original de cinco filas conservado y diario final de siete; 119 pytest y 51 checks conectados sin pendientes; v1 retirada sin editar. Mantener los contratos históricos y fuente/C5 intactos. C8 debe probar repositorios y capacidades con perfil/ACL/guard propios, sin reutilizar el lector inmutable administrativo ni redirigir el ticket C4.

**Scentra:** .
**CRM CBN:** [backend/tools/crm_extension_snapshot_v2.py:36](../../backend/tools/crm_extension_snapshot_v2.py#L36), [backend/tools/crm_extension_v2.py:67](../../backend/tools/crm_extension_v2.py#L67), [backend/tools/crm_extension_contract.py:57](../../backend/tools/crm_extension_contract.py#L57), [backend/tools/rehearse_crm_extension_v2.py:396](../../backend/tools/rehearse_crm_extension_v2.py#L396), [backend/tools/crm_extension_checks_v2.py:550](../../backend/tools/crm_extension_checks_v2.py#L550), [backend/tests/test_crm_extension.py:349](../../backend/tests/test_crm_extension.py#L349), [backend/tests/test_crm_extension_v2.py:20](../../backend/tests/test_crm_extension_v2.py#L20), [backend/tools/historical_checkpoint.py:100](../../backend/tools/historical_checkpoint.py#L100).

## Repositorios de Canales y API local sobre copia independiente · SQL-C8

Evidencia estructurada: [sql-c8.json](fragments/sql-c8.json).

### channels_repository_contract — Repositorios de Canales con perfil propio, guard mutable y API local acotada

**Diferencia:** B011 ya tiene repositorios ensayados en una copia C8 independiente. La UI de Canales y su integración con CRM/Inbox requieren otro corte y permisos explícitos; enqueue_message sigue dependiendo de MessageRoute/B015. La aceptación local con SQL2022Express no acredita SQL2019 institucional ni proveedores.

**Aceptación:** C8: ocho tablas de Canales ejercitadas, 189 pruebas offline y 38 comprobaciones conectadas; perfil/login/AES/ticket independientes; catálogo completo equivalente entre administración/runtime; 33 GRANT y siete DENY sin CONTROL ni INSERT en cola. Diario heredado de siete filas y 199 registros CRM originales conservados; crecimiento sintético a 203 registros sin invalidar el guard. API sólo configuración sin secretos y lecturas locales, sin workers/proveedores. C9 debe aceptar UI/capacidades y revisar ACL en otra composición si amplía el alcance; C4/C5/C7 e historia permanecen intactos.

**Scentra:** .
**CRM CBN:** [backend/app/channels_catalog.py:10](../../backend/app/channels_catalog.py#L10), [backend/app/channels_contract.py:179](../../backend/app/channels_contract.py#L179), [backend/app/channels_profile.py:11](../../backend/app/channels_profile.py#L11), [backend/app/channels_app.py:25](../../backend/app/channels_app.py#L25), [backend/app/modules/channels/storage.py:194](../../backend/app/modules/channels/storage.py#L194), [backend/app/modules/channels/router.py:180](../../backend/app/modules/channels/router.py#L180), [backend/app/modules/channels/workers.py:170](../../backend/app/modules/channels/workers.py#L170), [backend/app/modules/channels/receipts.py:26](../../backend/app/modules/channels/receipts.py#L26), [backend/app/modules/ai/api/router.py:44](../../backend/app/modules/ai/api/router.py#L44), [backend/tools/rehearse_channels.py:213](../../backend/tools/rehearse_channels.py#L213), [backend/tools/check_channels.py:587](../../backend/tools/check_channels.py#L587), [backend/tests/test_channels_runtime.py:22](../../backend/tests/test_channels_runtime.py#L22), [backend/tools/historical_checkpoint.py:694](../../backend/tools/historical_checkpoint.py#L694), [artifacts/sql-c8/final-result.json:1](../../artifacts/sql-c8/final-result.json#L1).

## Paridad funcional de Canales Scentra → CBN · precisión durante SQL-C9

Evidencia estructurada: [sql-c9-scentra-parity.json](fragments/sql-c9-scentra-parity.json).

### channels_scentra_parity — Funciones y organización de Canales iguales a Scentra, con persistencia SQL Server y estilo CBN

**Diferencia:** C9 ya organiza Meta WhatsApp Cloud, verificación de número, Instagram Business, Facebook Messenger, TikTok y Webhooks en grupos verticales; Facebook/comentarios conserva su subconfiguración SQL. Sigue ofreciendo sólo configuración/lectura. Faltan gestión y rotación de secretos con pistas protegidas, sincronización/selección de números y PIN6, OAuth IG/FB con descubrimiento/selección de activos y diagnóstico, controles completos de TikTok (review, productos/scopes, eventos, rollout, cuotas y flags), gestión de endpoints/HMAC/verify token y procesamiento de eventos. C8 ya tiene cifrado AES-GCM ensayado; la brecha es su integración segura y funcional. El modelo Account por Channel, diez campos del DTO y cuatro tipos genéricos de secretos no acreditan equivalencia con las integraciones y controles de Scentra.

**Aceptación:** Conservar las mismas funciones, agrupación, campos, estados, validaciones y flujos observables de Scentra; mantener estilo CBN y sustituir PostgreSQL por SQL Server. Portar contratos/datos/permisos y probarlos en otra restauración, con secretos cifrados, pistas sin valor completo, errores/reintentos/concurrencia y aceptación en navegador. Revisar identidad/cardinalidad de integraciones, tipos de secretos y DTO TikTok; no añadir inputs que el backend descarta. Stripe/billing y comercio excluidos por alcance educativo no se copian; las cuotas operativas TikTok sí se conservan. La operación real de proveedores y SQL2019 institucional requieren sus puertas de aceptación; esta matriz no activa proveedores, webhooks, workers o transporte ni amplía tickets.

**Scentra:** [../saas-version/frontend/src/App.jsx:9610](../../../saas-version/frontend/src/App.jsx#L9610), [../saas-version/frontend/src/App.jsx:9619](../../../saas-version/frontend/src/App.jsx#L9619), [../saas-version/frontend/src/App.jsx:9687](../../../saas-version/frontend/src/App.jsx#L9687), [../saas-version/frontend/src/App.jsx:9715](../../../saas-version/frontend/src/App.jsx#L9715), [../saas-version/frontend/src/App.jsx:9788](../../../saas-version/frontend/src/App.jsx#L9788), [../saas-version/frontend/src/App.jsx:9982](../../../saas-version/frontend/src/App.jsx#L9982), [../saas-version/frontend/src/App.jsx:10174](../../../saas-version/frontend/src/App.jsx#L10174), [../saas-version/frontend/src/App.jsx:10200](../../../saas-version/frontend/src/App.jsx#L10200), [../saas-version/frontend/src/App.jsx:10350](../../../saas-version/frontend/src/App.jsx#L10350), [../saas-version/frontend/src/App.jsx:10368](../../../saas-version/frontend/src/App.jsx#L10368), [../saas-version/frontend/src/App.jsx:10424](../../../saas-version/frontend/src/App.jsx#L10424).
**CRM CBN:** [frontend/src/features/ChannelsUiPanel.tsx:37](../../frontend/src/features/ChannelsUiPanel.tsx#L37), [frontend/src/features/ChannelsUiPanel.tsx:70](../../frontend/src/features/ChannelsUiPanel.tsx#L70), [backend/app/channels_ui_app.py:16](../../backend/app/channels_ui_app.py#L16), [backend/app/channels_ui_app.py:29](../../backend/app/channels_ui_app.py#L29), [backend/app/modules/channels/router.py:16](../../backend/app/modules/channels/router.py#L16), [backend/app/modules/channels/storage.py:15](../../backend/app/modules/channels/storage.py#L15), [backend/app/modules/channels/storage.py:112](../../backend/app/modules/channels/storage.py#L112), [backend/migrations/cbn_channels_v2/B011_channels.sql:14](../../backend/migrations/cbn_channels_v2/B011_channels.sql#L14), [docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md:3](../../docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md#L3), [docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md:24](../../docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md#L24), [docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md:26](../../docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md#L26).

## Interfaz local de Canales por capacidades y permisos por columna · SQL-C9

Evidencia estructurada: [sql-c9.json](fragments/sql-c9.json).

### channels_capability_ui — UI Glass de Canales por capacidades con perfil propio y lectura de credenciales limitada a columnas

**Diferencia:** La composición C9 permite editar configuración y consultar etapas, comentarios y actividad local. Las acciones de proveedores, credenciales, recepción pública, respuesta y reintentos siguen bloqueadas; CRM/Inbox requieren otro alcance y permisos. B015/MessageRoute, transporte, SQL2019 institucional y paridad general permanecen pendientes. La agrupación visual ahora sigue las seis secciones Scentra; el fragmento sql-c9-scentra-parity.json registra que OAuth, secretos, números, TikTok completo y webhooks siguen sin paridad funcional completa.

**Aceptación:** Copia C9 independiente con perfil/login/ticket propios, sin clave de Canales ni DML CRM. Manifiesto v2 estricto antes del montaje; shell separada evita hooks CRM/Inbox. Sólo Account SELECT/INSERT/UPDATE, Audit INSERT y lecturas acotadas; Credential permite SELECT únicamente de Channel/Kind. Borradores y revisión se conservan ante error y usan readback ante resultado incierto. Evidencia pública actual: 244 backend (55 C9), 42 frontend (30 C9) y 35 checks SQL/API, con preservación de academia/C8/C5 y diario. Compose aislado loopback4175; C5 4173 conserva su contrato y origen. La aceptación general o de proveedores no se deriva de estas pruebas.

**Scentra:** .
**CRM CBN:** [backend/app/channels_ui_contract.py:90](../../backend/app/channels_ui_contract.py#L90), [backend/app/channels_ui_profile.py:11](../../backend/app/channels_ui_profile.py#L11), [backend/app/channels_ui_app.py:29](../../backend/app/channels_ui_app.py#L29), [backend/app/channels_catalog.py:10](../../backend/app/channels_catalog.py#L10), [frontend/src/shared/runtimeCapabilities.tsx:75](../../frontend/src/shared/runtimeCapabilities.tsx#L75), [frontend/src/App.tsx:713](../../frontend/src/App.tsx#L713), [frontend/src/features/ChannelsWorkspace.tsx:16](../../frontend/src/features/ChannelsWorkspace.tsx#L16), [frontend/src/features/ChannelsUiPanel.tsx:186](../../frontend/src/features/ChannelsUiPanel.tsx#L186), [frontend/src/test/channelsUi.test.tsx:166](../../frontend/src/test/channelsUi.test.tsx#L166), [backend/tests/test_channels_ui_runtime.py:22](../../backend/tests/test_channels_ui_runtime.py#L22), [backend/tools/rehearse_channels_ui.py:67](../../backend/tools/rehearse_channels_ui.py#L67), [backend/tools/check_channels_ui.py:30](../../backend/tools/check_channels_ui.py#L30), [compose.channels-ui.yaml:1](../../compose.channels-ui.yaml#L1), [docker/channels-ui-start.sh:1](../../docker/channels-ui-start.sh#L1), [docker/nginx.channels-ui.conf:16](../../docker/nginx.channels-ui.conf#L16), [artifacts/sql-c9/backend-results.xml:1](../../artifacts/sql-c9/backend-results.xml#L1), [artifacts/sql-c9/frontend-results.xml:2](../../artifacts/sql-c9/frontend-results.xml#L2), [artifacts/sql-c9/connected-checks.json:1](../../artifacts/sql-c9/connected-checks.json#L1), [artifacts/sql-c9/preservation-result.json:1](../../artifacts/sql-c9/preservation-result.json#L1).

## HORARIOSSIIE: comparación y plan CRM condicionado

Evidencia estructurada: [sql_c2.json](fragments/sql_c2.json).

## SQL-C3: fundamento ensayado sin aplicar a la fuente

Evidencia estructurada: [sql_c3.json](fragments/sql_c3.json).
