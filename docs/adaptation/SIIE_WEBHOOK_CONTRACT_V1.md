# Entrega al desarrollador de SIIE · Webhook y volante PDF de PRE-ICFES

Fecha: 25 de noviembre de 2026. Documento único y autónomo para implementar la recepción de preinscritos/inscritos y acordar la generación de volantes de PRE-ICFES. Los ejemplos contienen datos sintéticos; no son registros para insertar en producción.

## Estado y responsabilidades

| Componente | Estado y responsable |
|---|---|
| Receptor del webhook v1 | Implementado y publicado en RinovaPlus; firma configurada en Runtime y recepción habilitada el 25Nov2026 con etapa Calificación. Primer evento real verificado aún pendiente en este corte. |
| Emisor SIIE → RinovaPlus | El desarrollador de SIIE debe implementarlo después del guardado confirmado, con outbox y reintentos persistentes. No se presupone que los formularios ya emitan eventos. |
| Clave de llamadas RinovaPlus → SIIE | Se conserva la clave única existente, enviada como `X-API-Key` desde el backend. |
| Firma del webhook SIIE → RinovaPlus | Secreto dedicado `SIIE_WEBHOOK_SECRET` guardado por el titular en Runtime de RinovaPlus. SIIE debe usar exactamente el mismo valor entregado por canal privado; falta corroborarlo con el primer evento firmado. |
| Generación, consulta y descarga del volante | Contrato pendiente de SIIE. Las rutas de la sección de volantes son propuestas para acordar, no endpoints existentes o verificados. |
| Envío del PDF al interesado | Pendiente de integrar en RinovaPlus cuando SIIE entregue el contrato de pagos y pase el piloto de identidad/orden/PDF. El webhook actual guarda y clasifica; su acuse no significa que envió un mensaje. |

El piloto inicial es exclusivamente PRE-ICFES. Preinscripción, inscripción, matrícula académica, volante generado y pago confirmado son estados diferentes. Este trabajo no crea cobros, usuarios Moodle ni accesos institucionales.

## Dirección y activación

`POST https://app.rinovaplus.com/hooks/siie/v1`

El receptor requiere `SIIE_WEBHOOK_SECRET` en Runtime del backend y recepción habilitada en **Admisiones → SIIE → Inscripción y webhook** con una etapa inicial existente. Hasta entonces rechaza la recepción; no confirma eventos sin guardarlos. Esta clave firma la conexión entrante. `SIIE_API_TOKEN` sigue siendo la clave única existente para todas las llamadas salientes de RinovaPlus a SIIE.

El secreto de firma debe tener entre 32 y 512 caracteres ASCII sin espacios. Se recomienda generar 32 bytes aleatorios y representarlos como 64 caracteres hexadecimales. Ambos extremos usan los bytes UTF-8 de **ese mismo texto**, sin decodificarlo como hexadecimal. Guardarlo en configuración protegida de SIIE y como variable Runtime del backend de RinovaPlus, sin Build time; después desplegar el backend y habilitar la recepción. No incluir claves reales en este documento, repositorio, chat ni logs.

La URL es exacta: sin parámetros de consulta ni claves en la dirección. No requiere login de navegador ni cookies; la autenticación de la llamada entrante es su firma HMAC. No sustituirla por `X-API-Key`.

Emitir **un evento por persona y cambio confirmado**, después del commit de SIIE. Una lista se descompone en eventos individuales. No enviar arrays de personas, documentos adjuntos, información médica, contraseñas, datos de pago ni el formulario completo. Para recuperar históricos debe acordarse una lectura paginada o una emisión inicial controlada con identificadores estables.

## Dónde guardar el secreto en SIIE

El secreto pertenece a la configuración privada del **servidor que ejecuta el emisor del webhook**. No es un campo del formulario, una contraseña de estudiante ni un parámetro de la API de inscripción. RinovaPlus no conoce ni modifica la configuración interna del servidor SIIE.

Preferentemente, configurar una variable de entorno de servidor llamada `SIIE_WEBHOOK_SECRET` y leerla desde el proceso emisor:

