# C4 — unificación lógica reversible de fichas CRM

**Estado: C4 aplicado y aceptado en SQL local, pruebas, frontend, runtime y navegador de preflight.** Fecha: 2026-10-16, America/Bogota. Este documento amplía C1–C3 dentro del stack/contrato local vigentes; no declara un nuevo ADR aprobado ni la implementación completa del router de referencia.

## Comportamiento

Clientes presenta una ficha principal por grupo y busca también los valores de sus fichas de origen. Inbox conserva el contacto, teléfono, canal local, conversación, mensajes, responsables humano/IA, tareas, SLA y memoria originales. El editor utiliza explícitamente el contacto y la conversación de la ficha principal; enviar mensajes y operar el hilo sigue utilizando la conversación seleccionada. Se puede abrir cada conversación de origen. No se borran contactos ni se mueven mensajes, perfiles, asignaciones o memorias.

El grupo es plano: un principal admite varios orígenes; se rechazan ciclos, cadenas, autoasignación y usar como origen un principal que ya tiene miembros. SIIE mantiene su autoridad: no se fusionan estudiantes/aspirantes ni se confirma una identidad académica por coincidencia documental.

En **Ficha principal y conversaciones**, abrir **Revisar posible unificación**, buscar una ficha real y pulsar **Comparar impacto sin modificar datos**. Esta consulta no exige afirmar que sea la misma persona. Elegir cada valor, actualizar la comparación y revisar su resultado; programa/identificador de programa y tipo/número de documento son pares indivisibles, mientras los campos personalizados se seleccionan por clave. Se utilizan etiquetas institucionales reales; no hay catálogos sembrados. C1 y C2 validan los valores elegidos contra el catálogo actual.

La confirmación definitiva requiere una casilla explícita y el fingerprint exacto de la comparación revisada. El servidor exige el booleano literal `true`; rechaza `1`, `"true"`, ausencia y `false`. Nuevos datos, confirmaciones, catálogo o membresía invalidan la comparación con 409. Los borradores de las fichas participantes deben guardarse o descartarse; mensajes/tareas RAM permanecen en sus hilos. La búsqueda cancela y descarta respuestas obsoletas. Fallos/conflictos conservan selecciones y no confirman automáticamente una comparación nueva.

## Persistencia y reversión

La migración explícita `008_contact_merge.sql` añade únicamente `crm_merge.MergeCase` y `crm_merge.Operation`, con marcador/huella de forma propios y referencias NO_ACTION al CRM. No modifica los contratos físicos anteriores ni escribe core. No hay DDL ni datos iniciales al iniciar o leer la aplicación.

`MergeCase` conserva imágenes privadas anterior/aplicada y, al deshacer, anterior/aplicada de la reversión, decisiones y revisión CRM. `Operation` registra merge/undo y retención privada de identificadores anteriores/posteriores de futuras ediciones; las imágenes e identificadores completos permanecen en SQL y nunca se devuelven como auditoría pública. La respuesta muestra solo los campos necesarios para comparar. C3 expone la acción local, no un actor autenticado ni diferencias históricas inventadas. El escritor anterior se reutiliza dentro de la misma transacción/bloqueo global, sin un BEGIN ODBC anidado; se mantienen hashes e idempotencia anteriores.

**Revisar reversión de relación** siempre realiza una nueva consulta. Sin confirmaciones posteriores y con la imagen aplicada intacta, propone valores anteriores. Cualquier confirmación posterior, incluso un guardado equivalente, cambia el valor predeterminado a conservar el actual. Sustituirlo requiere una elección visible. Una elección anterior inválida en el catálogo actual se muestra bloqueada en la comparación y permite elegir conservar valores válidos. La ausencia exacta de perfil se restaura únicamente cuando la unificación creó el perfil destino; nunca se elimina el perfil origen. Deshacer retira la relación, conserva auditoría y no revierte mensajes/tareas/operaciones posteriores.

## Historial, métricas y privacidad IA

