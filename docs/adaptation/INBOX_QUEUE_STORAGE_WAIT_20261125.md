# Inbox: espera interna, continuidad y fechas confirmadas — 25Nov2026

El diagnóstico nativo del hilo autorizado confirma `storage_busy` en la primera parte de las 09:27:05 Bogotá; las cinco siguientes quedaron descartadas por no haber salido la anterior. La generación de Sonnet había concluido. Es distinto del saldo de IA y del límite HTTP del navegador. Las dos orientaciones manuales nuevas de las 09:42 y 09:43 quedaron **Entregado**, con el hilo devuelto a IA. No se reprodujeron las operaciones anteriores.

Los registros de producción previos al cambio muestran `55P03` al adquirir el bloqueo institucional, además de transacciones de escritura de aproximadamente 3,6–7,4 segundos. La reparación de la cola no demuestra por sí sola que se haya eliminado su causa; se añade duración y huella del SQL más lento y ubicación estática de código, sin parámetros, cuerpos SQL, credenciales ni datos de clientes, para localizar el trabajo que retiene el bloqueo.

## Cambios

- Una espera conocida **anterior al efecto externo** conserva el mismo trabajo en `queued`, libera la reserva y programa una revisión en cinco segundos. La siguiente parte sigue esperando. Al volver se comprueban otra vez cuenta, autoridad, conversación, ventana y modo Humano.
- Sólo el guardián previo al primer POST del transporte de texto nativo puede certificar esa condición una vez entrado en el transporte. Audio/media, transportes no acreditados y resultados inciertos no adquieren una autorización de repetición.
- La reserva sólo se reutiliza si la operación pendiente acredita `outbound_storage_wait`, sin efecto externo ni arrendamiento. Los fallos históricos `storage_busy` no se relanzan automáticamente.
- Las preguntas simultáneas sobre precios y comienzo de clases conservan la presentación revisada. Una fecha completa confirmada prevalece sobre respuestas antiguas; una vigencia inicial financiera vacía no convierte en desconocido el inicio de clases.

## PRE-ICFES

Ficha local revisión **7** guardada en la UI: tarifa regular **1.600.000 pesos**, **50%** de descuento de contado (**800.000 pesos**) hasta el **16/12/2026**; comienzo **13/02/2027** confirmado. Conserva G1 sábado mañana, G2 sábado tarde y G3 domingo mañana, 120 horas, plataforma/tutor/materiales y formulario oficial. La financiación mantiene abono y vigencia propios del 15/12/2026 y tres cuotas de 220.000; la instrucción recibida cambia la vigencia del descuento de contado, no autoriza inferir cambios en ese plan.

## Validación y límites del corte preparado

183 pruebas backend focalizadas pasan, seis excluidas reproducen el mismo fallo en HEAD previo `4cd2b8d`: un caso de contexto grande, una expectativa antigua de 34 guías frente a 37 y cuatro dobles de Cursor antiguos. Ruff pasa. No se declara suite completa verde. Pruebas nuevas cubren contención antes del guardián y en el guardián, un único envío posterior, liberación de reserva, fallo/timeout posterior al transporte, media, cambios de autoridad/contexto y las fechas dentro de una pregunta financiera.

Publicación y observación del nuevo diagnóstico aún pendientes en este corte. No acredita todo el histórico atendido, SLA, carga máxima, entrega perpetua ni nuevas aceptaciones de fases. Sin DDL, seeds, nuevos servicios, cambios de modelos o escrituras SIIE.


## Publicación y comprobación posterior

`f19cd38` publicado en backend `0u2vyjo9j5ymlluvsgfaosgh` (**Success**, 4m25s) y frontend `olik5czk0vq5l4aebwt2kdml` (**Success**, 25s). La muestra de logs nueva conserva esperas 55P03 durante el rollout 14:54:24–14:54:58 UTC; no se atribuyen al proveedor de IA. Los nueve procesos figuran **Al día** a las 09:57:49 Bogotá, sin trabajos de salida en queued/sending en ese corte. No implica que el histórico incierto o fallido esté resuelto.

Se localizaron otros dos turnos con el mismo `storage_busy`, de las 09:28 y 09:29: se enviaron dos orientaciones nuevas, ambas **Entregado**, y se restauró IA en ambos hilos. Total de este trabajo: cuatro mensajes entregados en tres hilos, sin repetir las colas antiguas. La revisión administrativa de últimas entradas sin operación de IA devolvió cero elegibles; ese filtro no incluye operaciones fallidas ni inciertas.

Prueba nativa aislada del especialista PRE-ICFES con Sonnet4.6 y un historial ficticio con fecha antigua/año desconocido: responde tarifa regular1.600.000, descuento50%800.000 hasta16Dic2026 e inicio13Feb2027. Mantiene el alcance separado de la financiación. 16.784 tokens de entrada,507 de salida,20.721ms; estimación USD0,057957. No escribió CRM, no envió mensajes y no cambió el agente activo. La revisión7 retira expresiones internas sobre el propietario de la presentación, conservando los hechos y su año.

61 pruebas adicionales de PostgreSQL/operación/seguimientos/fechas pasan, con solapamientos respecto de la selección anterior. El frontend añade recuperación coalescida de hasta dos GET adicionales (pausas1s/3s) sólo para storage_busy; mantiene429, permisos y mutaciones sin repetición. Una espera acreditada de salida se muestra **Esperando al servidor**, no como fallo ni invitación a reenviar. 15 pruebas frontend, tipos, ESLint y build institucional pasan; aviso histórico de bundle grande. La publicación de esta última ampliación visual se comprueba después del siguiente push.


## Causa de contención localizada y ajuste preparado

La telemetría publicada localizó `statement_id=c01a0c3f0050`: cálculo de cobertura de turnos en `reply_turns.snapshot`. Tardaba3559–3789ms por consulta en la muestra de15:00UTC y se repetía en lecturas y guardianes de envío; una transacción alcanzó8151ms. Dos subconsultas correlacionadas volvían a recorrer y convertir los JSON de todos los envíos de la cuenta para cada operación anterior.

Se sustituye por una sola agregación acotada a institución/cuenta/identidad, enlazada por operación. Un turno sólo se considera atendido si tiene al menos una parte y todas están aceptadas/enviadas/entregadas/leídas, o existe la decisión expresa confirmada de no responder. Partes en cola, fallidas, canceladas o inciertas conservan la consulta pendiente. Registros de otra identidad/cuenta/institución no acreditan cobertura. No se cambian bloqueos de autorización, límites HTTP, esquemas ni se crean índices.

171 pruebas backend focalizadas pasan, incluidas14 historias SQL ejecutadas en memoria con estados mixtos y registros ajenos y validación de sintaxis PostgreSQL. Selección solapada con las anteriores; Ruff pasa. La nueva consulta requiere publicación y observación real antes de atribuirle una mejora de latencia. Frontend466bc15 ya está Success44s, desplieguezqxp68nlc62cqrh9qwlycnj0.
