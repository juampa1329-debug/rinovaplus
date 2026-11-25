# Inbox: espera interna, continuidad y fechas confirmadas — 25Nov2026

El diagnóstico nativo del hilo autorizado confirma `storage_busy` en la primera parte de las 09:27:05 Bogotá; las cinco siguientes quedaron descartadas por no haber salido la anterior. La generación de Sonnet había concluido. Es distinto del saldo de IA y del límite HTTP del navegador. Las dos orientaciones manuales nuevas de las 09:42 y 09:43 quedaron **Entregado**, con el hilo devuelto a IA. No se reprodujeron las operaciones anteriores.

Los registros de producción previos al cambio muestran `55P03` al adquirir el bloqueo institucional, además de transacciones de escritura de aproximadamente 3,6–7,4 segundos. La reparación de la cola no demuestra por sí sola que se haya eliminado su causa; se añade duración y huella del SQL más lento y ubicación estática de código, sin parámetros, cuerpos SQL, credenciales ni datos de clientes, para localizar el trabajo que retiene el bloqueo.

## Cambios

- Una espera conocida **anterior al efecto externo** conserva el mismo trabajo en `queued`, libera la reserva y programa una revisión en cinco segundos. La siguiente parte sigue esperando. Al volver se comprueban otra vez cuenta, autoridad, conversación, ventana y modo Humano.
- Sólo el guardián previo al primer POST del transporte de texto nativo puede certificar esa condición una vez entrado en el transporte. Audio/media, transportes no acreditados y resultados inciertos no adquieren una autorización de repetición.
- La reserva sólo se reutiliza si la operación pendiente acredita `outbound_storage_wait`, sin efecto externo ni arrendamiento. Los fallos históricos `storage_busy` no se relanzan automáticamente.
- Las preguntas simultáneas sobre precios y comienzo de clases conservan la presentación revisada. Una fecha completa confirmada prevalece sobre respuestas antiguas; una vigencia inicial financiera vacía no convierte en desconocido el inicio de clases.

## PRE-ICFES

Ficha local revisión **6** guardada en la UI: tarifa regular **1.600.000 pesos**, **50%** de descuento de contado (**800.000 pesos**) hasta el **16/12/2026**; comienzo **13/02/2027** confirmado. Conserva G1 sábado mañana, G2 sábado tarde y G3 domingo mañana, 120 horas, plataforma/tutor/materiales y formulario oficial. La financiación mantiene abono y vigencia propios del 15/12/2026 y tres cuotas de 220.000; la instrucción recibida cambia la vigencia del descuento de contado, no autoriza inferir cambios en ese plan.

## Validación y límites del corte preparado

183 pruebas backend focalizadas pasan, seis excluidas reproducen el mismo fallo en HEAD previo `4cd2b8d`: un caso de contexto grande, una expectativa antigua de 34 guías frente a 37 y cuatro dobles de Cursor antiguos. Ruff pasa. No se declara suite completa verde. Pruebas nuevas cubren contención antes del guardián y en el guardián, un único envío posterior, liberación de reserva, fallo/timeout posterior al transporte, media, cambios de autoridad/contexto y las fechas dentro de una pregunta financiera.

Publicación y observación del nuevo diagnóstico aún pendientes en este corte. No acredita todo el histórico atendido, SLA, carga máxima, entrega perpetua ni nuevas aceptaciones de fases. Sin DDL, seeds, nuevos servicios, cambios de modelos o escrituras SIIE.
