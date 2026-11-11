# Roadmap de implementación con cierre comprobable

## Estado actual — admisiones con datos reales, 2026-10-15

La integración local ya persiste Clientes/Inbox y ahora añade Admisiones: listado/ficha por período de aspiración, coincidencias históricas de estudiantes y seguimiento CRM propio. [Informe actual](reports/admissions-local.md). El siguiente corte es alta/actualización de aspirantes por contrato SIIE; después formulario y revisión académica conectados, canales, IA informada y operación compartida. Auth/RBAC preceden exposición compartida; no bloquean el desarrollo ya autorizado en la copia local.

Las secciones posteriores son historial del prototipo y no sustituyen este estado.

## Corte local cerrado — 2026-10-15

Por confirmación expresa del propietario se completó el **backend local sintético de Clientes**: listado/búsqueda, creación, consulta, edición y reset temporal del servidor, coherentes con Inbox y sin SQL. Cerrado al 100 % de este alcance local con 1529 pruebas backend, 202 frontend, 54 comprobaciones HTTP/runtime y navegador escritorio/móvil. No se asigna una fase 7 ni se transforma el corte en persistencia de negocio. [Aceptación y evidencia](reports/clients-backend-local.md). La fase de seguridad queda entre las últimas incorporaciones y no se inicia hasta instrucción expresa; se mantienen las restricciones existentes. El siguiente alcance requiere selección del propietario. Este cierre no autoriza publicación o despliegue remoto.

## Estado integrado vigente — 2026-10-14

Las fases 0, 2, 3, 4, 5 y 6 tienen cortes **locales** presentes en la rama integrada; el corte 6 es ensayo operativo sintético, no piloto productivo. V6 e IA avanzada conviven con catálogos SQL de lectura optativa. [Informe vigente](reports/branch-integration.md); [formulario](reports/phase-4-local.md), [revisión](reports/phase-5-local.md), [operación](reports/phase-6-local.md), [contratos](reports/local-schema-definitions.md) y [catálogos SQL](reports/programs-local-api.md).

Secuencia inmediata autorizada: consolidar y comprobar fuentes → preparar Docker para revisión privada → resolver conectividad SQL externa e identidad/permisos antes de exposición compartida. Ningún contenedor necesita duplicar la autoridad transaccional SIIE. Las pruebas locales/TLS por memoria compartida no acreditan acceso remoto desde Oracle.

Las secciones siguientes conservan el roadmap histórico de diseño y sus puertas. Sus menciones a fases todavía no iniciadas corresponden a ese snapshot; la preparación Docker no cierra fase 1, aceptación conectada, piloto, producción ni autorización de escrituras.

## Roadmap histórico y puertas de aceptación

**Actualización:** 2026-10-14, America/Bogota. **Estado real: fases 0, 2 y 3 completadas al 100% de sus alcances LOCALES**, con checks y navegador comprobados; [informe 2](reports/phase-2-local.md) y [histórico 0](reports/phase-0.md). ADR-001/002/003 aceptados; fase 1 diferida al final del diseño funcional local, obligatoria antes de conexiones/datos reales/entorno compartido. Fase 3 local cerrada bajo [ADR-004](decisions/ADR-004-local-phase-three-workflows.md), con 60 tests/checks, navegador y 36/36 hashes intactos en [informe 3](reports/phase-3-local.md); su aceptación es independiente de los adelantos de fase 2. Sigue 4 local, todavía no iniciada. FastAPI/React/Celery/Redis conservan el stack general; diseño definitivo y contratos conectados pendientes. Esta fase no autoriza producción, cuentas o despliegues; Git sigue su política de autorización separada.

## Ruta inmediata y criterio de 100%

1. Fase 0 local cerrada con ADR-002, herramientas fijadas y checklist/evidencia completos.
2. [ADR-003](decisions/ADR-003-local-phase-two-sequence.md) acepta implementar **fase 2 local**: Clientes configurables, mini CRM conversacional y comentarios sociales. [Informe de fase 2 local](reports/phase-2-local.md).
3. Continuar el diseño funcional local en orden **0 → 2 → 3 → 4 → 5 (revisión sin integración)** y expansiones locales expresamente seleccionadas. Ninguna siguiente fase se inicia por el solo cierre de la anterior.
4. **Fase 1 al final del desarrollo local**, antes de DB/API, datos reales, conexión social/IA, entorno compartido, despliegue o piloto. Después se valida la aceptación conectada de 2–5 y se habilita 6 solo con autorización específica. La seguridad se difiere como implementación, no se elimina.

