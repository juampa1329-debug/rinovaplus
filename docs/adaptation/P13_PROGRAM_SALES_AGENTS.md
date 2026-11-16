# P13 · Agentes de venta por programa

Plan del 16 de noviembre de 2026. La ficha y la importación se desarrollaron en local. P13 conserva **0 de 4 hitos aceptados** hasta aprobar la ficha piloto, probar la URL real, activar el enrutamiento con el especialista y verificar ambos recorridos en WhatsApp. El piloto empieza con Auxiliar de Enfermería y valida la réplica con un segundo programa de software cuyo nombre oficial confirmará Admisiones.

## Recorrido del aspirante

1. **Admisiones** recibe el mensaje de WhatsApp. Si el aspirante pregunta por «enfermería», busca el alias en el catálogo. Si hay un solo programa compatible, lo usa como contexto comercial; si hay varios, pide una aclaración.
2. **El especialista** continúa en el mismo hilo con el contexto de la conversación. Responde sobre el programa, resuelve objeciones con datos aprobados y propone un siguiente paso como recibir el enlace de inscripción o hablar con un asesor.
3. El Inbox muestra el programa de interés y el agente que respondió. Si la persona cambia de programa, se valida el nuevo interés. Si el equipo pasa el chat a **Humano**, la IA deja de responder y se cancelan sus salidas pendientes que todavía admitan cancelación.

Ejemplo de prueba. «¿Cuánto cuesta enfermería y cuánto dura?» debe llegar al agente de Auxiliar de Enfermería si el alias identifica un programa único. El agente responde con el precio, la vigencia y la duración publicados. Si falta el precio vigente, lo dice y ofrece confirmarlo con Admisiones.

## Punto de partida en RinovaPlus

- P5 ya ofrece agentes por programa y etapa, prevalidación, simulación y asignación por contexto confirmado. P6 ya publica conocimiento por ámbito y vigencia con fuentes revisadas.
- WhatsApp ya recibe mensajes reales y el flujo Gemini elige la configuración del agente mediante el selector existente. Hoy clasifica la intención y usa respuestas predefinidas. Hay que conectar la respuesta con el catálogo y las fuentes vigentes.
- El interés detectado pertenece al CRM comercial. La postulación y los datos académicos conservan sus validaciones. El piloto reutiliza el selector, el control Humano y la cola actual de WhatsApp.

## Mini roadmap

| Hito | Entregable | Se acepta cuando |
|---|---|---|
| **P13.1 · Ficha comercial** | Una ficha por programa del catálogo con nombre oficial, alias, sede, jornada, modalidad, duración, materias o módulos, requisitos y enlace de inscripción. Registrar precio en COP, concepto, vigencia, fuente y responsable de aprobación. | Admisiones revisa la ficha piloto. Una tarifa vencida o sin aprobación queda fuera de la respuesta del agente. |
| **P13.2 · Importar desde URL** | En Conocimiento, pegar el enlace oficial del programa y, si aplica, adjuntar el plan de estudios. Extraer una página y seguir únicamente enlaces oficiales pertinentes cuando falten datos. Mostrar las diferencias en un borrador revisable. | Cada dato extraído conserva su URL o documento y fecha de consulta. Una segunda importación muestra los cambios al revisor antes de publicarlos. El importador se limita a fuentes públicas autorizadas. |
| **P13.3 · Enrutamiento y venta** | Vincular un especialista activo al programa. Detectar alias, resolver dudas con una pregunta breve y reutilizar el contexto comercial entre mensajes. Configurar un guion de diagnóstico, objeciones y siguiente paso. | El simulador verifica alias y errores de escritura, dos programas compatibles, cambio de interés, ausencia de tarifa, solicitud de asesor y cambio a Humano mientras hay una respuesta pendiente. |
| **P13.4 · Piloto real** | Probar Auxiliar de Enfermería y un programa de software en WhatsApp. Activar por programa y registrar programa detectado, agente y versión, fuente y resultado. | Ambos recorridos se verifican de extremo a extremo. Las respuestas citan datos vigentes, el chat queda en el mismo hilo y la toma de control humano funciona. Admisiones aprueba el resultado y prueba cómo pausar cada agente. |

Para empezar con Auxiliar de Enfermería hacen falta su URL oficial, el plan de estudios si está en otro documento, y la tarifa vigente aprobada. Para el segundo piloto hacen falta los mismos insumos y su nombre oficial.

## Skills y extracción

