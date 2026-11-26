# Motor de agentes por etapa y margen de salida

Estado inicial: código preparado, publicación/configuración nativa pendientes.

## Diagnóstico

La ficha general mostraba Gemini 3.1 Flash Lite, mientras el motor P21 global ya tenía OpenRouter Sonnet 4.6 como principal y Sonnet 5.5 de respaldo. Eso no demostraba una llamada a Flash Lite en cada turno. Sí existía una dependencia real: el trabajador exigía perfil y credencial Gemini antes de ejecutar el principal global. El simulador sin elección explícita tampoco heredaba ese motor. Los fallos PostgreSQL documentados anteriormente son otra causa y no se atribuyen a cuotas de Gemini.

## Cambio

- IA general y especialistas heredan el motor institucional. Sus instrucciones, skills, fuentes, memoria, asignación de voz y permisos siguen perteneciendo al agente.
- Una ruta de apertura opcional se aplica sólo en las etapas CRM activas seleccionadas por clave. La pregunta y el turno pendiente completo tienen prioridad: financiación, objeciones, comparación, decisión y seguimiento conservan el principal comercial incluso en Nuevo.
- Apertura fallida: principal comercial y después respaldos aprobados, sin regresar al modelo propio antiguo. Se conserva la revisión de catálogo/capacidades/precios y las reservas por intento. Cambiar modelo no permite enviar en Humano.
- El simulador sin modelo explícito hereda el motor; las pruebas explícitas P22 conservan su modelo exacto. Sin ficha CRM vinculada utiliza el principal comercial. El simulador de agente admite un alternativo; la cola automática conserva la lista completa de respaldos P21.
- El trabajador ya no exige una clave Gemini para texto/imágenes si el motor elegido usa OpenRouter. La interpretación de audio es una etapa aparte, con el modelo de audio seleccionado en APIs y modelos. La síntesis sigue siendo ElevenLabs.
- Máximo común de salida configurable entre 512 y 8000 tokens, independiente del presupuesto acumulado y del tamaño visual de cada parte. La propuesta operativa es 4000; las reglas siguen exigiendo mensajes breves y contratos completos. No implica cobrar ni generar siempre ese máximo. Las reservas son conservadoras, no facturas de consumo real.
- Se evita una segunda reserva inicial completa para la generación que ya reserva P21 tras validar el catálogo. Se mantienen reservas de ASR y de cada alternativa.
- Los perfiles muestran el modelo efectivo heredado; sus versiones históricas se conservan sin reescribir 28 perfiles. Desactivar el motor central haría reaparecer sus configuraciones propias: revisar antes de hacerlo.

## Comprobación local

334 pruebas backend focalizadas aprobadas, incluida selección por necesidad/etapa, ausencia de dependencia Gemini en texto, cambio de contexto, control Humano, ASR e imágenes. Selección solapada con rondas anteriores; no suite completa verde. Se actualizó un contador de biblioteca de 34 a las 37 guías existentes y se aisló el doble de ASR de consultas de cola ya cubiertas por otros tests.

21 pruebas frontend focalizadas, tipos, ESLint de archivos modificados y build institucional aprobados. ESLint global informa 8 errores y 4 advertencias en archivos ajenos a este cambio (ChannelSettings, AdmissionsPanel, SessionState y vistas multimedia); no se declara lint global verde. Advertencia histórica de bundle grande conservada.

## Publicación y aceptación

Completar después del despliegue: modelos y tarifas recargados, claves de etapas CRM seleccionadas, máximo 4000 guardado, lectura nativa de general/especialista y salud Coolify. No acreditar inferencia pagada, respuesta real por etapa, ausencia universal de fallos o P22 aceptada sólo por estos tests.

Sin DDL, seeds, servicios nuevos ni escrituras SIIE. P23 sigue con 0/9 criterios aceptados; P22 conserva 3/5 técnico y 0/5 comercial. Otros pendientes del Inbox y el envío incierto de horarios no se reenvían con esta configuración.
