## Estado vigente P5-ES local — 2026-10-27

P5 cerrada al **100,00% local,4/4 criterios canónicos**. Un solo CRM CBN integrado: **http://127.0.0.1:4178/#/agents**. Imagen `crm-cbn-workspace:p5es-r5`, base propia `CBN_P5ES_TRIAL_20261027_13990dac`, perfil privado `.local/p5-es/final-runtime`, acceso `.local/p5-es/ACCESS.txt` con las mismas credenciales humanas. Receta vigente: `docker compose -p crm-cbn-current-p5 -f compose.agents.yaml up -d --pull never`. P4 conserva imagen/base/perfil/volumen y contenedor detenido `crm-cbn-preview-p4-preserved`; P3 y los demás checkpoints siguen conservados. No iniciar sus recetas simultáneamente en4178.

Constructor, jerarquía orientador→programa→etapa, personalidad/instrucciones/variables/reglas/objetivos/herramientas/canales, modelos/fallback/cuotas por perfil, diagnóstico opcional, archivo/restauración/versiones y asignación desde el Inbox real están integrados. Guardar válido deja disponible; editar pausado conserva pausa. Etapas, fuentes y acciones sensibles mantienen sus controles separados. Simulación fija agente/versión; actor/nonce/hash/lease evita doble inferencia. Handoff, pausa y epoch invalidan resultados y envíos antiguos. No se activa IA automática por guardar ni se monta el productor B011; una sola outbox C10. Restaurar configuración crea versión nueva en pausa y conserva memoria, historial y asignaciones.

Se conservaron8contactos/8conversaciones/26mensajes/8notas/8tareas y3comentarios, y se añadieron3perfiles educativos y1etapa de ejemplo persistidos. El modelo de ejemplo bloquea IO; la prueba de navegador dejó el agente de programa pausado para revisión. El catálogo nuevo es declarado CRM, con ejemplos marcados sintéticos; no representa oferta académica SIIE validada. Vincular solicitud/período sigue cerrado hasta revisar el mapeo real. Publicación/administración/reindexación de conocimiento pertenece a P6; P5 sí aplica ámbito, responsable, vigencia y revisión al recuperar fuentes.

Pasan242pruebas backend,311frontend, tipos y lint(exit0,1warning histórico de cleanupEpoch),19checks de navegador y smoke tras reinicio;8constructor/API,22ejecución,18ciclo/fuentes/handoff,28C10/dispatch,8archivo/tarea/techos,3replay de contexto,10storage y5recuperación. Los conteos son alcances separados. Cero llamadas a proveedores reales: las inferencias y transportes de calificación son controlados. No hay dominio/apps reales; **P4 permanece82,29%**, sin aceptar recepción/OAuth/envío externo por esta fase.

Release P5 `9046a8c33a3bbbb9d874ba0fc5451e3db5815c9afcc9b6552aabb6b0d2a2793a`:3entradas congeladas,150tablas,242FK,120mapeos. Se conservan14entradas P2 y releases P3/P4. Se comprobaron106tablas de negocio heredadas y30académicas vacías entre fuente/respaldo/P5; no hubo nueva consulta a SIIE Windows. Recuperación conserva145tablas estables, autentica vault y retira sesiones copiadas; reinicio conserva147tablas estables y sesión. La fuente y destino finales tienen0blobsready: volumen propio y copia vacía verificados, sin afirmar ensayo P5 de archivos poblados. Fuente P4 intacta frente a respaldo fresco.

El ledger conserva pesos y textos: **170/279 hitos done,109pending;26/56criterios aceptados**. Los porcentajes incluyen trabajo parcial, no horas ni producción externa.

| Fase | Avance técnico con trabajo parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Evidencia: `docs/adaptation/sql/SQL_P5_ES_REVIEW.md`, `artifacts/p5-es/acceptance-review.json`, `docs/adaptation/sql/p5_es_validation.json`, `tasks/p5-es-progress.json` y `graphify-out/p5-es/`. Retomar con `python -X utf8 -B backend/tools/check_p5_es_checkpoint.py --self-test --replay-parent` y `python -X utf8 -B backend/tools/p5_es_graphs.py check`, offline; nunca con preparadores/seeds/calificadores SQL automáticos. Replay transitorio P4→preview→P3→P2→P1 desde1225preimágenes exactas, sin modificar verificadores. Cinco referencias históricas a dos fuentes cambiadas conservan sus bytes/SHA en `docs/adaptation/history/p5-predecessors/`; la evidencia P5 actual está separada. El replay usa un directorio privado persistente del helper para evitar llenar su tmpfs.