- Codex tiene instaladas globalmente `firecrawl`, `firecrawl-scrape`, `firecrawl-crawl` y `firecrawl-build-scrape`. Sirven para explorar la URL de un programa y preparar la integración. [Firecrawl CLI](https://github.com/firecrawl/cli) · [Skills oficiales](https://github.com/firecrawl/skills)
- Las skills de diseño de agentes y calificación comercial orientan el guion y los casos de prueba. La ruta **Académico → Programas por escuela** permite crear y editar fichas y aplicar al borrador la información extraída. Los agentes que ya tienen un programa seleccionado pueden consultar su ficha en el contexto de simulación. El enrutamiento de respuestas de WhatsApp a especialistas sigue en P13.3.
- Para usar la extracción alojada, configurar `FIRECRAWL_API_KEY` en el backend. La lista predeterminada admite `cbn.edu.co` y `www.cbn.edu.co`. `RINOVA_PROGRAM_SOURCE_HOSTS` permite especificar los nombres exactos de otros sitios autorizados, separados por comas. Pegar en la ficha una URL HTTPS del programa y revisar los valores antes de guardar. [API de extracción de Firecrawl](https://docs.firecrawl.dev/api-reference/endpoint/scrape)
- Páginas candidatas para el piloto. [Auxiliar en Enfermería, Escuela de Salud](https://cbn.edu.co/escuela-de-salud/auxiliar-en-enfermeria/) · [Desarrollo de Software y Aplicaciones Móviles, Escuela de TIC](https://cbn.edu.co/escuela-tic/desarrollo-de-software-y-aplicaciones-moviles/). Admisiones debe confirmar las tarifas y su vigencia antes de que el agente las cite.
- **Ajustes → APIs y modelos** carga el catálogo del proveedor seleccionado con su credencial guardada. En OpenRouter se consulta el catálogo filtrado para la cuenta. Los modelos se agrupan por empresa y se pueden filtrar por familia. Por ejemplo, Anthropic agrupa Claude, OpenAI agrupa GPT y ChatGPT, y Google agrupa Gemini y Gemma. [Catálogo de Gemini](https://ai.google.dev/api/models) · [SDK oficial de OpenRouter](https://github.com/OpenRouterTeam/go-sdk/blob/main/models.go)

## Actualización del roadmap general

El corte canónico mantiene **93,62 % técnico**, **261 de 279 hitos** y **45 de 56 criterios aceptados**. P12 reúne la puesta online y puede acreditar hitos de las fases originales. P13 tiene seguimiento propio y sus cuatro hitos empiezan pendientes.

| Fase | Evidencia disponible y revisión pendiente |
|---|---|
| **P4 · Canales** | Adjuntar verificación de la cuenta WhatsApp, recepción de webhooks, envíos del Inbox y recibos de Meta. Completar la matriz de canales del alcance vigente y verificar recuperación externa antes de aceptar el criterio completo. |
| **P7 · Mensajería masiva** | Usar los recibos del Inbox como antecedente del transporte. Para los hitos de P7, registrar una plantilla real aprobada de Meta y un envío desde Mensajería masiva con el recorrido y los estados exigidos. |
| **P8 · Campañas** | Completar el recorrido de campaña o remarketing del criterio original con sus dependencias cerradas. |
| **P9 · Ads** | Aceptar el alcance de cuentas, captación y acciones de Meta/TikTok, y sus dependencias. |
| **P10 · Inteligencia** | Revisar la evidencia del modelo y cerrar las dependencias de P8 y P9. La prueba conversacional de Gemini es evidencia de operación del agente. |
| **P11 y P12 · Operación en línea** | Adjuntar el despliegue verificado en Coolify, HTTPS, la salud de los workers y la prueba real IA/Humano. Conciliar el motor y alcance institucional acordados, el corte y los mapeos, el respaldo con restauración y la aceptación institucional. |

Cada actualización debe registrar **ID de hito, alcance probado, entorno y versión, fecha, resultado, enlace al recibo y responsable de aceptación**. Tras aceptar la evidencia contra el criterio original, actualizar su estado, ejecutar los verificadores y publicar el porcentaje recalculado. La definición, los pesos y los denominadores permanecen fijos. El detalle de los 18 hitos está en el [backlog P12](../../tasks/p12-online-backlog.json).

### Primer registro de conciliación

- **16 de noviembre de 2026, producción, `b64436d`.** Frontend y backend desplegados en Coolify. La aplicación HTTPS cargó el Inbox y Operación mostró las ocho etapas al día. Evidencia candidata para P11.3.m4. [Despliegue del frontend](https://coolify.rinovaplus.com/project/4sbjxzeggnkoxduukakxrdir/environment/hqyhsbzxmznuyhra3gowdbsq/application/kqqiosl3tuiym2zcu2x0frdr/deployment/7xuf6zfsmtfaoxetii1s1mir) · [Despliegue del backend](https://coolify.rinovaplus.com/project/4sbjxzeggnkoxduukakxrdir/environment/hqyhsbzxmznuyhra3gowdbsq/application/nwbyrdvtsfclmm6zyffjqjqp/deployment/wp0ld6bjmcv9wtldhkgzjnmb)
- **WhatsApp en producción.** Gemini respondió primero en un hilo nuevo. El mensaje de prueba de las 10:54 a. m. de Bogotá entró con el hilo en Humano y sin respuesta de Gemini durante la verificación. Los tres envíos pendientes del Inbox mostraron recibo de lectura de Meta. Evidencia parcial para P4.3.m6. Conservar los recibos operativos de la cuenta en el ámbito privado.

Los verificadores de aceptación y avance ponderado se detienen en esta copia de despliegue porque faltan 20 archivos de evidencia histórica referenciados por el registro de aceptación. Para formalizar el próximo corte, recuperar esos originales desde su archivo de evidencias y ejecutar ambos verificadores en una copia que los tenga accesibles.