```csharp
string webhookSecret = Environment.GetEnvironmentVariable("SIIE_WEBHOOK_SECRET");
if (string.IsNullOrWhiteSpace(webhookSecret))
    throw new InvalidOperationException("Falta configurar la firma del webhook.");
```

Si SIIE usa ASP.NET Framework y su mecanismo privado habitual es `web.config`, el desarrollador puede usar `appSettings` en el servidor, con el valor entregado por canal privado, y leerlo con `System.Configuration.ConfigurationManager.AppSettings["SIIE_WEBHOOK_SECRET"]`. No añadir el valor real al repositorio ni a un archivo descargable desde el sitio. El mecanismo elegido debe estar disponible para el proceso que despacha la outbox; si cambia su entorno, reiniciar o reciclar ese proceso según el alojamiento.

En **Coolify → backend RinovaPlus → Environment Variables**, el titular debe guardar exactamente el mismo valor como `SIIE_WEBHOOK_SECRET`, sólo Runtime y sin Build time. Después desplegar el backend y comprobar el panel de preparación antes de habilitar la recepción. La clave actual `SIIE_API_TOKEN` no se reemplaza. El emisor envía únicamente la firma calculada en `X-SIIE-Signature`, nunca el secreto.

## Firma

Encabezados únicos:

```text
Content-Type: application/json
X-SIIE-Timestamp: <segundos Unix actuales>
X-SIIE-Signature: sha256=<hexadecimal SHA-256 en minúsculas>
```

Calcular HMAC-SHA256 con la clave compartida sobre estos bytes exactos:

```text
UTF8("rinovaplus-siie-v1." + timestamp + ".") + cuerpo_JSON_UTF8_original
```

La ventana de la firma es de cinco minutos. Sin claves en la URL. No registrar firma, clave, cuerpo, cédulas ni datos personales en logs. Mantener HTTPS. No volver a serializar el cuerpo después de firmarlo.

El timestamp es un número decimal de segundos Unix, no milisegundos. La firma tiene el prefijo literal `sha256=` y 64 caracteres hexadecimales en minúsculas. Enviar una sola instancia de cada encabezado. Serializar JSON UTF-8 sin BOM, firmar y transmitir el mismo arreglo de bytes. Mantener sincronizado el reloj del servidor SIIE.

Ejemplo para el desarrollador de SIIE, sin credenciales reales:

```csharp
// Imports: System, System.Globalization, System.Linq,
// System.Net.Http, System.Net.Http.Headers, System.Security.Cryptography, System.Text.
// webhookSecret se obtiene de configuración protegida; json ya está serializado.
byte[] body = Encoding.UTF8.GetBytes(json);
string timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture);
byte[] prefix = Encoding.UTF8.GetBytes("rinovaplus-siie-v1." + timestamp + ".");
byte[] signedBytes = prefix.Concat(body).ToArray();
byte[] signature;
using (var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(webhookSecret)))
    signature = hmac.ComputeHash(signedBytes);
string header = "sha256=" + BitConverter.ToString(signature).Replace("-", "").ToLowerInvariant();
using (var request = new HttpRequestMessage(HttpMethod.Post,
    "https://app.rinovaplus.com/hooks/siie/v1"))
{
    request.Content = new ByteArrayContent(body);
    request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
    request.Headers.Add("X-SIIE-Timestamp", timestamp);
    request.Headers.Add("X-SIIE-Signature", header);
    // httpClient es reutilizable, tiene timeout y no sigue redirecciones.
    using (var response = await httpClient.SendAsync(request))
    {
        // 200: confirmar acuse y retirar de outbox.
        // Timeout/429/503: conservar evento y programar otro intento.
        // Revisar otros estados según la tabla de errores; no registrar el cuerpo.
    }
}
```

## Diagnóstico de un 403

La firma se verifica antes de validar el JSON. Comprobar la respuesta constante `siie_webhook_signature_rejected` y, en los logs privados de RinovaPlus, `siie_webhook_rejected`: distingue formato, `clock_skew`, `signature_mismatch` o ambos. El proxy registra sólo el resultado HTTP y duración como `siie_webhook_http`. No registrar claves, firmas ni cuerpo para depurar.

