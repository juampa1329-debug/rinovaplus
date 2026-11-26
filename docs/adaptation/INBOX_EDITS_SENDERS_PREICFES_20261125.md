# Inbox: ediciones, autor de la vista previa y PRE-ICFES

Fecha Bogotá25Nov2026. Estado inicial: cambios funcionales comprobados localmente; publicación y lectura histórica real pendientes.

## Ajustes y atención nativos

- Política de voz revisión38 guardada y recargada: máximo120s, campo editable0–300s. Se conservan perfiles, mezcla, modo de notas entrantes, cupo5 por hilo y controles existentes.0 en el campo de duración tiene la semántica ya documentada de ausencia de máximo configurado, sujeto al procesador de5min; no se confunde con0 en el cupo por conversación, que significa sólo texto. Sin nueva síntesis pagada.
- Una consulta de PRE-ICFES sobre pago inicial/recibo fue respondida manualmente por petición expresa: abono220.000, tres cuotas220.000, total880.000 y confirmación explícita de financiación antes de emitir volante. Una sola salida acreditada Entregada, después de comprobar que el primer clic no había creado una salida. Chat restauradoIA; no replay de operaciones anteriores ni generación de volante/SIIE.
- PRE-ICFES ya existía activo, cubría el programa27 y tenía las37 skills, grafo/contexto, memoria comercial y observaciones CRM habilitados. Se guardó versión2 con nombre que incluyeG1/G2/G3 y sin horario G2 pendiente en el prompt. Pautas de estudiante/acudiente, venta gradual, ficha vigente, cuotas, formulario diligenciado, volante y menores específicas; políticas contextuales de pagos/menores añadidas. No se crearon duplicados ni se concedieron herramientas nuevas. Modelos institucionales y4000tokens conservados. Tener las37 disponibles no implica usar todas innecesariamente en un turno.

## Ediciones

El normalizador anterior omitía edit/original_message_id y trataba la edición como marcador sin contenido. Las ediciones no eran entradas elegibles para nueva respuesta. En el hilo revisado hay dos operaciones anteriores fallidas por cambio de contexto/control; no se atribuye sin trazabilidad una causa más precisa a cada una.

La corrección conserva esos campos acotados. Antes de usar un texto editado o programar su respuesta exige un único original entrante en la misma institución, cuenta, identidad y conversación. Se crea una nueva entrada de corrección, manteniendo inmutable el cuerpo original. Las bajas editadas siguen excluidas de respuesta y su texto validado llega al observador de campañas. Sin original verificable no se adivina contenido ni se encola una respuesta basada en él.

La vista muestra «Mensaje editado», el contenido nuevo y una cita del original. El contexto de IA interpreta la corrección y conserva el ID del evento vigente para sus guardas. Si la edición es el ancla citada, cita el ID externo/interno del original verificado, sin cambiar la identidad del evento que cerca el envío. Los marcadores antiguos se reconstruyen sólo desde el recibo cifrado previamente autenticado, coincidiendo canal/ruta/tipo/autor/ID; esta lectura no reproduce eventos ni envíos históricos.

## Autor en la lista

Una lectura agrupada para los25 resultados identifica el mismo último mensaje usado por la vista previa, con orden CreatedAt/Sequence. El autor humano proviene de ProviderOperation.ActorRef unido a AccessUser de esa institución, no del responsable asignado actualmente. La interfaz abrevia Juan Pablo→Juan P. Las respuestas bot con origen de IA muestranIA; otra automatización muestraAutomático y un envío externo sin autor atribuible muestraCanal. Los mensajes del contacto no reciben prefijo. Se conserva la estructura visual y el recorte existente.

## Validación

330 pruebas backend focalizadas pasan, incluidas16 del archivo de ediciones/remitentes: límites del parser, recibo histórico coincidente, origen único, aislamiento, bajas, inserción separada, cita del original, autor efectivo y traducción SQL PostgreSQL. Ruff E9/F aprobado.

Archivo frontend amplio:52 aprobadas/2 fallidas previamente documentadas (expectativa antigua de saldo insuficiente y aviso de acceso). Selección independiente de7 pruebas de nueva vista previa/duración pasa; se solapa con las52. Una selección negativa que omitió los dos casos antiguos expuso además dependencia del doble de HTMLDialogElement.close en otros casos; no es una verificación completa verde y no se modificó ese código de producto. Tipos, ESLint de archivos modificados y build institucional pasan. Bundle1203,55kB/348,46gzip, aviso histórico conservado.

Sin optimizacionesP24, DDL, seeds, servicios nuevos ni escriturasSIIE. P24 implementación0%/aceptación0 de6; otras aceptaciones intactas. No se acredita una nueva edición real después de publicar, respuesta de voz nueva ni SLA/carga máxima.
