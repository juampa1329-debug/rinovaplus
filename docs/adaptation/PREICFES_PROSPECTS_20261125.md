# Importación de solicitudes PRE-ICFES · 25 de noviembre de 2026

## Plantilla elegida y campaña guardada, sin envío

Tras elegir expresamente la opción 2, el titular autorizó su revisión por Meta y guardar la campaña sin enviar mensajes. Se creó `cbn_preicfes_promocion_juan_pablo_v1`, Marketing/es, con el cuerpo elegido, cabecera y tres respuestas rápidas, vinculando la variable al primer nombre del CRM y usando un ejemplo ficticio. Meta la recibió y figura **En revisión de Meta**; no se acredita aprobación. Se completó la confirmación reciente con el acceso guardado, vaciando el segundo campo, sin extraer credenciales.

Se guardó la campaña **CBN · PRE-ICFES Alta Competencia · Promoción 50 % · Solicitudes noviembre 2026 · No activar**, en la cuenta WhatsApp CBN, con la nueva plantilla y la selección exacta de 100 fichas. La recarga y nueva apertura confirman **Borrador, versión 1**, primer nombre, zona America/Bogota, sin fecha programada y Seguimiento sólo después de un envío confirmado. No se pulsó Preparar sin enviar ni Activar: hay cero destinatarios preparados, cero intentos y cero mensajes de esta campaña. El caso de celular incompleto no forma parte de la selección.

Los dos teléfonos alternativos siguen conservados en las notas CRM y el plan local para la futura preparación. No se los cuenta como destinatarios de canal ya habilitados: la selección guardada es de 100 fichas, y los dos números adicionales aún requieren su tratamiento al preparar el envío. No se habilitaron consentimientos ni cambió el control Humano por guardar el borrador. Recibos completos en `.local/preicfes-import-20261125/meta-submission-campaign-receipt.json` y las comprobaciones nativas privadas. Esta acción no requiere cambios de código ni un nuevo despliegue. Pendientes: decisión de Meta, revisión operativa de destinatarios y autorización posterior de activación.

## Resultado final tras la resolución del titular

El titular resolvió expresamente cuatro de los cinco grupos: conservar ambos teléfonos y una sola ficha para dos casos, escoger el nombre del formulario fechado para un número compartido y crear una ficha comercial en la coincidencia con documentos contradictorios, dejando su identidad académica por validar. Se añadieron las cuatro fichas mediante un lote nativo separado, sin modificar las 96 previas. El contraste final de los 101 grupos devuelve **100 importados, uno para revisión y cero nuevos pendientes**, con 100 identificadores únicos. Sólo permanece fuera el caso con celular incompleto. Veinte fichas creadas conservan sus fechas de solicitud vacías.

Las dos instrucciones de contactar ambos teléfonos están guardadas como notas de seguimiento. Una de ellas se abrió en la ficha real y muestra la observación y ambos números, junto a la fuente original legible. Se conserva una sola ficha por cada caso. Los dos teléfonos adicionales constan como intención para una futura campaña autorizada: 100 fichas y 102 números declarados, todavía sin identidades adicionales de canal habilitadas, preparación de destinatarios ni envíos. La selección final de contactos sustituye la selección inicial de 96 para el trabajo futuro; los recibos iniciales permanecen conservados.

## Corte inicial observado

El titular autorizó crear fichas CRM desde dos Excel de solicitudes de información y clasificar el grupo PRE-ICFES. Los mensajes nuevos se muestran primero en el chat para su elección; no se someten a Meta ni se activa la campaña durante esta unidad.

Se revisaron 116 filas con datos: 34 del archivo general y 82 de Alta Competencia. Las coincidencias se consolidaron en 101 grupos de revisión; no se confundió un grupo con una identidad académica acreditada. El contraste nativo devolvió 96 nuevos claros, cinco para revisión y cero contactos previamente importados. Se crearon las 96 fichas por la importación nativa, con interés PRE-ICFES CBN Alta Competencia, tipo Preinscrito y etapa Calificación. Un segundo contraste devolvió 96 importados, cinco para revisión y cero nuevos pendientes; los recibos contienen 96 identificadores únicos.