**100% de una fase** significa que todos sus criterios acordados están satisfechos y comprobados, las aprobaciones aplicables están registradas y no quedan bloqueos de su alcance. No significa todo el proyecto implementado. No se publicará un porcentaje estimado para suplir evidencia.

## Puertas previas a fase 0 — alcance revisado y aceptado

[ADR-001](decisions/ADR-001-skeleton-architecture.md) acepta arquitectura base; [ADR-002](decisions/ADR-002-local-functional-skeleton.md) autoriza skeleton y diseño funcional **locales**, elección mínima de herramientas compatibles y diferimiento de inventario SIIE/diseño definitivo. La interfaz usa solo fixtures/estado temporal y no depende del backend. No hay integración DB/API de negocio.

P-001, responsables/reglas restantes P-002, P-003/P-015/P-018, P-017/P-026 permanecen abiertos antes de funciones conectadas en fase 1 o su capacidad; P-004 queda parcial para herramientas locales, sin driver o identidad real. P-005 precede todo dato/persona real. P-021/P-022/P-027 necesitan contratos antes de funcionalidades conectadas; el prototipo no resuelve diferencias de referencia. P-016 antes de texto IA en fase 3. Git sigue su política de autorización separada; producción no está autorizada por esta fase.

## Secuencia de implementación

Fases 0 y 2 **completadas al 100% de sus alcances LOCALES**: fase 2 tiene 40 tests/checks y navegador escritorio/móvil comprobados en el [informe](reports/phase-2-local.md). Fase 1 diferida y funcionalidades conectadas no iniciadas. Fase 3 local cerrada con aceptación propia ADR-004, 60 tests/checks, navegador y 36/36 hashes intactos. Fase 4 local es la siguiente y no ha iniciado. La numeración conserva identidad, no impone el orden de ejecución; aceptación conectada independiente.

| Fase | Entrega y módulos | Entrada necesaria | Salida comprobable y siguiente fase |
|---|---|---|---|
| **0 — Skeleton local** | Shell React, salud FastAPI y flujos demostrativos. | ADR-001/002. | Cerrada local; sigue 2 local. No acredita integración. |
| **2 — Clientes + mini CRM + comentarios locales** | Ficha/lista/búsqueda, pipeline configurable, etiquetas, tipo/intereses y ocho tipos de campos. Estado compartido Inbox, contexto de temperatura/abandono con evidencia, cuatro canales ficticios; comentarios Facebook/Instagram/TikTok. | Fase 0 y autorización ADR-003; solo fixtures. | Checklist local abajo. Sigue 3 local. **Diferido:** validación servidor, conflictos, paginación SQL/permisos, duplicados y baja auditada; requieren 1 y P-027. |
| **3 — Inbox y asistente funcional local** | Estados Abierta/En espera/Cerrada, asignación ficticia, prioridad/filtros, tareas/timeline, Asistente/IA compartidos y plantilla revisada con vinculación contacto/contexto/control/configuración. Sin envíos/modelo. | Fase 2 local y ADR-004; solo fixtures/estado temporal. | Cerrada al 100% LOCAL: 60 tests/checks y navegador; sigue 4 local, no iniciada. **Conectado, después de 1:** UN adapter texto, WhatsApp sandbox, otros canales según discovery; P-005/007/010/016/017/021/022/024/025/027/029/030. Firma/replay, inbox/outbox, envío incierto/recovery/handoff concurrente y proveedor requieren sus propias pruebas. |
| **4 — Formulario de aspirante** | Diseño local de captura/validación y estados, sin registro real. | Fase 3 local y campos aceptados. | Pruebas locales de errores/confirmación/escritorio/móvil; sigue 5 local. **Conectado, después de 1:** token de uso único/consumo atómico/rate limits/idempotencia/audit y persistencia `CRM_` solo con DDL test autorizado. |
| **5 — Revisión académica humana** | Flujo local de revisar/observar/rechazar con fixtures; integración separada. | Fase 4 local y alcance aceptado. | Cierre local, después 1 o expansiones locales seleccionadas. **Core:** P-011, DBA/autorización específica, transacciones/carreras/rollback/restauración/carga fuera de producción; nunca matrícula automática. Sin esa prueba no se cierra integración. |
| **1 — Base segura y contratos de datos (última del corte local)** | Auth/permisos/sesiones/2FA, auditoría, secretos/ambientes y contratos SQL/API. | Diseño funcional local revisado; P-001/002/004/005/006/017/026; acceso/DDL test autorizado. Git/CI P-009 aparte. | Negativos, revocación/invitaciones/último admin/perfil, TLS/aislamiento/redacción, contratos y reversión probados. **Obligatoria antes de cualquier conexión/dato real/entorno compartido.** Sigue aceptación conectada de 2–5, no publicación automática. |
| **6 — Piloto y operación** | Volumen acotado, soporte/métricas, recuperación/rotación/exportación/baja. No piloto local ficticiamente operativo. | Fase 1 y aceptación conectada aplicable; P-012/019/025/026 y autorización de piloto/despliegue. | SLAs/budgets/RPO/RTO/runbooks/rollback/pausa probados en ambiente autorizado. Build no acredita operación; sigue expansión seleccionada. |
| **7 — Expansiones condicionadas** | Voz, recordatorios, RAG/memoria, retención, corporativo y CRM de creadores; cortes independientes abajo. | Piloto aceptado y necesidad/diseño/datos/coste/autorizaciones de cada corte. | Aceptación y reporte propios; solo los cortes seleccionados son alcance comprometido. No bloquean el corte base. |

