# SIIE: acceso y detalle comercial pendiente

Comprobación autorizada del18-11-2026, zonaAmerica/Bogota. Sólo HTTPS GET desde el backend de RinovaPlus y su UI. No se inspeccionaron SQL/logs internos de SIIE, no se escribieron seguimientos, no se matriculó ni se efectuó pago alguno. Las claves no se incluyen en esta evidencia.

## Acceso confirmado

- El token original de Catálogo guardado por el titular funciona en `Commercial/Programs.aspx` y `Commercial/ProgramOffers.aspx`.
- Programas: dos páginas consultadas correctamente. Software: ID143, `DESARROLLO DE SOFTWARE Y APLICACIONES MOVILES`, DSAM, Escuela de TIC; la fuente declara cuatro niveles, no un número de meses.
- Ofertas de Software: cuatro páginas en RinovaPlus; referencias de2016-A a2027-A. Se conservan los IDs completos con nivel, incluidos `1080-n1` para2026-B. La paginación es keyset sobre catálogo vivo, no snapshot inmutable.
- Ese mismo token fue rechazado al consultar `Periodos.aspx`. Falta la clave GENERAL de ApiSecurity para Admisiones. No persistimos el token de Catálogo como clave General ni afirmamos acceso a aspirantes.

## Incidencia del detalle financiero

Base: `https://siieplus.online/SIIEWebPlus/Api/CRM/v1/`.

| Consulta | Respuesta directa de SIIE | Correlación |
|---|---|---|
| `Commercial/Offer.aspx?offer_id=338-n1` | HTTP503, `catalog_unavailable`, `quotable=false`, sin `partial_offer` | `39b0a401f0564399854d80675d940f6f` |
| `Commercial/Offer.aspx?offer_id=1080-n1` | HTTP503, `catalog_unavailable`, `quotable=false`, sin `partial_offer` | `488bd06b491747fea60ec1f101d6345a` |

La consulta de `281-n1` también terminó en `siie_catalog_unavailable` del consumidor; para ese ID no se observó directamente el status del origen. No inferimos que fuera otro503 sin medirlo.

La guía entregada describe422`source_data_incomplete` con un `partial_offer` para toda oferta resoluble. Las pruebas indicadas reciben503sin ese objeto. Los listados y la autenticación sí pasan, por lo que no procede reemplazar la clave ni atribuir el error a una suma de cuotas de RinovaPlus. Tampoco podemos precisar la excepción SQL interna sin los logs del proveedor.

El responsable de SIIE debe localizar las dos correlaciones en sus logs, revisar la ejecución de `Commercial/Offer.aspx`/CrmCommercialApi, disponibilidad y versión de sus consultas y manejo de cardinalidad/errores. Debe informar la causa real y la corrección; no desactivar autenticación ni devolver errores SQL privados al cliente. Repetir después ambas lecturas para comprobar el422parcial documentado o un200completo válido.

## Antes de aceptar cotizaciones o Admisiones

1. Proporcionar la clave General de Admisiones por un canal privado y guardarla directamente en Coolify como `SIIE_ADMISSIONS_API_TOKEN`, sólo Runtime. Nunca en chat ni Git.
2. Corregir el503 y devolver datos de origen trazables. La sola presencia de filas no acredita sede, requisitos, vigencia comercial, condiciones de planes ni costo completo.
3. Entregar dos ofertas reales completas y vigentes para revisar contado, alcance por nivel/programa, extras, abono, cada cuota, vencimientos y total. Fechas académicas no equivalen a vigencia financiera.
4. Probar después aspirantes y su historial con la clave General. Confirmación de origen no equivale a matrícula. Estudiantes matriculados y cartera individual siguen sin rutas en el contrato recibido.

Estado de P16:0/5unidades aceptadas, con progreso parcial de acceso y paginación. La inspección no publica fichas a Gemini, no asocia personas por nombre y no habilita POST/PUT en SIIE.