**Comprobación productiva del 25Nov2026:** el backend registró `reason=clock_skew skew_seconds=-10809`. En ese intento la firma coincide con la clave configurada, pero el timestamp está 3 horas y 9 segundos adelantado. El proxy confirmó 403 del backend. No rotar la clave por este rechazo ni ampliar la ventana. Sincronizar el reloj del servidor SIIE y revisar la conversión UTC; todavía no acredita aceptación/guardado del evento.

El emisor debe comprobar su reloj UTC. Para cada intento, `DateTimeOffset.UtcNow.ToUnixTimeSeconds()` produce el encabezado Unix en segundos. No convertir a milisegundos, sumar horas, escribir una fecha ISO en ese encabezado ni reutilizar el timestamp de un intento antiguo. La firma se recalcula sobre el mismo cuerpo UTF-8 y el timestamp nuevo. La ventana permitida sigue siendo300segundos.

`occurred_at` es otra cosa: la fecha UTC real del guardado original, conservada al reintentar. No añadir `Z` a una hora local sin convertirla correctamente. El ensayo16922 mostró una fecha casi tres horas futura, que debe corregirse en origen; de lo contrario recibirá422 después de resolver la firma. No cambiar arbitrariamente la fecha de un evento ya aceptado con el mismo GUID. Para el ensayo rechazado, corregirlo en la outbox antes de la primera aceptación y conservar su referencia; si ya hubiera un200 confirmado, conciliar antes de modificar contenido.

## Evento de preinscripción

Los identificadores siguientes son sintéticos. Los reales proceden de las filas confirmadas de SIIE, nunca de un contador del navegador.

```json
{
  "schema_version": "siie-crm-event-v1",
  "event_id": "4f6df394-1b6d-44c8-a16b-9f047b5da773",
  "event_type": "pre_registration.created",
  "occurred_at": "2026-11-25T16:00:00Z",
  "sequence": 1,
  "documento": "ENSAYO123",
  "idPreinscripcion": 101,
  "idOferta": 201,
  "idPeriodo": 301,
  "programa": "PRE-ICFES",
  "jornada": "Sábados · Mañana",
  "persona": {
    "nombres": "NOMBRE DE ENSAYO",
    "primerApellido": "PRUEBA",
    "segundoApellido": "",
    "celular": "3000000000",
    "correo": "ensayo@example.invalid",
    "ciudad": "Santa Marta"
  }
}
```

Campos comunes: `schema_version`, GUID global `event_id`, `event_type`, `occurred_at` con zona, `sequence` entero positivo, `idOferta` e `idPeriodo` nativos positivos. El titular confirma que el formulario de preinscripción ya exige cédula: **SIIE debe enviar `documento` también en el flujo normal de preinscripción**. Es alfanumérico de hasta 16 caracteres y siempre obligatorio para aspirante/inscripción/documentos. El receptor tolera su ausencia únicamente en eventos excepcionales de preinscripción para conservar la referencia técnica, sin corroborar identidad ni autorizar acceso privado. `idOferta` es `ACProgramaOfrecido.Id_PrgOfrecido`, no el programa base ni el identificador comercial compuesto. Los campos desconocidos se rechazan.

`idPreinscripcion` es la referencia estable para evitar duplicados, aunque la cédula esté presente; no sustituye su validación. Cuando una preinscripción se convierta en inscripción, conservar ese ID en el evento junto a `idEstudiante`, `idInscripcion` y el documento corroborado por SIIE. No reutilizarlo para otra persona. Un formato de documento no admitido devuelve 422; un documento diferente del ya vinculado devuelve 409 `siie_webhook_person_conflict` para revisión. La referencia técnica permite localizar el caso y corregirlo, pero no dar por válido un número mal escrito ni comprobar su existencia en un registro oficial. Si no se conserva la referencia previa, una coincidencia sólo por teléfono requiere la revisión de vínculo prevista más abajo.