## Fase 0 — checklist del skeleton

**Objetivo:** base local ejecutable y verificable, no doce módulos ficticiamente terminados. **Estado:** completada al 100% del alcance local aceptado ADR-002; evidencia de checks, HTTP y navegador en el [informe de fase 0](reports/phase-0.md). No aprobación visual humana ni integración real.

- [x] Alcance y aprobación local ADR-001/002, herramientas/versiones, comandos y responsabilidad técnica local registrados; roles/aprobaciones conectados pendientes para sus fases.
- [x] Backend FastAPI mínimo arranca reproduciblemente. Health de proceso separado de readiness: no anunciar SQL Server, Redis, auth o proveedores conectados si no se probaron. Dependencia ausente aparece no configurada/no verificada.
- [x] Límites dominio/aplicación/adaptadores/entradas para responsabilidades reales; sin capas vacías, SQL/LLM en rutas o abstracciones especulativas.
- [x] React arranca con shell/navegación y rutas mínimas acordadas; otras rutas son superficies de diseño rotuladas; los demostradores guardan exclusivamente estado temporal identificado y nunca aparentan guardar/enviar a sistemas reales. Acceso simulado no es autenticación.
- [x] Fuente única de tokens/componentes y estados mínimos; shell validado por teclado y escritorio/móvil. Tema claro/oscuro e idioma español neutral provisionales para revisión según ADR-002, no aprobación visual definitiva.
- [x] Configuración local/plantillas ficticias sin secretos/defaults productivos; sin llamadas DB/proveedor, DDL/cuentas reales. Errores/logs sin datos sensibles.
- [x] Manifiestos/lockfiles fijan lo aprobado; instrucciones saneadas reproducen instalación/arranque/checks sin dependencias ocultas. No afirmar CI/repositorio remoto.
- [x] Tras normalización, lint/tipos/pruebas/build acordados ejecutados con resultado/entorno; pruebas mínimas de health y shell/rutas. Cambio posterior renueva evidencia afectada.
- [x] Navegador confirma navegación, ruta desconocida, estados visibles y shell responsive con evidencia sintética. Build no sustituye navegador ni prueba módulos completos.
- [x] Cierre/pendientes actualizados: qué se hizo, evidencia, no comprobado y siguiente unidad; la secuencia vigente ADR-003 pasa a fase 2 local y difiere 1.

**No objetivos:** DB/core, auth real, IA/canales/envíos, migraciones, workers, pagos, media/voz, RAG, cloud/despliegue. Celery/Redis permanecen confirmados en el stack, pero se incorporan al flujo durable de fase 3; skeleton no instala cola/vault/cloud por anticipación. Store seguro/identidad reales pertenecen a fase 1 tras decidir su diseño. Git/CI no son requisito del arranque local ni están autorizados por este encargo.

## Fase 2 — aceptación LOCAL y aceptación conectada diferida