Para revertir un perfil: restaurar versión en pausa y revisar permisos descendientes antes de reanudar. Para volver a P4: pausar entrada/salida, conservar base/solicitudes/colas/volumen P5, detener P5 e iniciar el contenedor P4 conservado. No reparentar datos posteriores ni reenviar efectos inciertos. Siguiente: P6; las validaciones externas P4 necesitan dominio/apps/cuentas reales y conservan sus pendientes.

## Historia preservada anterior a P5

## Registro de implementación anterior; prevalece el cierre superior

# P5 en implementación — 2026-10-27

## Actualización de continuidad vigente

Release aditivo P5 congelado SHA `9046a8c33a3bbbb9d874ba0fc5451e3db5815c9afcc9b6552aabb6b0d2a2793a`, tres entradas inmutables: diario + catálogo CRM declarado + solicitudes IA por actor/lease. Compilación150tablas SQL2019/150 revertida; no cambios académicos. Se aplicó en copias propias fixture, fixture-r2 y fixture-r3; cada perfil/principal nuevo, sin reticket de previos. R1 detectó SELECT de KnowledgeDocument denegado; R2 añadió sólo lectura de las3tablas de conocimiento y pasó8checks API (constructor, catálogo declarado901/902, replay, guardar disponible, jerarquía, edición conserva pausa). R3 amplía lectura de Campaign/Task para memorias ya admitidas; su perfil está preparado, calificación pendiente. Archivos privados en `/var/lib/cbn-p2/p5-es-v1`, perfil vigente de calificación `fixture-r3-profile.json`. R1/R2 conservados, nunca reutilizar sus tickets con el nuevo ACL.

Implementados adaptadores `agents_policy.py`, `agent_catalog.py`, `agent_ai.py`, `agents.py`, `agents_api.py` y preparación/migración propias. Despacho P5 en spanish/store/auth/api/settings/ui_contract sin editar14entradas P2 ni releases P3/P4. Reutiliza constructor/ciclo/simulador y vault canónico; no credenciales Scentra. History.Actor codifica UUID íntegro en24caracteres; no truncamiento. Peticiones con ledger y modelo/versión seleccionados, estados pausados bloquean IO, fallback sólo rechazos previos conocidos. Rollback histórico implementado conservando pausa e historial; aún falta evidencia. Endpoint supervisión ahora consulta ledger P5, nunca productor B011. Cambios de asignación invalidan solicitudes P5 y cola C10, sin borrar B011. Reindexación se declara pendiente P6; no otorgar DELETE conocimiento por conveniencia.

Últimos tests legacy:45passed/12failed; varios esperan aprobación de perfiles que el humano eliminó y otros tienen fakes antiguos o contrato de gateway obsoleto. No declarar estas12preexistentes sin reproducir baseline ni debilitar pruebas. Corregidos isinstance(actor,str) y render opcional de nombre; fuentes se consultan sólo si document_ids no vacío. Falta ejecutar otra vez tests. Frontend sólo transporteCSRF actualizado; falta montaje institucional completo, catálogo declarado, restauración de versiones y controles de Inbox. No hay imagen/perfil final P5 ni promoción4178 todavía. P4main sigue preservado/activo con su imagen/base/volumen, roadmapP5 sigue45% hasta evidencia final.

Revisiones semánticas iniciales completas: artifacts/p5-es/reference-review.json (13fuentes,42campos,15acciones,12hallazgos) y existing-review.json (39fuentes,64hechos), fragmentosdraft51/109 y64/88. Son evidencia del epoch inicial; no sustituyen revisión final del código actual. Baselines públicos no recapturar. Próximo: terminar simulación/roles/concurrencia/handoff/fallback/reversión, UI y pruebas actuales; recuperación SQL/media/rollback, preview4178, grafos/proof/memoria y ledger fijo279/56.

## Registro inicial anterior (no describe el estado actual)