`sequence` debe crecer para una misma persona/documento **a través de todos sus tipos de evento y ofertas**. El emisor puede usar un número global persistente de su outbox. No reiniciarlo por intento ni por proceso. `occurred_at` es la fecha original del cambio; no el momento del reintento. El reloj de firma sí se actualiza en cada envío.

| Evento | Referencias adicionales requeridas |
|---|---|
| `pre_registration.created`, `pre_registration.updated` | `idPreinscripcion`, `persona` |
| `applicant.created` | `idAspirante`, `persona`; corresponde al aspirante, no a una inscripción |
| `registration.created`, `registration.updated` | `idEstudiante`, `idInscripcion`, `persona` |
| `documents.updated` | `idEstudiante`; `documentos` puede contener hasta 18 IDs de tipos, sin archivos ni rutas |

Para `registration.created` sustituir el tipo de evento del ejemplo, usar un nuevo `event_id`, incrementar `sequence` y añadir `idEstudiante` e `idInscripcion` realmente confirmados. Los nombres tienen límite 100/30/30; celular 23; correo 50 y ciudad 100. `programa` y `jornada` son etiquetas del catálogo de SIIE, no instrucciones libres del solicitante.

Ejemplo de inscripción posterior de la misma persona; conservar la referencia previa:

```json
{
  "schema_version": "siie-crm-event-v1",
  "event_id": "729940e3-392e-4efa-a6e6-9332a9bce103",
  "event_type": "registration.created",
  "occurred_at": "2026-11-25T16:05:00Z",
  "sequence": 2,
  "documento": "ENSAYO123",
  "idPreinscripcion": 101,
  "idEstudiante": 401,
  "idInscripcion": 501,
  "idOferta": 201,
  "idPeriodo": 301,
  "programa": "PRE-ICFES",
  "jornada": "Sábados · Mañana",
  "persona": {
    "nombres": "NOMBRE DE ENSAYO",
    "primerApellido": "PRUEBA",
    "segundoApellido": "",
    "celular": "3000000000",
    "correo": "ensayo@example.invalid",
    "ciudad": "Santa Marta"
  }
}
```

Los IDs son enteros JSON positivos, no etiquetas ni cadenas numéricas. `sequence` también es un entero. `occurred_at` conserva el instante original con zona horaria; el timestamp de la firma representa cada intento actual. Campos desconocidos, claves JSON duplicadas y tipos incorrectos se rechazan. No añadir al evento v1 propiedades de volante, PDF o pago: no forman parte de este esquema.

## Confirmación y reintentos

Una respuesta HTTP 200 confirma que el recibo y su clasificación quedaron guardados en RinovaPlus. Ejemplo:

```json
{"received":true,"duplicate":false,"event_id":"4f6df394-1b6d-44c8-a16b-9f047b5da773","projection":"created"}
```

`projection`: `created` crea contacto; `linked` actualiza el vínculo confirmado; `review_required` conserva el evento para revisión de identidad; `stale_ignored` conserva el recibo sin reemplazar una ficha más reciente. Ninguna significa pago, matrícula académica ni mensaje entregado.

- Repetir el mismo evento devuelve `duplicate:true` sin crear otro contacto. Conservar GUID, contenido y secuencia; recalcular únicamente timestamp/firma. El mismo GUID con contenido distinto devuelve 409 `siie_webhook_event_conflict` y necesita revisión.
- Ante 429/503, timeout o pérdida del acuse, conservar el evento en una outbox de SIIE y reintentar con espera creciente, respetando `Retry-After`. No perder el registro local porque RinovaPlus esté temporalmente ocupado.
- 403: revisar firma, clave y reloj. 413: máximo 64 KiB. 415: JSON requerido. 422: corregir contrato. No reenviar indefinidamente los errores de contrato.
- La autenticación usa el cuerpo original. La deduplicación compara el objeto validado, por lo que cambiar sólo el espaciado del JSON no duplica personas.

SIIE debe guardar el evento pendiente en una **outbox dentro de la misma transacción que guarda la preinscripción/inscripción**, y transmitirlo únicamente cuando esa transacción esté confirmada. Así no se pierde un cambio si el proceso se detiene entre guardar la persona y llamar al webhook. Un rollback no debe producir evento. Para la entrega usar espera creciente con variación aleatoria y conservar los eventos pendientes tras reiniciar el proceso. No seguir redirecciones con el cuerpo firmado.