C3 agrega la historia y las métricas del grupo actualmente relacionado, identifica contacto/conversación de origen y deduplica la confirmación del escritor frente a merge/undo. El SLA corresponde al hilo seleccionado, no al grupo. Los cursores mantienen precisión SQL, cortes por fuente y vínculo de membresía: después de unir/deshacer se debe actualizar la actividad reciente. No se deducen métricas predictivas.

La redacción R4 considera identidades actuales e históricas de participantes, incluso después de deshacer y de futuras ediciones. Ese cierre histórico también determina los hilos protegidos por reserva e invalidados, separado de los miembros activos que presenta la UI. Cualquier `Attempt` todavía `reserved` bloquea confirmación, reversión o edición afectada dentro del mismo lock global, aunque el estado ya no tenga lease. No se expira una reserva para eludir la protección. Solo los estados existentes aumentan generación/revisión y quedan pendientes, conservando contexto/procedencia/recibos; no se crean estados vacíos. La lectura redacta una copia del contexto/feedback, sin reescribir la evidencia original. El envío al proveedor vuelve a comprobar propietario/fingerprint; no se concatena memoria ni se activan proveedores.

## Evidencia por capa

Evidencia saneada en `.local/c4-merge-20261016/`, con recuentos, resultados y hashes. Los snapshots de fuente contienen rutas/hashes de código, no datos de contactos. Las imágenes privadas de reversión permanecen solo en SQL.

- Respaldo nuevo COPY_ONLY/CHECKSUM, restauración independiente y CHECKDB: 3 comprobaciones aprobadas. El primer intento no inició el respaldo porque el sandbox denegó CIM; se ejecutó con permiso local estrecho.
- Ensayo 008: 9 comprobaciones aprobadas de huella CRM previa, fallo/rollback, repetición, esquema vacío, rechazo de drift y conservación. La alteración técnica de drift se retiró únicamente en la restauración y se verificó la forma.
- Aplicación 008: 9 comprobaciones aprobadas y seis auditorías DDL automáticas. Core y todas las filas CRM/C1/C2/R2/R3A/R4 previas intactas; ambas tablas nuevas vivas vacías. Ninguna pareja real fue confirmada ni unificada.
- Servicio exclusivamente en restauración independiente: 32 comprobaciones aprobadas. Persistencia por conexión nueva, replay/conflicto, alias de lectura, agregado/dedup C3, confirmación posterior equivalente, perfil ausente exacto, perfil origen preservado, reservas históricas, nuevas generaciones sin reemplazar contexto, concurrencia, paginación/cursor e identidad histórica tras undo. Preflight completo con apertura/guards: 1719 ms; no es tiempo SQL puro.
- Backend: corrida completa con **1732 aprobadas y un fallo de arnés**: el snapshot sintético de filtros omitía `contactGroups`, metadato que el repositorio real sí proporciona. Corregido únicamente el mock y añadido el caso de búsqueda por origen que devuelve principal una vez y conserva hilos. Verificación focal final **51/51**, sin repetir la suite completa. Se mantienen dos warnings preexistentes de workers del TestClient con IO real bloqueado; no se realizaron conexiones externas. Ruff, formato y exportación canónica aprobados.
- Frontend: `npm.cmd run check` aprobado — formato, lint, tipos, **202 pruebas en 31 archivos** y build. Ocho pruebas C4 cubren preflight sin afirmar identidad, elección/confirmación vinculada a fingerprint, 409 y nueva comparación, AJAX obsoleto, reintento, borradores, etiquetas institucionales, respuesta tardía y pareja explícita principal/origen. La prueba de Inbox mantiene mensajes/control sobre el hilo origen, guarda ficha sobre la pareja principal y conserva el mensaje RAM tras desvincular. Un fallo inicial de lint por setters síncronos en efectos se corrigió con respuestas ligadas al alcance; no fue un cambio de datos. Build con aviso informativo por chunk de 517,61 kB, sin ampliar división de rutas.
- Preview `127.0.0.1:4173` saludable, imagen `016aa7edc42b074176f8eb7a87d9faef6521c2683828d64dfa612803713d6694`: **7 controles de recreación y 43 HTTP** aprobados. Actividad real 328/250 ms; preflight real completo de lectura 656 ms. C1 revisión 3, perfiles vacíos, dos contactos/hilos/mensajes, 13 operaciones CRM, responsables R2, referencias R3A y ausencia de política/llamadas R4 conservados. Outbound bloqueado y bytes del volumen IA intactos. Rechazo HTTP de confirmaciones inválidas sin escritura; ningún commit/undo vivo.
- Navegador del coordinador: **12 comprobaciones aprobadas**, evidencia `cua-result.json` y captura saneada `c4-review.png` en la carpeta de visualizaciones de la sesión, inspeccionada por el coordinador. Clientes e Inbox muestran preflight real con 17 elecciones; la casilla nunca se marca y confirmar permanece deshabilitado. Cambiar valores exige nueva comparación; nueva búsqueda limpia opciones/preview y cancelar no unifica. El borrador RAM de mensaje sobrevive a navegar Clientes→Inbox; solo se retira el borrador de prueba propio. Scroll CRM de 3071 a 4825 manteniendo página 58, lista 0 y mensajes 0. Móvil de 390 px, página de 375 y panel CRM de 326 px con `scrollWidth` 326: sin desbordamiento. Pestaña del propietario intacta y viewport restaurado. Ninguna corrección adicional de fuente.
- Comprobación SQL final de solo lectura después del navegador: **3 controles aprobados**. Dos contactos, dos conversaciones, dos mensajes, 13 operaciones CRM, perfiles vacíos y ambas tablas C4 sin filas; estados/intentos/política R4 siguen vacíos. Fuente de la imagen aceptada y bytes del módulo de referencia sin cambios. No hubo unificación viva, afirmación de identidad humana ni llamada al proveedor.

