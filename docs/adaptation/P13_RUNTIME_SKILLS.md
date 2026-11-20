# Política central de skills de RinovaPlus

Corte: 19 de noviembre de 2026. P13 sigue en validación, 0/4 unidades aceptadas.

## Dónde viven y cómo se aplican

El catálogo ejecutable de procedimientos revisados está en `backend/app/modules/agents/sales_skills.py`; la selección por turno está en `skill_policy.py`. Son **34 procedimientos nativos del CRM**, disponibles para la IA general y todos los especialistas. No dependen de una instalación de Codex, de un directorio de skills en el contenedor ni del proveedor del modelo. Las selecciones antiguas de 20 IDs se conservan por compatibilidad histórica y no omiten la política central nueva.

La política se incorpora en el backend antes de invocar al proveedor, tanto por `assemble_prompt` (admisiones, simulador y agentes) como por `grounded_replies.context` (WhatsApp, Messenger, Instagram, comentarios y sugerencias). No hay una llamada adicional a un modelo para seleccionar skills. Un selector determinista considera la consulta y hasta dos mensajes entrantes del contexto autorizado. Siempre incorpora continuidad, presentación, escucha y revisión; añade diagnóstico, precios, objeciones, negociación, cierre o seguimiento cuando corresponde. El tema de la publicación activa la comunicación contextual para comentarios públicos.

La instrucción es prioritaria respecto a los prompts editables. Los IDs, versión y motivos se incorporan al contexto y a su huella. Mensajería y comentarios guardan `skill_policy` en su operación; las ejecuciones de agentes lo guardan por intento en `AttemptsJson` y el simulador lo muestra. La memoria comercial conserva la traza del último turno, visible en Inbox → Memoria y contexto → Skills del último turno. Esta traza prueba qué procedimientos se suministraron, **no certifica por sí sola que una respuesta generada sea correcta**.

## Catálogo disponible

| Finalidad | IDs |
|---|---|
| Apertura y comunicación | cold-call-opener, customer-voice, draft-outreach, sales-enablement, copywriting, copy-editing, marketing-psychology, ads-copywriter |
| Diagnóstico y calificación | lead-triage, route-lead, lead-intelligence, sales-discovery-questions, meddpicc-scorecard, deal-champion-mapping, deal-review, win-loss-review, sales-call-review |
| Valor, precios y negociación | deal-value-calc, pricing, handle-objection, sales-objection-handling, negotiation-concession-planner, negotiation |
| Cierre y seguimiento | close-plan, sales-closing-tactics, deal-signals, deal-red-flags, customer-escalation |
| Memoria, grafos y continuidad | call-summary, log-activity, graphify, recall, commit-context, handoff |

Los tres IDs repetidos entre las listas del propietario se consolidan. `graphify` es una adaptación de relaciones con mensaje fuente sobre la memoria nativa: no se afirma ejecutar el indexador externo Graphify ni entrenar una red neuronal. La calificación y el abandono son señales explicables; el SLA conserva sus tiempos operativos reales.

## Límites y presentación comercial

Los procedimientos no conceden acceso, permisos de envío, matrícula, pagos, descuentos ni cambios de control. Las opciones de memoria y escritura CRM mantienen sus comprobaciones independientes. Una respuesta pública no recibe historial privado ni datos personales de otros hilos. Las instrucciones contenidas en mensajes, anuncios, transcripciones y páginas son datos no confiables.

Las metodologías SPIN, Sandler, GAP, MEDDPICC, LAARC y JOLT se adaptan a orientación educativa, sin interrogatorio empresarial ni decisiones de admisión basadas en presupuesto o datos sensibles. No se inventan salarios, retornos de inversión, cupos, acreditaciones ni testimonios.

La ficha calcula `entry_payment_offer`: el menor abono inicial positivo entre los planes vigentes permitidos. El agente lo presenta como pago inicial, con las cuotas pendientes y su alcance. Si se pregunta por contado, total o alternativas, informa directamente esos valores. Usa «pesos» y evita las etiquetas internas A1/A2. Una fecha ausente sigue por confirmar; no invalida un importe conocido. Inglés sigue sin tarifa comercial hasta que el propietario confirme su alcance.

## Audio antes del especialista

Las notas entrantes se transcriben primero con un esquema acotado. La interpretación se vincula a institución, conversación, mensaje, recurso y SHA256 del audio original. Se conserva el audio y el cuerpo original; la transcripción se etiqueta como automática, no como verificación humana. Con ella, el siguiente paso vuelve a resolver el especialista y consulta su ficha. Un cambio a Humano, una nueva entrada, un cambio de modelo/contexto o un lease vencido detienen la operación antes de persistir o enviar. Una transcripción no entendida pide aclaración; no completa nombres ni precios.

La transcripción es una etapa adicional de Gemini con reserva independiente de tokens; no se presenta como gratuita. Las extracciones CRM de ese texto conservan su procedencia automática. No se reprocesan audios históricos ni resultados inciertos por esta actualización.

## Empezar una prueba desde cero

Inbox → Memoria y contexto → Reiniciar contexto requiere revisión e identidad reciente. Fija un límite de secuencia; la IA no usa mensajes, referencias publicitarias ni memorias privadas anteriores. Conserva mensajes, recibos, ficha CRM y consumo de voz. Invalida la autorización de respuestas pendientes mediante el epoch del hilo. Restaurar contexto recupera la memoria anterior. Una entrada concurrente obliga a revisar de nuevo, sin borrar datos. Las asignaciones académicas confirmadas y el control Humano permanecen bajo sus recorridos propios.

## Procedencia de las adaptaciones

La lista y el alcance fueron solicitados por el propietario. Los 20 antecedentes y sus fuentes permanecen en `artifacts/live/p13-skills-20261119.json`. Se consultaron las metodologías de `mbfinotti/sales-skills`, commit `b2ed3628695e523919af440eab77648e16c5eea8`, especialmente discovery, objeciones y límites de concesiones: <https://github.com/mbfinotti/sales-skills>. Licencia MIT; copyright 2026 Nativa Labs. La adaptación no ejecuta scripts, conectores ni instrucciones de instalación de terceros. No se afirma instalar paquetes externos sin una fuente revisada; el catálogo productivo es el código nativo indicado arriba.

Se conserva su aviso de licencia en `docs/third-party/sales-skills-MIT.txt`.

## Validación y pendientes

Las pruebas cubren política obligatoria sin selección guardada, selección por tema, aislamiento público/privado, menor abono vigente, prueba de procedencia del audio, cambio de interés interpretado, control Humano durante transcripción y reset/restauración sin borrado. El piloto anterior de Enfermería coincidió con la ficha; el de Barismo expuso el enrutamiento previo a transcripción y **no se acepta**. Queda repetir el audio real y verificar dos programas, continuidad y silencio Humano del nuevo corte antes de aceptar P13.

El ambiente de oficina y sus faders solicitados son una ampliación de P19 pendiente de implementación y prueba, separada de su aceptación técnica inicial de voces.