Antes de retirar un evento, comprobar HTTP 200, `received:true` y que `event_id` corresponda al enviado. `duplicate:true` con el mismo ID también es un acuse válido. Ante HTTP 5xx transitorio o pérdida de respuesta, conservar el evento; no crear otro GUID para el mismo cambio. Registrar sólo ID de evento, intento, código HTTP y referencia técnica de soporte. Un 409 por conflicto de contenido o documento va a revisión, no a una cola infinita.

## Clasificación y coincidencias

En el CRM, origen **SIIE** y clasificación **Preinscrito** o **Inscrito · Sin promociones**, con filtros separados de **Importados · Excel** y **Redes sociales**. No se concede consentimiento comercial. Las conversaciones de importación sin entradas reales no aparecen como atención recibida del Inbox.

Un vínculo de documento ya establecido se conserva sin sobrescribir nombres/teléfonos editados por un asesor. Una coincidencia sólo por teléfono se conserva para revisión; no fusiona personas. Admisiones puede confirmar el candidato desde el detalle del evento. Una inscripción confirmada excluye promociones incluso para candidatos con ese teléfono mientras se revisa la vinculación. También se comprueba la exclusión al despachar campañas y seguimientos CRM; una nueva preinscripción o un evento antiguo no reabre promociones.

Los datos de registro se conservan cifrados en el almacén institucional existente. No se convierten en notas, prompts, conocimiento de IA ni archivos públicos. La política definitiva de retención y el piloto con datos autorizados forman parte de la aceptación pendiente de P23.

## Volante PRE-ICFES: contrato que falta entregar

El titular aprobó preparar: **inscripción corroborada → vínculo seguro con conversación → elección expresa contado/financiado → volante SIIE → PDF privado al mismo contacto verificado**. No se ha implementado generación ni envío de volantes; las cuatro rutas de Registration 2 ni el catálogo adicional de GuiaImplementacionCRM documentan esa capacidad.

SIIE debe confirmar los nombres y publicar las cinco operaciones siguientes, o indicar endpoints existentes que cumplan íntegramente esas funciones. **Los nombres de esta tabla son propuestas; no se deben llamar hasta recibir el contrato definitivo y verificar su publicación.**

Base de API configurada actualmente: `https://siieplus.online/SIIEWebPlus`. Conservar esa carpeta. Todas las rutas propuestas son relativas a esa base y usarían `X-API-Key` con la clave única actual, previa confirmación de sus permisos. Nunca enviar la clave al navegador público ni como query string.

| Operación faltante | Método y ruta propuestos, por confirmar | Entrada y salida mínimas |
|---|---|---|
| Corroborar inscripción antes de matrícula | `POST /Api/CRM/v1/InscripcionConsulta.aspx` | Consulta de lectura por `idInscripcion` o `idPreinscripcion`, con filtros de oferta/período. Si hace falta buscar por documento, enviarlo en JSON protegido, no en URL. Devolver IDs nativos, documento, nombre, contacto registrado, oferta/período, estado de inscripción y referencia previa. Incluir inscripciones del formulario público todavía no matriculadas. Una coincidencia ambigua no se resuelve tomando la primera fila. |
| Consultar planes vigentes de PRE-ICFES | `GET /Api/CRM/v1/PlanesPagoPreIcfes.aspx` | `idInscripcion`, `idOferta`, `idPeriodo`. Devolver planes permitidos para esa inscripción: ID de plan, modalidad contado/financiado, revisión, moneda, total, abono, cuotas, fechas, vigencia de la cotización y reglas de promoción. |
| Generar el volante | `POST /Api/CRM/v1/VolanteGenerar.aspx` | `operationId` UUID persistente, `idInscripcion`, `idOferta`, `idPeriodo`, ID de plan y revisión de la cotización elegida. Devolver ID estable de volante/orden, estado, referencias de inscripción/plan, revisión, importe y moneda. SIIE valida y calcula los valores; no acepta un importe libre impuesto por el chat. |
| Consultar resultado sin regenerar | `GET /Api/CRM/v1/VolanteConsulta.aspx` | Consulta por `operationId` o por ID de volante. Devolver el mismo resultado confirmado, estado, vencimiento, disponibilidad del PDF y su referencia de versión. Debe funcionar tras timeout del POST. |
| Descargar el PDF | `GET /Api/CRM/v1/VolantePdf.aspx` | ID del volante y, si aplica, versión. Devolver el archivo binario autenticado con `Content-Type: application/pdf`, ligado inequívocamente a la orden consultada. |

