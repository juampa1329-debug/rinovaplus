# Borradores descartados y estados de entrega del Inbox

## Inbox: borradores descartados separados de mensajes enviados — 2026-11-23

El titular reporta Cancelado en un hilo Instagram aunque vio respuestas en la app. Contraste del texto exacto en Meta: los borradores de16:44 no figuran como mensajes recibidos; la respuesta final distinta sí está vista y tiene reacción. Diagnóstico confirma cero intentos en las colas canceladas y un intento/Leído en la última salida. Código gemini_whatsapp_control_or_history_changed; el contexto se invalidó antes de invocar Meta, sin atribuir a un componente histórico no trazado. No convertir a Leído por semejanza de texto.

La proyección agrega evidencia de intentos y bandera de borrador sólo para origenIA, cancelado,0intentos y sinIDexterno. UI conserva el cuerpo con Borrador de IA · no enviado, estilo neutro y pie Descartado · no enviado, sin alerta modal roja. Otras cancelaciones/resultados inciertos conservan su diagnóstico; recibos reales no se reescriben.74backend y47frontend pasan; tipos/ESLint/Ruff/compilación institucional aprobados, advertencia histórica de bundle conservada. Publicación y validación visual pendientes en este corte. No reenvíos ni cambios de control, mensajes, recibos, DDL, seeds, servicios nuevos oSIIE. P4/P13/P21 y P22 conservan estados. Ver docs/adaptation/INBOX_UNSENT_DRAFTS_20261123.md.

## Evidencia y causa

En el hilo señalado, los registros cancelados de16:44:09 y16:44:24 tienen0intentos; la respuesta final de16:44:38 tiene1intento y reciboLeído. Las colas a3f44945-a2a8-465a-b088-f15daa450269,77666e76-d9b3-4ef0-a785-6008e8f09d33 ydb8fe3e7-4c66-4fb0-bce9-80ff41ded1b7 son borradores descartados; edd15eb1-7bca-4eb5-8804-5960392dd779 es la salida final leída. El texto exacto del borrador señalado no aparece en la ventana nativa de Meta desde16:39 hasta16:44; la respuesta final sí aparece con Visto y reacción. Nombres, cuerpos y precios se mantienen fuera de esta evidencia versionada.

La guardia de contexto del trabajador cancela antes del primer intento las partes que ya no corresponden al turno vigente. Esto conserva el control Humano y evita responder a un historial anterior. La interfaz anterior coloreaba todos los cuerpos salientes igual, incluidos los descartados, y presentaba su cancelación prevista como alerta roja. El estado almacenado era correcto para los registros contrastados; el problema era su presentación como si fueran mensajes enviados.

## Presentación y límites

El backend sólo marca deliveryUnsentDraft si State=cancelled, Attempts=0, ExternalId ausente y origin=gemini_whatsapp/gemini_comment. Ausencia de metadatos no acredita esta condición. Estados con ID de proveedor, intentos positivos, origen humano o recibo real no reciben esta marca. No se alteran el estado original, la auditoría ni la cola. El lector sólo consulta SELECT.

El cuerpo permanece visible para revisión con una etiqueta textual y estilo neutro/delineado, por lo que la distinción no depende sólo del color. El pie dice Descartado · no enviado y su título explica que no existió intento. No invoca el modal de error para esta cancelación prevista. Leído, Entregado y los demás estados conservan el manejo anterior y sus recibos; no se declara éxito a partir de contenido similar.

Las pruebas cubren la traducción PostgreSQL de la consulta y las combinaciones de origen/intentos/ID/estado; la integración de UI diferencia un borrador de la siguiente salida realmente leída. El ajuste no recupera ni reenvía mensajes históricos y no requiere borrarlos.

## Inbox: borradores y recibos reales publicados y verificados — 2026-11-23

48a122c saludable: backend tiuzhc4py6z0eqqipxfcplpo Success/Running4m27s; frontend vqjeq8sorp79agu9z9d0popj Success43s. Tras recargar el hilo real de Instagram, los10avisos Cancelado del tramo cargado pasan a10etiquetas Borrador de IA · no enviado/Descartado · no enviado, con0botones de error por esas cancelaciones previstas. El mensaje final conserva Leído y el estilo de enviado. Contraste nativo de Meta confirma que el texto exacto señalado no aparece entre los mensajes enviados del tramo16:39–16:44, mientras que la respuesta final distinta sí aparece vista/con reacción. No falsificar entrega por semejanza semántica.

Se conservan cuerpos, estados almacenados, colas, recibos, control IA/Humano y auditoría; no reenvíos ni nuevas inferencias. Sólo presentación y metadatos de lectura acotados.74backend/47frontend,tipos/ESLint/Ruff/workspacebuild pasan; bundlehistórico. Captura local de la vista corregida; evidencia pública sin nombres/cuerpos/precios en artifacts/live/inbox-unsent-drafts-20261123.json. Roadmap actualizado sin modificar aceptaciones P4/P13/P21 ni P22 3/5técnico/0aceptación. SinDDL,seeds,servicios nuevos niSIIEwrites.