Durante normalización se produjo un reordenamiento accidental de imports de dos archivos de referencia al ejecutar Ruff con una exclusión relativa incorrecta desde raíz. Ambos se restauraron exactamente desde la imagen C3 vigente, verificando su identidad y los hashes de bytes; no se ejecutó/importó ese módulo. La verificación final excluye correctamente `app/crm` desde `backend`.

## Operación y límites

El despliegue es solamente el preview privado loopback 4173. No se cambiaron credenciales, proveedor, outbound, producción, core, publicación o Git. No se considera autorizada una fusión de los dos contactos reales por el hecho de existir este corte: el operador debe verificar la pareja y confirmar en la UI.

La imagen C3 anterior sirve como reversión de aplicación mientras las tablas C4 sigan sin operaciones. **Tras el primer uso, incluso después de deshacer un grupo, C3 no protege aliases ni conserva/redacta sus identidades históricas.** Mantener esquema/auditoría y una versión compatible; no recomendar una imagen antigua con escrituras o R4 activos ni borrar tablas para retroceder. Cualquier recuperación posterior requiere un procedimiento explícito con pausas y verificación de compatibilidad.

No se combinan grupos completos, memorias IA, tareas, responsables o SLA. No hay autenticación empresarial de actor ni confirmación académica por IA. La fusión efectiva y su reversión se prueban en restauración y mocks; el navegador vivo solo compara y revisa sin guardar una unión real.

## Fases ordenadas

| Corte | Estado y siguiente aceptación |
|---|---|
| C1 | Configuración compartida y mini CRM aceptados. Edición avanzada/reordenación del catálogo sigue pendiente. |
| C2 | Ficha institucional declarada y candidatos de lectura aceptados; sin vincular SIIE automáticamente. |
| C3 | Historial real y métricas aceptados; C4 añade alcance de grupo, sin reconstruir diferencias anteriores. |
| C4 | Unificación lógica reversible aplicada y aceptada: SQL/pruebas/frontend/runtime y navegador de preflight. Merge/undo efectivo solo en restauración; ninguna unificación viva confirmada. |
| C5 | Próximo: canales, agentes y predicción bajo puertas independientes R3B/R4/R5/R6/R7. Primero definir/validar el canal y permisos de recepción/envío; activación y aceptación de inferencia real siguen separadas. |

La secuencia complementa R1.1/R2/R3A/R4; no renumera sus fases ni da por completadas las 35 rutas del origen.