### Reglas del contrato de pagos propuesto

- **Fuente de precios:** SIIE devuelve importes y fechas vigentes. RinovaPlus no incrusta tarifas fijas de este documento, no concede descuentos nuevos ni aprueba reajustes. Documentar si los importes se expresan en pesos enteros, unidades menores o decimales; evitar floats ambiguos. Declarar `COP` y la regla de redondeo. Distinguir total del plan, importe del volante y saldo, especialmente si el volante corresponde sólo al abono inicial.
- **Plan explícito:** la persona debe confirmar contado o financiado, y el plan concreto cuando haya varios. Una preinscripción recibida no autoriza generar una orden. Un dato de precio o fecha ausente se confirma con el área responsable; no se inventa ni se sustituye por cero.
- **Vigencia:** SIIE debe indicar revisión y vencimiento de la cotización. Si cambia precio, plan u oferta, rechazar la solicitud obsoleta y pedir nueva confirmación; no generar automáticamente con otra tarifa.
- **Idempotencia de generación:** `operationId` se registra de forma duradera junto a la orden. Repetir la misma clave y los mismos parámetros devuelve la misma orden; la misma clave con parámetros distintos devuelve conflicto. Un timeout conserva la clave original y se concilia por consulta antes de decidir otro envío. Es un requisito nuevo del endpoint de volante; no se presupone que las rutas actuales de inscripción lo tengan.
- **Resultado incierto:** distinguir «no existe», «procesando» y «no se pudo determinar». Una consulta con error no demuestra que el POST no creó el volante. Si la generación es asíncrona, documentar HTTP 202, estados, cadencia y `Retry-After`; nunca generar otra orden sólo porque el PDF aún no esté listo.
- **PDF:** definir máximo de bytes, tamaño esperado, hash SHA-256 y versión, vinculados al mismo volante. RinovaPlus verificará tamaño, tipo, firma de archivo PDF e integridad antes de enviar. La descarga debe exigir autenticación y responder en binario; no devolver una ruta de IIS, enlace público permanente o archivo codificado dentro del webhook de 64 KiB. El nombre descargable no debe incluir documento ni otros identificadores privados.
- **Vencimiento y reemplazo:** explicar cuándo se puede anular, regenerar o reemplazar un volante, si cambia el plan y qué orden queda vigente. Ningún reemplazo automático ante un resultado incierto.
- **Pago:** generar/descargar un PDF no confirma recaudo ni matrícula. Si se incorpora pago confirmado, acordar otra operación o una ampliación versionada de eventos. `payment.confirmed` y datos de volante **no están admitidos** por el webhook v1 actual.

### Flujo previsto en RinovaPlus

1. Recibir `registration.created`/`.updated`, conservar recibo y clasificar como inscrito sin promociones. Una preinscripción mantiene su clasificación previa.
2. Corroborar en SIIE la inscripción y resolver de forma segura el vínculo con la conversación.
3. Mostrar las opciones vigentes y obtener elección expresa de contado o financiado. Conservar IDs, revisión y confirmación de esa elección.
4. Guardar una intención duradera con `operationId` antes de pedir a SIIE la generación del volante.
5. Consultar la orden hasta conocer el resultado; descargar el PDF autenticado cuando esté listo.
6. Validar que PDF, versión, importe, inscripción y plan correspondan. Enviar una sola vez al contacto verificado, conservando los recibos reales del canal.
7. Ante envío de mensajería incierto, consultar y conciliar antes de repetir. Mantener Humano, restricciones de contacto y ventanas/plantillas del canal.

