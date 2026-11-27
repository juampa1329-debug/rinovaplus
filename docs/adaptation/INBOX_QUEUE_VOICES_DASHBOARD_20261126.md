# Continuidad del Inbox, voces y gráfica — 26 de noviembre de 2026

## Diagnóstico observado y alcance

El titular pidió atender primero las preguntas pendientes desde las 16:00 Bogotá, corregir la continuidad tras varios botones de campaña, dejar sólo Juampa, preparar selección aleatoria/copia de ajustes y mejorar la gráfica. La revisión completa del intervalo sigue abierta: no equivale a haber atendido todo el histórico.

Se observaron nativamente `55P03` bajo bloqueo institucional, generaciones `operation_lease_expired` y partes salientes `send_lease_expired` con resultado incierto. Un saludo entregado no acredita la entrega de las demás partes. La telemetría publicada en `c0429a8` identifica dos consultas que ocupaban el escritor: `candidate_rows:188` (audiencia de campaña) e `inactivity:838` (historial de recibos de seguimientos).

`edafe9a`, integrado en `c0429a8`, espera como máximo tres adquisiciones de transacción antes de entrar al trabajo, sin repetir el cuerpo ni un commit; renueva sólo la generación propia todavía vigente dentro de un plazo total acotado. Conserva incertidumbres de proveedor. Backend publicado y observado saludable en Coolify tras 4m19s. La contención persistió después: ese corte no resuelve por sí solo toda la incidencia.

## Corrección preparada sobre ese corte

- La validación de un destinatario de campaña consulta todas las identidades de su persona canónica, conservando filtros originales, deduplicación, consentimientos, bajas, autoridad, inscripción SIIE, control Humano, cuenta, plantilla y cadencia. No reconstruye toda la audiencia para cada destinatario. Las vistas previas completas conservan su alcance.
- La búsqueda general de inactividad se realiza en lectura. Antes de escribir una señal se repite la consulta para el trabajo exacto con activador, flujo, autoridad, última entrada, recibos y deduplicación vigentes. Un cambio entre ambos momentos descarta el candidato. No se relajan horarios ni consentimiento.
- `Ver plan de pagos` recupera contexto únicamente si se acredita como botón nativo de una campaña aceptada de la misma cuenta, identidad y conversación. No concede la excepción de atención humana del botón específico del asesor.
- La recuperación académica incluye el nombre del programa de esa campaña verificada. Dos botones seguidos de pagos y programa conservan los hechos financieros completos. Se reconoce también «opciones de pago» como consulta financiera.
- Voces: opción `assigned` por defecto, o distribución entre voces activas para conversaciones nuevas; las asignaciones explícitas por agente/escuela y la voz ya reservada tienen prioridad. La selección usa una distribución estable por conversación. Una voz desactivada nunca se sintetiza; una reserva antigua incompatible conserva el retorno a texto. La copia de perfil preserva parámetros de síntesis/ambiente, limpia asignaciones, exige elegir voz nueva y empieza desactivada.
- Gráfica diaria: techo redondeado a múltiplos de 100, marcas de 100 en 100 y detalle por barra con puntero o teclado; el área se desplaza si hay muchas marcas. No se modifica la consulta ni la semántica de recibos.

No se creó ni activó un supervisor GPT-4.1 cada 30 minutos. Se explicó como propuesta complementaria: deberá distinguir preguntas pendientes, trabajo en curso, borrador sin intentos y envío incierto, volver a consultar el contexto y pasar por la cola existente. No debe reenviar a ciegas ni levantar Humano.

## Atención operativa comprobada hasta el corte

Ocho nuevas orientaciones manuales revisadas: cinco con recibo Entregado observado y tres Aceptado por el canal. El envío de Evelin quedó Entregado a las 19:01 Bogotá; su chat se observó en IA. Un límite de tiempo de la herramienta al comprobarlo no fue un fallo del envío. No se repitió. El noveno envío seguía En cola al último corte; requiere conciliación antes de restaurar control o repetir.

No se acreditan todavía entrega de las tres aceptaciones, auditoría completa desde las 16:00, prueba automática nueva del arreglo, ficha/especialista PRE con grado 10 guardados, ni desactivación nativa de las otras voces. Permanecen tareas de esta petición, no aceptaciones concedidas.

## Verificación local

- 318 pruebas backend focalizadas aprobadas; después 43 solapadas, que incluyen una regresión nueva de dos botones y recuperación del programa. Regresiones de selección canónica ejecutan la consulta en SQLite y validan traducción PostgreSQL; no son prueba de plan/carga PostgreSQL productiva.
- Frontend: 22 aprobadas y dos fallos en reproducción/descarga de muestras, coincidentes con los dos fallos heredados documentados en el corte previo. No declarar suite completa verde. Los casos nuevos de escala/detalle y copia de voz pasan.
- TypeScript, ESLint de archivos modificados, Ruff E9/F63/F7/F82 y compilación pasan. Bundle 743,19 kB / 219,01 gzip; conserva advertencia de tamaño. Node local 22.16, distinto del rango 24.19 declarado; no equivale a validación en el runtime de producción.

P13/P19/P21 conservan aceptaciones iniciales; P22 técnico3/5 y comercial0/5, P23 aceptados0/9 intactos. P24 inicia implementación acotada de contención por nueva autorización urgente; no se aceptan sus seis criterios ni se acredita SLA/carga máxima. Sin DDL, seeds, servicios nuevos ni escrituras SIIE. Sin correo ni apagado nuevos.