**Estado: completada al 100% LOCAL**, bajo ADR-003. Todos los criterios locales siguientes están comprobados mediante 40 tests/checks y navegador escritorio/móvil/claro/oscuro/teclado; 30/30 hashes frontend intactos. Resultados, capturas y checklist íntegro en [informe 2](reports/phase-2-local.md). La demo no prueba la réplica exacta de Scentra ni requisitos conectados originales.

- Configuración única en App: etapas con clave única/probabilidad 0–100, etiquetas reutilizables con conteo/filtro, campos Text/Number/List/Date/Boolean/Email/Phone/URL con validación y desactivación sin borrar valores.
- Crear/editar/cancelar fichas ficticias; nombre o identificador obligatorio, tipo/intereses libres y vínculo Clientes/Inbox sin duplicar estado.
- Mensajes de demostración en WhatsApp/Facebook/Instagram/TikTok, con filtro y canal visibles. Un hilo por cliente en la demo, sin resolución de identidad omnicanal.
- Mini CRM: Frío/Tibio/Caliente/Sin evidencia, posible abandono, contexto/evidencia/sugerencia humana. Análisis determinista explícitamente identificado como demo, no modelo entrenado. Sin porcentaje de conversión; espera sintética solo con metadata válida, nunca SLA real.
- Comentarios separados de mensajes para Facebook/Instagram/TikTok: publicación contextual, filtros, respuesta local, estado y borradores separados por registro y modo. Respuesta marcada **No publicada · Solo local**.
- Reset/recarga descartan la configuración, valores, hilos, comentarios y borradores; claro/oscuro, teclado, escritorio/móvil; checks sin business fetch/storage/envío.

**No se cierran con esta entrega:** SQL/API/persistencia/permiso/autenticación/seguridad operativa, proveedor IA/modelo/scoring calibrado, conectores/publicación/media, SLA, duplicados/fusión/baja, pagos/matrículas. P-027/029/030 mantienen la aceptación conectada.

## Fase 3 — aceptación LOCAL

**Estado: completada al 100% LOCAL** bajo ADR-004; 60 tests/checks, navegador escritorio/móvil/claro/oscuro/teclado y 36/36 hashes source intactos acreditados en [informe 3](reports/phase-3-local.md). No duplica entregas de fase 2 ni acredita aceptación conectada.

- [x] Estado/asignación/prioridad por hilo y filtros; cierre bloquea mensajes/plantillas hasta reapertura.
- [x] Tareas humanas con validación, completar/cancelar; fecha/hora opcional no programa recordatorios.
- [x] Timeline temporal ordenado de acciones explícitas y hora real; no auditoría persistida ni recibos sociales.
- [x] Configuración única Asistente/IA, guardar/descartar/revisar solo demo, proveedor/modelo sin configurar.
- [x] Plantilla determinista identificada, edición/revisión/copia humana; acción separada añade solo al hilo local. Target/contexto/configuración/control invalidan derivados.
- [x] Canales confirmados sin conectar y diagnóstico de contadores temporales; Clientes/mini CRM/Comentarios preservados.
- [x] Checks finales sobre source normalizado y congelado: formato/lint/tipos/build y 60 tests; resultado exacto en informe.
- [x] Navegador escritorio/móvil/claro/oscuro/teclado con evidencia y límites; cierre/pendientes actualizados.

Después sigue **4 local — formulario de aspirante**, por autorización específica. Fase 1 y aceptación conectada permanecen obligatorias antes de datos reales/DB/API/modelos/entorno compartido. P-027/029/030 y contratos de asistentes/tareas/handoff no se cierran por estas pruebas.

## Paridad documental por capacidad

Referencias: [Clientes](design/settings-reference/scentra_clientes_especificacion.md), [CRM de creadores](design/settings-reference/scentra_crm_subpestanas_especificacion.md), [Inbox](design/settings-reference/scentra_inbox_especificacion.md) y [adaptación de Ajustes](design/settings-specification.md). Se planifica replicar comportamientos pertinentes bajo invariantes CRM CBN. **Clientes y CRM de creadores son capacidades distintas**; creadores no es M-03 ni amplía por inferencia el inventario histórico de doce módulos propuestos.

P-027 debe producir antes de cada capacidad una matriz acción/campo/estado/permiso con fuente, aceptación CRM, contrato backend, casos y evidencia. Separar **documentado en referencia**, **inferido/propuesto**, **aceptado** y **probado en CRM**. Los autores no verificaron registros dinámicos/operaciones completas; MD/etiquetas estáticas no prueban backend, concurrencia ni aislamiento.