Confirmar el nombre ayuda al trato en el chat; nombre o cédula por sí solos no autorizan abrir una ficha ni entregar un PDF. Coincidencia dudosa de teléfono, perfil nuevo u otra persona requieren validación adicional/revisión. El mensaje transaccional se preparará con las reglas y ventanas reales del canal, conservando Humano y No contactar; no se enviará como promoción a inscritos.

## Entrega requerida al desarrollador de SIIE

Para conectar y verificar ambos recorridos, devolver en un solo contrato:

1. Confirmación de implementación del emisor, tabla/outbox persistente, eventos y continuidad `idPreinscripcion` → `idEstudiante`/`idInscripcion`. Medio privado para configurar el secreto compartido; no su valor en documentación.
2. URLs y métodos definitivos de las cinco operaciones de inscripción/plan/volante/PDF, con permisos de la clave existente y entorno de pruebas. Señalar si alguna ya existe y su ruta exacta.
3. JSON de solicitud/respuesta de éxito, tipos, campos obligatorios, valores nativos/estados y ejemplos ficticios. Para PDF, cabeceras y forma de consultar tamaño/hash/versión.
4. HTTP y códigos de error para inexistencia, conflicto, plan obsoleto, validación, límite temporal, indisponibilidad y resultado incierto; incluir correlación y `Retry-After` cuando apliquen. No devolver mensajes SQL ni trazas privadas.
5. Garantía y pruebas de idempotencia, consulta por operación, vencimiento/anulación/reemplazo y generación asíncrona si aplica.
6. Datos de ensayo autorizados y mecanismo para conciliar/limpiar el piloto. No usar documentación privada de terceros ni inventar inscripciones en producción.

## Comprobación conjunta antes de activar

| Prueba | Resultado esperado |
|---|---|
| Preinscripción normal con documento | Un recibo y una ficha SIIE Preinscrito. |
| Reintento del mismo evento | `duplicate:true`, sin duplicar la ficha. |
| Firma incorrecta o reloj fuera de ventana | Rechazo 403, sin guardar el evento. |
| Mismo UUID con contenido diferente | Conflicto 409 y revisión. |
| Inscripción de la misma persona | Mantiene la continuidad y queda Inscrito · Sin promociones. |
| Evento antiguo o cambio de documento vinculado | Sin sobrescritura indebida; recibo antiguo ignorado o conflicto para revisión, respectivamente. |
| Mismo celular de otra persona | Revisión de vínculo; sin fusión automática ni entrega de datos privados. |
| Caída entre commit SIIE y entrega | Outbox conserva el evento y recupera la entrega sin otro GUID. |
| Volante con plan confirmado | Una orden y un PDF de esa inscripción; importes y vencimiento coherentes. |
| Timeout al generar y repetición de clave | Consulta recupera la misma orden, sin segundo cobro/volante. |
| Cambio de parámetros con la misma clave | Conflicto; no altera la orden original. |
| PDF pendiente, inválido o de otra orden | No se envía al interesado; se conserva para conciliación. |

Estado comprobado 25Nov2026: secreto configurado en Runtime y recepción habilitada con Calificación, confirmado después de recargar. El formulario público PRE-ICFES registró un ensayo sintético autorizado con número 16922; todavía no se observó su evento verificado en RinovaPlus. SIIE debe comprobar la outbox de ese guardado y entregar el mismo evento firmado a la URL indicada, aportando sólo `event_id`, intento y respuesta HTTP para soporte. No crear otra inscripción para reintentar la notificación.

Pendientes: primera entrega real firmada y conciliación del piloto, continuidad preinscrito→inscrito, retención y contrato definitivo del volante/PDF; después implementar y comprobar la orden y el envío privado del PDF. Los envíos finales de RinovaPlus a SIIE siguen desactivados. P23 continúa 0/9 aceptados, sin cierre funcional completo. Ver [ensayo del formulario](SIIE_WEBHOOK_PILOT_20261125.md).
