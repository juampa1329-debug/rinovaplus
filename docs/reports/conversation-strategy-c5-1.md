# C5.1 — señales, estrategia y autonomía interna

## Resultado y alcance

Este corte amplía el mini CRM compartido por Clientes e Inbox con señales comerciales trazables, riesgo de abandono cualitativo, propuestas de estrategia y evaluación humana. La autonomía se limita a crear una tarea interna; no responde al contacto ni envía mensajes o campañas. C5 completo, aprendizaje neuronal y aceptación de inferencia real permanecen pendientes.

La base local conserva dos conversaciones con dos registros salientes. No contiene evidencia entrante suficiente para una evaluación comercial, una probabilidad o una estrategia real validada. El estado inicial muestra **No evaluable**, **Desconocido** y autonomía no solicitada. No se cargan planes, calificaciones ni mensajes de demostración en el preview.

## Contrato de evaluación

El índice cuenta criterios respaldados por evidencia entrante: interés expresado, siguiente paso solicitado y compromiso declarado. Cada criterio aporta una unidad, sin ponderaciones; el intervalo es de una a tres señales cuando existen. La ausencia de señales produce `null`, no cero ni un porcentaje. La rúbrica es experimental y visible; no representa una probabilidad calibrada de conversión.

El riesgo de abandono admite desconocido, preocupación o retirada expresada, con explicación y referencias entrantes verificables. Una objeción no confirma abandono y el silencio no demuestra churn. Los registros salientes y las correcciones del operador no se convierten en declaraciones del contacto. La solicitud de no contacto bloquea las tareas aunque después aparezcan señales positivas. El historial C4 y las evaluaciones humanas que reportan no contacto aportan restricciones de seguridad separadas; no se reescribe una salida del modelo para atribuirle evidencia histórica que no produjo.

El modelo devuelve un único envelope con `context` y `strategy`. Se conservan las seis listas y el formato histórico de `ContextJson`; las respuestas legadas siguen siendo legibles y no reciben una estrategia inventada. La estrategia añade propuestas informativas, manejo de objeciones, remarketing como propuesta y borradores de lectura, siempre con referencias. No inventa precios, información académica, horarios acordados o resultados. El prompt pasa a `analysis-v2-strategy-v1`.

El plan se inserta dentro de la misma transacción que confirma el resultado R4, después de validar lease, política, binding, revisión y fingerprint. Un resultado obsoleto no crea un plan. No se añade una segunda llamada al proveedor, un nuevo servicio ni consumo duplicado.

La procedencia original —plan, conversación, generación, revisión de inferencia, proveedor, modelo, prompt, política y fecha— se conserva. La elegibilidad actual se calcula por separado: contexto, mensajes, feedback, identidad histórica, generación, configuración y cobertura deben seguir coincidiendo. Una operación de control puede ser preparada y recibida por R3A/R4 sin otra inferencia; eso actualiza la cobertura observada, no afirma que el modelo haya visto información nueva. Un mensaje, corrección, cambio de contexto/procedencia, configuración o generación C4 invalida la elegibilidad anterior.

## Autonomía que se ejecuta realmente

La interfaz separa autonomía solicitada y efectiva, con motivos de bloqueo. Empieza desactivada por conversación y dispone de pausa global para tareas IA. El análisis R4 puede continuar durante atención humana; únicamente la ejecución de tareas se pausa. El control IA previo se rotula **sin envíos automáticos**, porque una tarea interna constituye ejecución.

Antes de crear una tarea, una transacción con el lock global existente vuelve a comprobar pausa global, permiso individual, control IA, conversación abierta, política/configuración, plan vigente con cobertura completa, evidencia de siguiente paso o compromiso, no contacto, agente IA activo asignado y responsable humano vigente si existe. También comprueba cualquier tarea pendiente, ejecución previa del plan y reservas R4 de los participantes históricos C4. Un bloqueo esperado por reserva omite esa acción y permite que R4 recupere sus propias reservas; C5 nunca expira leases para forzar una tarea.

Cada plan puede crear una sola tarea normal, pendiente, sin fecha inventada, asignada al humano actual elegible o sin asignar si no existe. No se genera otra mientras haya cualquier tarea pendiente. La creación y su auditoría `automation` se confirman juntas. No se altera el CHECK que reserva `crm_inbox.Operation` a operadores locales ni se atribuye una acción IA a un humano ficticio. La revisión R2 también refleja las tareas automáticas para rechazar ediciones con revisión antigua. R3A conserva la referencia durable exacta de la operación/tarea y C3 muestra su origen IA sin duplicarla como operación humana.

