# P3 · Inbox, ficha compartida, CRM y riesgo de abandono

La persistencia española se amplía sobre una restauración propia de P2. SQL Server 2019, compatibilidad150 y TLS validado son obligatorios. Los nombres físicos pasan por114 bindings cerrados; los parámetros de usuario nunca se convierten en nombres SQL. Las30 tablas académicas conservan su estructura y autoridad, con DENY para el principal de aplicación.

## Persistencia y recuperación

El release `cbn_workspace_spanish_v1` tiene SHA256 `7d4c3f55654d8d683246c2cd2547d29da5274825170f304b2c6b069e914d379b`. Sus tres entradas SQL/modelo quedan congeladas tras comprometerse. Añade `CRMTrabajoEstado`, `CRMTrabajoAsignacion`, `CRMTrabajoTarea`, `CRMTrabajoNota`, `CRMTrabajoUnificacion` y `CRMTrabajoMigracion`:144 tablas y229 FK en la composición completa.

El responsable es un usuario institucional UUID con FK compuesta por InstitutionId/UserId. Una tarea deriva su contacto de la conversación; no admite una pareja contacto/conversación contradictoria. Las notas son apéndices con autor. Unificar requiere confirmación humana, revisiones vigentes y control transaccional de ciclos, alias y tamaño; conserva personas, conversaciones, mensajes y valores originales. Separar desactiva el vínculo. La ficha primaria determina etapa y riesgo compartidos del grupo.

La migración sólo se ejecuta mediante el operador explícito en destino nuevo autorizado: STARTED durable, bloqueo, DDL transaccional, COMMITTED y repetición NOOP. Rechaza destino, release, modelo o diario ajenos y no toma propiedad de una transacción del llamador. El arranque del producto no contiene DDL.

La restauración nativa valida COPY_ONLY, CHECKSUM, cabecera, VERIFYONLY, identidad y huellas de144 tablas antes de publicar la copia. El perfil propio conserva el origen del diario y su linaje; revision2 fija también el contenido binario y las fechas de ese diario. Autentica los secretos con su clave, conserva cuentas/MFA y retira sesiones/desafíos/códigos copiados. El consumidor anterior conserva su imagen, perfil, base y puerto; el retorno no borra datos P3 ni intenta aplicar un ticket de138 tablas a144 tablas.

## Consultas, edición y concurrencia

Clientes, Inbox y tareas filtran en SQL antes de OFFSET/FETCH con25 elementos. Los mensajes usan secuencia bigint numérica y cursor anterior con límite SQL; se serializa la secuencia como texto para evitar pérdida de precisión en JavaScript. Las páginas posteriores incluyen revisión ancla; un cambio concurrente pide actualizar el listado. Buscar un alias puede localizar su ficha primaria, mientras etapa y demás filtros pertenecen a esa ficha.

Inbox conserva colas de no leídos, propios/sin asignar, estados, humano/IA, interés manual, SLA y riesgo vigente, además de canal y etapa. La asignación consulta usuarios elegibles paginados. Toda escritura vuelve a comprobar sesión, CSRF, módulo y permisos actuales dentro de la transacción; usa CAS e idempotencia por actor, acción, recurso y payload. La revisión combina estado de trabajo y definiciones CRM.

La misma ficha editable se presenta en CRM e Inbox/mini CRM con etapas, etiquetas, campos, notas, tareas, actividad y origen institucional. No duplica arriba una ficha de lectura y abajo otra editable. Los valores académicos se conservan; no se inventa un programa ni se modifica su identidad oficial sin un enlace aprobado. Un nuevo contacto exige una etapa institucional configurada.

Los borradores se conservan en memoria de sesión por persona/conversación, incluso al desmontar el panel y visitar otras secciones. Salir o expirar limpia la sesión. Una respuesta incierta conserva OperationId y payload con la revisión original: el reintento puede recuperar el resultado ya comprometido. Un409 definitivo de revisión permite una nueva acción explícita con revisión actual. No se persisten fichas, mensajes ni credenciales en localStorage.

Tomar control humano incrementa el epoch y cancela bots todavía no iniciados. Los trabajos iniciados/inciertos se conservan y se señalan para revisión; una respuesta del operador no finge cancelar una entrega externa en curso. Marcar leído sólo avanza hasta la secuencia realmente observada. Los mensajes de esta composición se registran como locales; identidades de proveedor requieren el transporte de P4.

## Riesgo compartido y alcance

CRM, listado Inbox y mini CRM consumen la misma proyección. Sólo se muestra una rúbrica vigente si su EvaluationRun está completado, corresponde a la misma identidad/conversación, su evidencia tiene mensajes/rutas compatibles, coinciden watermark/etapa/fórmula/score/nivel, la fecha no está en el futuro y tiene como máximo24 horas. Una entrada nueva, cambio de etapa o evidencia obsoleta invalida la proyección. Sin evidencia válida aparece «Sin evaluación»; una conversación cerrada identifica «No aplica».

El resumen incluye estado, razones, fecha, origen y siguiente acción. La valoración manual de interés y el SLA son independientes. Una rúbrica cualitativa no es una probabilidad ni una predicción entrenada. P3 integra la superficie de análisis y su lectura verificable; productores automáticos, proveedores y entrenamientos conservan sus fases P7/P10. Las pruebas conectadas utilizan una ejecución de reglas sintética identificada, sin atribuirle aceptación de proveedor real.

## Interfaz y verificaciones

Se conserva Azul noche · Glass, temas claro/oscuro y la shell general. Tres paneles a1200/1440px y composición móvil sin desbordamiento horizontal; controles de teclado, estados de carga/error, detalle técnico y ayuda extensa colapsados. Las pantallas del producto no muestran nombres de copia, códigos de sprint ni rótulos de ensayo.

La evidencia separa pruebas puras, SQL/API, navegador, migración/restauración y conservación. Los56 criterios y279 hitos canónicos mantienen textos y pesos; un porcentaje técnico admite trabajo parcial, mientras el100% requiere todos los criterios y dependencias aceptados en su alcance.
