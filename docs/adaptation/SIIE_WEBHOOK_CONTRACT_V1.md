# SIIE → RinovaPlus · Contrato del webhook v1

Preparado el 25 de noviembre de 2026 por solicitud del titular. El emisor de SIIE debe implementar este contrato; no se presupone que sus formularios ya emitan estos eventos.

## Dirección y activación

`POST https://app.rinovaplus.com/hooks/siie/v1`

El receptor requiere `SIIE_WEBHOOK_SECRET` en Runtime del backend y recepción habilitada en **Admisiones → SIIE → Inscripción y webhook** con una etapa inicial existente. Hasta entonces rechaza la recepción; no confirma eventos sin guardarlos. Esta clave firma la conexión entrante. `SIIE_API_TOKEN` sigue siendo la clave única existente para todas las llamadas salientes de RinovaPlus a SIIE.

Emitir **un evento por persona y cambio confirmado**, después del commit de SIIE. Una lista se descompone en eventos individuales. No enviar arrays de personas, documentos adjuntos, información médica, contraseñas, datos de pago ni el formulario completo. Para recuperar históricos debe acordarse una lectura paginada o una emisión inicial controlada con identificadores estables.

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

Ejemplo para el desarrollador de SIIE, sin credenciales reales:

```csharp
byte[] body = Encoding.UTF8.GetBytes(json);
string timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture);
byte[] prefix = Encoding.UTF8.GetBytes("rinovaplus-siie-v1." + timestamp + ".");
byte[] signedBytes = prefix.Concat(body).ToArray();
byte[] signature;
using (var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(webhookSecret)))
    signature = hmac.ComputeHash(signedBytes);
string header = "sha256=" + BitConverter.ToString(signature).Replace("-", "").ToLowerInvariant();
// Enviar body sin modificar con X-SIIE-Timestamp y X-SIIE-Signature.
```

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

## Clasificación y coincidencias

En el CRM, origen **SIIE** y clasificación **Preinscrito** o **Inscrito · Sin promociones**, con filtros separados de **Importados · Excel** y **Redes sociales**. No se concede consentimiento comercial. Las conversaciones de importación sin entradas reales no aparecen como atención recibida del Inbox.

Un vínculo de documento ya establecido se conserva sin sobrescribir nombres/teléfonos editados por un asesor. Una coincidencia sólo por teléfono se conserva para revisión; no fusiona personas. Admisiones puede confirmar el candidato desde el detalle del evento. Una inscripción confirmada excluye promociones incluso para candidatos con ese teléfono mientras se revisa la vinculación. También se comprueba la exclusión al despachar campañas y seguimientos CRM; una nueva preinscripción o un evento antiguo no reabre promociones.

Los datos de registro se conservan cifrados en el almacén institucional existente. No se convierten en notas, prompts, conocimiento de IA ni archivos públicos. La política definitiva de retención y el piloto con datos autorizados forman parte de la aceptación pendiente de P23.

## Piloto PRE-ICFES aprobado: siguiente contrato de SIIE

El titular aprobó preparar: **inscripción corroborada → vínculo seguro con conversación → elección expresa contado/financiado → volante SIIE → PDF privado al mismo contacto verificado**. No se ha implementado generación ni envío de volantes; las cuatro rutas de Registration 2 ni el catálogo adicional de GuiaImplementacionCRM documentan esa capacidad.

El desarrollador debe aportar:

1. Consulta de inscripción que permita corroborar IDs, documento, oferta, período y teléfono **antes de matrícula**, incluyendo solicitudes creadas por el formulario público. La consulta actual de estudiante matriculado no demuestra que incluya estos nuevos inscritos.
2. Modalidades/planes disponibles de PRE-ICFES, IDs, valores, fechas y revisión. RinovaPlus no calculará un plan nuevo ni aprobará un reajuste por su cuenta.
3. Operación para generar el volante con una clave de idempotencia, `idInscripcion`, oferta/período y modalidad/plan confirmado. Debe devolver ID estable de orden, estado e importe/moneda.
4. Consulta por clave de idempotencia/orden para conciliar un timeout sin generar un segundo volante, y reglas de vencimiento/anulación/reemplazo.
5. Descarga autenticada del PDF, tamaño, MIME, vínculo exacto con la orden e integridad. No una URL pública reutilizable ni una ruta física de IIS.
6. Estados/evento de pago confirmado, si se integrará después; generar o descargar un volante no equivale a pago.

Confirmar el nombre ayuda al trato en el chat; nombre o cédula por sí solos no autorizan abrir una ficha ni entregar un PDF. Coincidencia dudosa de teléfono, perfil nuevo u otra persona requieren validación adicional/revisión. El mensaje transaccional se preparará con las reglas y ventanas reales del canal, conservando Humano y No contactar; no se enviará como promoción a inscritos.