| Referencia / capacidad | Destino previsto | Decisión o evidencia que falta |
|---|---|---|
| Clientes: ficha/búsqueda, etapas/etiquetas/campos, abrir Inbox | Fase 2, contrato único compartido con 3. | Normalización/duplicados, paginación/permisos/etapas. `Tipo` es texto libre en Clientes y lista cerrada en Inbox; pago `Devuelto` existe en Clientes pero no en Inbox. Resolver sin pérdida de datos; no escoger enum unilateralmente. |
| Clientes: baja/configuración/pagos | Baja lógica 2 solo aprobada; configuración pertinente sin presets Industria; pagos condicionados. | Reauth/audit/cancelación/retención y alcance de baja. Cobros Stay/marcar pagado/estados financieros no autorizan pagos SIIE ni reconciliación: contrato propio. |
| Inbox: mensajes/filtros, asignación/handoff, ficha, lectura/avisos/sonido, notificaciones internas/eventos/timeline/tareas | Texto 3; avisos según capacidad/permisos browser, tareas acotadas si aceptadas, programación/envío 7B. | Permisos/propiedad/lectura/SLA, orden/sincronización/paginación/durabilidad. Notificación interna no es mensaje al contacto. Scoring/temperatura/conversión/abandono/fusión necesitan reglas/datos/privacidad y pruebas propias: UI no revela algoritmos. |
| Inbox: media/audio/comentarios sociales, visión/búsqueda/referencias, memoria | Comentarios y cuatro canales confirmados **solo para diseño local 2**, contratos conectados P-030; media/voz 7A; visión/búsqueda P-020; RAG/memoria 7C. | Cada red requiere discovery de capacidad/scopes/consentimiento/ventanas/coste antes de conectar. TikTok no se presume compatible por estar en la demo. Sin publicación automática o entrenamiento libre. |
| Creadores: Creadores/Campañas/Recursos/Derechos/Rendimiento/Spark/Auditoría | 7F condicionado, separado de admisiones. | Necesidad institucional/contratos/permisos/scoring/licencias. Contacto `planned` no envía correo; recurso URL no es upload; derechos 6m no valida contrato; Spark preflight no publica anuncios. |

No importar Industria, Plan comercial, SaaS/multitenancy, Stay/Stripe o nuevos conectores por aparecer en fuente. La paridad incompatible con invariantes requiere decisión y contrato seguro; no prometer “tal cual” sin registrar diferencias/pruebas. Fidelidad observable exige aceptación por flujo y navegador, no copiar controles.

## Ajustes — entrega por capacidad, menú único

Se conserva **IA → Canales → APIs → Diagnóstico → Usuarios → Perfil → Seguridad**, sin Industria/Plan comercial. Sin backends duplicados ni cambio de propiedad M-07/M-08/M-10.

| Sección | Fase y comprobación |
|---|---|
| IA | 3: modelo activado desde APIs, parámetros soportados/estilo bajo invariantes, evaluación/publicación separadas; voz 7A, recordatorios 7B, knowledge 7C. |
| Canales | Diseño local 2 confirma WhatsApp/Facebook/Instagram/TikTok, ninguno conectado. Tras 1: WhatsApp sandbox y resto según P-024/030; contratos/capacidades no verificados. Selector “connected” no prueba conexión. |
| APIs | 1 controles/store; 3 UN texto aprobado, auth/discovery si existe, catálogo/modelo/test final/activación; 6 rotación. Selección visual P-018 pendiente. |
| Diagnóstico | Health local 0 no es diagnóstico integral. 3 lectura saneada vs procesar/simular mutantes; 6 operación/recovery. P-025 exige aislamiento. |
| Usuarios | 1 invitación de uso único, matriz permisos, último admin protegido, sesiones/audit y negativos antes de habilitar. |
| Perfil | 1 edición propia, correo verificado/reauth, zona/foto bajo política; cargo visible no privilegio. |
| Seguridad | Diseño previo; 1 auth/2FA enrolado/verificado/recovery, permisos/firmas no desactivables; 6 export/baja revisada sin cascada core. |

## Fase 7 — cortes independientes, sin compromiso implícito