Desactivar el permiso, activar pausa global o tomar control humano compite mediante el mismo lock de escritura. Una tarea ya confirmada permanece como tarea real; desactivar no borra actividad ni mensajes. No se ejecutan respuestas, campañas, matrículas, pagos o herramientas dictadas por el modelo.

## Evaluación humana y privacidad

La evaluación registra útil, no útil o corrección, junto con un resultado observado explícito. Se liga al plan y a su revisión y conserva actor de operador local, sin afirmar autenticación compartida. La corrección entra en R4 como evidencia atribuida al operador y restablece su recuperación después de fallos; no modifica campos derivados ni confirma resultados académicos. Las métricas cuentan tareas y evaluaciones reales de la conversación.

Los borradores sobreviven a navegación en RAM. Si cambia el plan, una evaluación anterior queda bloqueada; iniciar la evaluación del nuevo plan requiere una acción explícita que reinicia utilidad, resultado y comentario. Los conflictos 409 conservan el borrador y la advertencia aunque una consulta periódica posterior tenga éxito. Las lecturas descartan respuestas antiguas del mismo polling y de otras conversaciones.

Los textos generados y correcciones pasan por la redacción R4, incluidos identificadores históricos C4. La lectura vuelve a redactar los textos contra las identidades actuales/históricas, sin alterar UUID de evidencia. No se concatenan memorias entre conversaciones, no se consulta un conjunto de casos parecidos ni se envían identidades institucionales al proveedor. No hay entrenamiento ni realimentación neuronal acreditados.

## Persistencia y operación

La migración explícita `009_conversation_strategy.sql` crea únicamente `crm_strategy.Policy`, `crm_strategy.EvaluationPlan` y `crm_strategy.Operation`. No crea filas iniciales, modifica tablas anteriores ni escribe el core de negocio. Tiene marker/shape propios, FKs conservadoras, restricciones JSON y una única ejecución de tarea por plan. No se ejecuta DDL desde GET, arranque o `create_all`.

El nuevo respaldo COPY_ONLY/CHECKSUM y la restauración independiente con CHECKDB preceden al ensayo y aplicación. La transacción ODBC de ejecución normal usa `autocommit=False` y el lock existente; no introduce un `BEGIN` anidado. Los fixtures y las tareas de prueba se restringen a pruebas unitarias o restauración independiente.

Antes de utilizar C5.1 puede arrancarse la imagen C4 anterior sólo tras verificar que las tres tablas están vacías y no existe actividad C5.1. Después de cualquier plan, tarea, feedback u operación C5.1 se debe conservar esquema, planes y auditoría; una imagen anterior no interpreta permisos ni procedencia de tareas IA. Para revertir runtime se necesita pausar la automatización, verificar actividad y utilizar una versión compatible o un procedimiento explícito de operación detenida. No borrar tablas, tareas o auditorías para simular una reversión.

## Evidencia por capa

La evidencia saneada se conserva en `.local/c5-strategy-20261016/`: hashes de fuente inicial, respaldo/restauración, ensayo de migración, servicio SQL, bordes de cobertura y resultados de gates. No contiene dumps de identidades, mensajes o snapshots privados. La implementación no acredita inferencia real Gemini, campañas, autenticación compartida o producción.

Resultados comprobados y aceptación local cerrada:

| Capa | Evidencia y límite |
|---|---|
| Recuperación/migración | Respaldo COPY_ONLY/CHECKSUM, VERIFYONLY, restauración independiente y CHECKDB; nueve controles de ensayo y nueve de aplicación. Tres tablas vacías y siete auditorías DDL automáticas; hashes CRM/Admisiones/core conservados. |
| Servicio SQL | 29 controles del servicio, 14 de bordes y ocho finales de cobertura/supresión histórica, exclusivamente en restauración. Sin llamadas al proveedor. |
| Backend | Una regresión amplia: 1765 aprobadas y dos warnings preexistentes de workers/TestClient. Tras añadir la comprobación explícita de cobertura: 56 focales aprobadas; no se repitió la suite completa ni se suman pruebas superpuestas. Ruff formato/lint y exportación canónica comprobados. |
| Frontend | 207 aprobadas en 32 archivos; tras cerrar reintento incierto y su caso: 15 focales en tres archivos aprobadas. Formato, lint, tipos y build finales aprobados; advertencia del bundle mayor a 500 kB conservada. |
| Runtime/HTTP | Imagen `sha256:fa3bb5bc73b915f1f5ff36e98ae9f9da8978f95eb9e243a2ac9897349db2fb10`, healthy en loopback 4173; siete controles de recreación y 62 HTTP. Snapshot y volumen IA intactos, cero escrituras HTTP válidas y cero llamadas externas. |
| Navegador | 12 controles escritorio/móvil aceptados en Clientes e Inbox: ausencia de evaluación demo, rúbrica, opt-in persistente y opt-out, atención humana, borradores y scroll independiente. Dos escrituras legítimas de configuración; permiso final OFF, pausa global intacta y cero tareas. |

