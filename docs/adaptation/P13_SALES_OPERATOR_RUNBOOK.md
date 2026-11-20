# P13 · Especialistas comerciales y contexto

Corte del 20 de noviembre de 2026. Alcance inicial aceptado 4/4 tras fuentes y piloto real, no por cantidad de pruebas. Original P0–P11:100%; P12 auxiliar:100% PostgreSQL/Meta. No cambia el denominador original.

## Configurar los agentes

En **Agentes → Especialistas por programa y origen de anuncios**, elegir el orientador activo y preparar la vista previa. La tabla incluye cada programa/jornada activo, su escuela, el system prompt propio y los datos pendientes. Revisar y confirmar antes de crear. El alta es atómica, conserva especialistas existentes y rechaza una vista previa desactualizada; repetir la misma operación no duplica agentes.

Se conservan proveedor, modelo, capacidades y límites actuales del orientador. Cada especialista tiene instrucciones editables y20procedimientos seleccionables. La voz queda en selección automática para respetar el perfil por escuela y el respaldo de P19; se puede asignar otro perfil desde cada agente. Los importes y contenidos se consultan en la ficha vigente; no quedan congelados dentro del prompt.

**20 skills** descubiertas con find-skills e instaladas globalmente para Codex:12de Anthropic,4de Corey Haines y4de memoria/contexto. Fuentes y huellas en `artifacts/live/p13-skills-20261119.json`. El CRM incorpora procedimientos originales revisados en español derivados de esas prácticas. No ejecuta archivos SKILL.md descargados ni sus conectores o comandos. Graphify es una herramienta para grafos de repositorios/documentos; aquí se adaptan sus principios de procedencia a un grafo nativo por conversación. No se afirma que el motor externo Graphify/AgentMemory esté ejecutándose en producción.

## Derivación y memoria

Una selección académica confirmada o un agente elegido manualmente conserva prioridad. En automático se usa el interés explícito más reciente, alias, correcciones ortográficas acotadas y jornada. Una coincidencia única elige su especialista activo; varias jornadas o programas requieren aclaración. Si el especialista no está disponible, continúa el orientador indicando lo pendiente. No se modifica el expediente académico.

El mismo hilo conserva citas comerciales del cliente con mensaje/secuencia de origen y los últimos intercambios. En **Inbox → Ficha CRM → Memoria comercial**, abrir el grafo para consultar hechos, procedencia, calificación y continuidad entre agentes. Son hasta80evidencias,40turnos y24mensajes recientes; el historial completo permanece en el chat. No es memoria ilimitada ni un motor de entrenamiento neuronal.

La extracción comparte la llamada de Gemini que redacta la respuesta: no añade una inferencia separada. Sólo acepta categorías permitidas y citas literales del mensaje entrante. Se registran objetivo, presupuesto declarado, jornada, plazo, objeción, resolución explícita y siguiente paso. Datos ausentes quedan desconocidos; ninguna cita de la respuesta del bot se convierte en declaración del cliente. Se requiere memoria de perfil habilitada. La memoria se separa por institución y conversación y nunca se incluye en comentarios públicos.

La calificación comercial usa una rúbrica explícita de interés/preparación; no es probabilidad de matrícula. Presupuesto/riqueza y atributos demográficos no puntúan. Sólo completa LeadScore/Temperature vacíos o todavía pertenecientes a su última escritura automática; una corrección humana se conserva. El riesgo muestra objeciones con evidencia y explicación, sin atribuirse un modelo entrenado. El SLA sigue usando tiempos y recibos reales del motor existente; la IA no escribe tiempos ficticios.

## Anuncios y comentarios

Para Click-to-WhatsApp se guarda el referral firmado recibido en messages:source_id,source_type,headline,body,source_url y ctwa_clid acotados. El identificador de clic se conserva para atribución y no se envía al LLM. Se puede vincular localmente el ID del anuncio al programa/jornada desde la vista de especialistas. No crea anuncios ni cambia gasto. Un anuncio sin vínculo sigue aportando su texto; si no identifica un programa de forma suficiente, se aclara sin inventar. Sin referral no se puede atribuir de forma fiable un chat a un anuncio.

En comentarios de Facebook/Instagram, generación automática y sugerencias comparten el contexto de publicación que consulta Meta. «Precio», «información» o «me interesa» se refieren a esa publicación. La regla de contexto prevalece sobre una bienvenida genérica, incluso para PreICFES u otra actividad aún no incluida en los25programas. Sólo un cambio explícito del cliente cambia el tema. La publicación identifica el tema pero no acredita una tarifa o requisito; se consultan las fichas/fuentes revisadas. Sin texto suficiente, el automático deja revisión. No se mezcla la memoria privada ni se afirma haber enviado un DM.

La prueba real inicial de PreICFES generó una sugerencia sobre ese curso tras guardar las instrucciones del panel. No se publicó una segunda respuesta a comentarios antiguos. No se necesita ampliar suscripciones si los eventos y el texto de la publicación ya llegan; el caso observado disponía del caption correcto.

## Antecedentes y cierre del piloto

El piloto del44 por nota de voz detectó un batch SQL Server no compatible en el guardado de calificación. Se reemplaza por INSERT/UPDATE parametrizados dentro del bloqueo institucional; la transacción anterior no confirmó una respuesta para enviar. La memoria muestra el estado de la generación. **Revisar recuperación de respuesta** comprueba la última fuente, cuenta activa, control IA/epoch, lease vencido y ausencia de respuesta comprometida. Requiere permisos de Canales/Inbox, identidad reciente y confirmación del nuevo consumo. Reutiliza la misma generación y EffectKey, guarda auditoría y conserva el intento previo; no reenvía mensajes aceptados ni repite automáticamente inferencias inciertas. Máximo3intentos. Los datos citados extraídos de texto se validan contra el cuerpo entrante; las voces pendientes se interpretan cronológicamente antes de derivar, con transcripción automática atribuida al recurso/SHA; no se presenta como verificación humana.

La revisión comprende dos fichas oficiales (Enfermería y Software), alias, ambigüedad, cambio de interés, memoria y control Humano. El resultado real de cierre consta abajo y en `tasks/p13-sales-progress.json`.

## Aceptación del alcance inicial · 20 de noviembre

El propietario pidió cerrar tras comprobar el piloto: fuentes/fichas Enfermería y Software revisadas, orientación y financiación/objeciones contrastadas. Barismo→Software conservó nombre, ciudad y objetivo. Entrada real en Humano a las 18:06 sin respuesta automática hasta las 18:10; después se restauró IA. El grafo conserva la meta concreta frente a referencias genéricas. P13 queda 4/4. Las pruebas pendientes descritas arriba son antecedentes ya resueltos; ver tasks/p13-sales-progress.json y artifacts/live/p13-close-review-20261120.json.

Biblioteca vigente: 34 procedimientos revisados del backend, independientes de Codex. Cada turno selecciona y traza las guías consultadas completas, sin atribuir ejecución a las diferidas. Inglés sin precio confirmado, SLA sin umbral y candidatos/traspasos por etapa P22 siguen explícitos. No se garantiza conversión ni se decide matrícula autónomamente.