Objetivo humano: llevar P5 al100% local, conservando SIIE/P4 y copias anteriores, con pruebas, grafos, memoria y porcentajes. No aceptar por esquema ni redefinir textos/pesos279/56. P5 depende P2/P3 (ambas100%), no del cierre externo P4. P5 parte45%: constructor/ciclo/simulador histórico existen; falta composición institucional actual y sus pruebas. Regla humana vigente: guardar perfil válido lo hace disponible; un perfil pausado conserva pausa; diagnóstico opcional. No reinstalar aprobación obligatoria de perfiles. Etapas/fuentes/acciones sensibles mantienen sus controles propios.

Versión fuente actual: P4 `crm-cbn-workspace:p4es-r3`, base `CBN_P4ES_TRIAL_20261026_a8ef717a`, preview4178, receta compose.channels.yaml/proyecto crm-cbn-current-p4. P4=82,29%; no dominio/apps reales. Sus1218pins/checks pasaron localmente al iniciar P5; replay padre primero falló por Docker apagado, después pasó sin modificar ningún checker. Se inició Docker Desktop oculto y los contenedores crm-cbn-p2-sql2019 y crm-cbn-p2-tools. Principal/helper/CA/TLS siguen iguales; siempre `docker exec -w /tmp/p2-code/backend crm-cbn-p2-tools ...`, nunca su /app/backend antiguo. Nunca imprimir perfiles/credenciales.

Baseline público previo a cambios de aplicación: `.local/p5-es/public-preimages.zip`, registro `p5_es_input_baseline.json` (incluye proofP4 y su archivo público de preimágenes para replay transitivo). El setup creó el archivo/registro/corpus y luego falló al desempaquetar check_semantic_cache: API actual devuelve4valores (nodes,edges,hyperedges,uncached), no3. No repetir setup ni recapturar baseline: `.local/p5-es/graph.py` completó caché/AST. Corpus16archivos/66819palabras,4docsuncached, AST309nodos/1164aristas. Dos revisiones semánticas por mandato de Graphify: `/root/p3_reference_graph` y `/root/p3_existing_graph`; sólo escriben reviews/fragmentos P5, no implementación. La referencia real del constructor está en Scentra/agents, no ai_agent (IA general). Su suplemento de preimágenes se captura separado antes de cambios.

Decisión de integración: reutilizar Configuration/effective_configuration/resolve/policy_for, ciclo, cuotas y componentes del constructor existentes. No montar routers legacy con contexto de operador local ni leer/copiar credenciales de Scentra. Nuevo perfil/principal P5, restauración nativa propia y release aditivo propio; mantener cerrados los perfiles y releases P2/P3/P4. Vault/ajustes canónicos siguen en crm_access. Permisos de agentes basados en ajustesIA, asignación basada en inbox; revalidar sesión/CSRF/módulos antes de IO y después. Una sola outbox C10; guardar perfiles no activa automatización. No montar dispatcher B011.

Pendiente de implementar: journal propio, catálogo CRM de programas con autoridad explícita (la copia española tiene30tablas académicas vacías; no fabricar datos oficiales ni escribir SIIE), registro durable de solicitudes IA por actor/nonce/hash/lease para replay e incertidumbre. Reutilizar las8tablas crm_agents existentes. Adaptador de catálogo fijo y explícito; no aliases académicos ambiguos. Simulación siempre agente/versión seleccionados, sin memoria escrita de aspirante ni envíos; propuesta en Inbox ligada al epoch/control y sesión para que handoff/inactivación invalide resultados. Fuentes publicadas/revisión/vigencia/ámbito filtran en SQL. Rollback de versión conserva historial/asignaciones/memorias y no activa productores. Añadir pruebasSQL reales/fallos/roles/concurrencia/sourceisolation/recovery, corregir7testsUI obsoletos que exigían aprobación, seed de perfiles claramenteficticios en nueva copia, integrarconstructor/asistente/asignación en4178 y preservarP4contenedor/imagen/perfil/base/volumen.

Hasta este checkpoint no hay implementación P5 ni migraciones aplicadas, no hay perfil/base P5. El roadmap sigue45% y la app visible sigue P4. Seguir trabajando, no declarar100% por inventario. Los scripts anteriores de calificación/seed no son comandos de arranque ni de consulta de memoria.