| Corte | Resultado por aceptar | Dependencias / salida específica |
|---|---|---|
| 7A — Voz y proveedores alternos | Audio/TTS/STT/media seleccionados; fallback por capacidad autorizada. | P-005/012/013/017, modelo/licencia/coste; OGG/Opus/límites en API/dispositivo y recovery/privacidad. Build no prueba dispositivo. |
| 7B — Recordatorios/seguimiento | Programación durable/cancelable y recontacto consentido, sin envío masivo por defecto. | P-005/007/014; opt-out/ventanas/plantillas, zona/calendario y revalidación al enviar, volumen/carreras. 2/24/48h no política aceptada. |
| 7C — RAG/memoria autorizada | Fuentes/metadata/aliases, indexación/evaluación/publicación separados, casos autorizados M-08/M-09. | P-001/005/008/017/023; necesidad/SQL Server, versiones/fuentes/retención/consentimiento y respuestas con fuentes esperadas. Sin pgvector directo, DB transaccional alternativa o aprendizaje libre del chat. |
| 7D — Retención | Descubrir/aceptar problema/flujos/datos M-11 antes de implementar. | Propietario/privacidad y contrato SIIE permitido; mockup no aprueba scoring/campañas/cobros. |
| 7E — Relacionamiento corporativo | Descubrir/aceptar actores/flujos M-12 antes de implementar. | Alcance/datos/roles; no inventar convenios/vacantes/facturación desde imagen. |
| 7F — CRM de creadores | Tras P-028: datos/pipeline/campañas/recursos/entregables/audit; derechos/inteligencia/Spark solo si aceptados. | P-005/017/020/027/028, permisos/licencias; relaciones/estados/fechas, scoring reproducible o pendiente explícito. Sin email/publicación/pauta implícitos; derechos requieren revisión humana de contrato. |

Cada corte puede diferirse/descartarse mediante decisión registrada. Visión/búsqueda, nuevos canales, pagos, fusiones/perfilamiento y publicación requieren discovery/alcance propio antes de añadir tareas; no son requisitos ocultos de fases 0–6.

## Cierre obligatorio de cada fase

Usar la [plantilla](templates/report-and-decision.md), actualizar [avance](progress.md)/[pendientes](pending.md) y emitir en el chat:

1. **Fase/resultado:** completada, parcial o bloqueada; checklist/alcance que se cierra.
2. **Qué se hizo:** entregables, rutas/IDs y cambios verificados.
3. **Evidencia:** entorno/versiones, comprobación/comandos/resultados; separar documentación, build, navegador, SQL test, proveedor sandbox y dispositivo/piloto.
4. **Límites:** no comprobado, aprobaciones/autorizaciones y bloqueos por ID. No ocultar fallos ni usar mocks como prueba real.
5. **Qué prosigue:** fase/unidad exacta y condición de inicio. Si requiere decisión, una pregunta y esperar.

Con aceptación completa y siguiente unidad lista/autorizada se continúa por cambios pequeños; el cierre no autoriza core writes, despliegue o Git. Ante bloqueo informar la salida necesaria sin declarar completada la fase.

## Compatibilidad con el historial

La numeración aplica **desde este roadmap**. No reescribe informes A-001…A-010 ni referencias históricas de otros documentos; interpretar sus números con esta tabla hasta actualización específica. Fuentes/mockups/aprobaciones conservan contenido intacto.

| Referencia anterior | Referencia actual |
|---|---|
| 0 fundamentos/seguridad documental; 1 evidencia/contratos | Puertas previas a 0; contratos adicionales antes de cada capacidad. No son skeleton ejecutado. |
| 2 base ejecutable/roles/store | Se separa en 0 skeleton y 1 base segura/datos; Git/CI sujetos a P-009 aparte, no requisito artificial de arranque local. |
| 3 primer corte/prospectos | 2 Clientes/prospectos y 3 Inbox/texto/canal sandbox. |
| 4/5/6 | Conservan formulario/integración/piloto; entradas/evidencia aclaradas. |
| 7A–7E / D-01 | Conservan voz/recordatorios/RAG/retención/corporativo y revisión visual; 7F añade planificación condicional creadores. |

**Siguiente unidad:** revisión humana del diseño fase 2 local cerrado; después fase 3 local, solo alcance restante aprobado de Inbox/asistente. Fase 1 queda al final del diseño funcional local, antes de cualquier conexión/dato real/entorno compartido. No interpretar demostración como integración, fase 3 completa o aprobación visual definitiva.