Los cinco grupos pendientes incluyen un registro con teléfonos alternativos, una misma denominación con teléfonos/correos distintos, nombres distintos que comparten celular, un teléfono incompleto y una coincidencia con documentos/correos contradictorios. No se escogió un destinatario ni se sobrescribió una ficha para resolver esas diferencias.

Diecinueve fichas creadas carecen de fecha de solicitud en origen; se conservaron vacías sus fechas de preinscripción. Dos de ellas indican información enviada según el Excel, sin fecha o recibo verificable: la nota conserva ese dato, sin inventar ausencia de respuesta ni antigüedad de conversación. Las filas del formulario registran aceptación de política de datos; esta evidencia se conserva en sus notas, sin crear consentimiento activo de campaña. Se reutilizan los once campos existentes. No se importaron documentos de identidad a notas comerciales.

La comprobación de una ficha sin fecha confirma interés, etapa, referencia, archivo y fechas vacías. La fecha de importación no sustituye última conversación. La clasificación se conserva en Interests y pre_programas; no es asignación a un programa académico ni matrícula. Los filtros actuales de búsqueda/programa del listado no consultan esos intereses: no acreditar una vista de cohorte filtrable por nombre de programa. La selección exacta de las 96 fichas para una futura campaña queda guardada localmente, sin prepararlas ni activarlas.

## Corrección de la ficha comercial

El titular aclaró que la promoción está disponible con pago de contado y financiación. Se corrigieron concepto de tarifa, presentación y condiciones del plan en la ficha nativa PRE-ICFES, revisión 8 comprobada tras recarga. Se distingue precio base promocional de total financiado y se retira la exclusividad del descuento al contado. Se preservan las fechas existentes de abono/cuotas, inicio, grupos, beneficios y requisitos. Un primer guardado excedió el máximo de 150 caracteres del concepto y fue rechazado; se acortó ese campo y se verificó el guardado posterior. No se alteraron importes o fechas por deducción ni otras fichas.

## Publicación y verificación

El importador admite fechas de solicitud vacías, conservando la validación de las fechas presentes, la revisión de identidades y las operaciones idempotentes. Su nota común dirige a la evidencia original en lugar de afirmar universalmente que los Excel carecen de autorización documentada. No activa consentimiento.

Código `feca36a`, integrado con la versión productiva concurrente en `fc14046`. Push a ambas ramas sin forzar ni retirar cambios recientes. Backend `hygtdntuv2ooic22adbwsn3d`: Success/Running, 4m23s. Frontend `pq0jbgdrrvozmocqbvxnqwxa`: Success/Running, 21s. Pasan 36 pruebas backend focalizadas y tres frontend del importador; Ruff pasa. No se declara suite completa ni prueba de entrega Meta.

Recibos, clasificación nominal, propuestas completas, datos comerciales y libro de revisión se conservan únicamente en `.local/preicfes-import-20261125/`, excluido de Git. La evidencia agregada está en `artifacts/live/preicfes-prospects-20261125.json`. No se crearon mensajes, consentimientos de campaña, plantillas Meta, envíos o activaciones por este trabajo. Sin DDL, seeds, nuevos servicios ni escrituras SIIE. Roadmap y aceptaciones previas intactos.

Siguiente paso: elección del titular sobre los textos propuestos; posterior revisión Meta y autorización de lanzamiento. Corregir el celular incompleto antes de incorporar el único caso pendiente. Al preparar la campaña deberán contemplarse los dos números adicionales expresamente solicitados, con sus verificaciones propias de canal y consentimiento; guardar una nota no acredita esas verificaciones.