El baseline de C5 contiene 15 confirmaciones, siete y ocho registros por contacto; las dos confirmaciones de conversación adicionales respecto del antiguo corte C4 ya aparecen en el respaldo previo con los mismos UUID, hashes y fechas. El arnés heredado esperaba 13; se contrastó la causa antes de actualizarlo. No se atribuye identidad autenticada a ese registro. La conservación se demuestra mediante el snapshot/hash, no una constante histórica.

Incidencias acotadas: el sandbox impidió crear el temporal de pytest y no ejecutó los casos; se utilizó el permiso local habitual. El primer ensayo DDL falló porque `Plan` es palabra reservada SQL; se sustituyó por `EvaluationPlan` antes de aplicar en la copia viva y se repitió el ensayo. El arnés SQL de bordes comparaba un GUID textual de pyodbc en mayúsculas con una cadena canónica en minúsculas; se corrigió su comparación y el ensayo pasó. Los controles de reserva, feedback UTC/recuperación y polling/reintento se cerraron antes del freeze.

La fuente importada `backend/app/crm` conserva sus cuatro hashes iniciales y sigue sin montarse. Los planes/tareas sintéticos, unificaciones y reversión de pruebas sólo existen en la restauración independiente; las tablas C5 vivas seguían vacías al terminar HTTP. El pase posterior de navegador confirmó dos operaciones reales de permiso: una fila de política quedó OFF, dos auditorías de autonomía, cero planes/tareas/attempts y ninguna unificación. El readback final confirmó 15 operaciones CRM previas, snapshot de negocio intacto, fuente congelada y referencia importada sin cambios. La configuración de IA del propietario se preservó; no se ejecutó una transferencia de credenciales ni activación de política/modelo. La prueba de generación con conversaciones reales continúa pendiente de sus puertas de alcance, modelo y presupuesto.

## Recorrido y evidencias de aceptación

En Clientes o en el panel derecho del Inbox, la sección **Inteligencia predictiva · IA** muestra evaluación, rúbrica y propuestas de lectura cuando exista un plan real. **Solicitar autonomía interna** guarda la preferencia; el estado efectivo explica por qué no puede ejecutarse. **Desactivar autonomía interna** y **Pausar todas las tareas IA** son controles durables; ninguna opción activa el proveedor o campañas.

La creación efectiva de planes/tareas, feedback, conflictos, no contacto y reversión transaccional se verificó con SQL real exclusivamente en restauración y con respuestas sintéticas de pruebas aisladas. El navegador vivo no demuestra inferencia ni ejecución sobre un prospecto evaluado. El panel de tareas R2 mantiene su actualización explícita para consultar nuevas tareas confirmadas; los borradores no se sobreescriben.

Evidencia saneada: `backup-result.json`, `rehearsal-result.json`, `apply-result.json`, `repository-result.json`, `edges-result.json`, `coverage-result.json`, `gates-result.json`, `docker-final.json`, `http-result.json`, `cua-result.json` y `final-result.json`, dentro de `.local/c5-strategy-20261016/`. La lectura HTTP de estrategia tardó 687 y 765 ms en este ensayo local; no es un benchmark de producción. La captura aceptada se conserva en `C:/Users/Developer_PC/.codex/visualizations/2026/10/15/01a1413b-fa6a-75f0-9cb1-49f8df6bf312/c5-strategy.png`.

## Fases siguientes

1. **C5.1 aplicado y aceptado localmente:** señales experimentales, planes y autonomía interna acotada; navegador acepta el estado real sin evaluación y sus controles. La aceptación de inferencia real permanece separada del modo desactivado.
2. **C5.2:** biblioteca de estrategias revisadas para casos similares, con objetivo, resultados observados, privacidad y evaluación antes de compartir o recomendar entre conversaciones.
3. **R3B/R5:** primer canal confirmado, recepción real y banco general/especialistas por programa o curso, con conocimiento versionado y transferencia humana efectiva.
4. **R7:** campañas y horarios medidos, consentimiento, frecuencia y permisos de salida; una propuesta no autoriza su envío.
5. **R6:** dataset revisado, baseline y aprendizaje neuronal fuera de línea, evaluación/sombra/promoción/reversión. No sustituir esta puerta por un índice heurístico o el almacenamiento de feedback.
