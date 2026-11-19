# P16 · Resultado real de la clave única y pendientes de SIIE

Comprobación del 19-11-2026 desde el backend publicado de RinovaPlus. Solicitudes GET acotadas al servidor autorizado, sin SQL directo, DDL ni escrituras SIIE. No se guardan claves ni datos de personas en este informe.

## La autenticación única funciona

El propietario guardó la clave original nueva en `SIIE_API_TOKEN`, sólo Runtime. El contenedor nuevo informa modo `unified`; no utilizó otra clave ni volvió a una credencial anterior. Las credenciales deliberadamente inválidas reciben 401 tanto en Periodos como en Commercial/Programs.

| Consulta | Resultado observado |
|---|---|
| Periodos | Ofrecido129, nombre2027-A; académico activo128. Selección ofrecida explícita, sin confundir ambos. |
| Periodos históricos | 34 registros. |
| EstadosSeguimiento | 11 estados oficiales. |
| FiltrosAdmisiones | 31 combinaciones de programa/jornada del período. |
| Aspirantes | Dos páginas de25; todas las filas de ambas páginas tienen al menos un contacto nativo. No se exportaron personas. |
| Aspirante | Ficha e identidad nativa comprobadas; historial de ese registro válido y vacío. |
| FiltrosEstudiantes | 6 programas,3 jornadas,3 niveles y1 estado observados. |
| Estudiantes | 8 registros del período129; los8 tienen algún contacto nativo. |
| Estudiante | Detalle nativo coincidente con el seleccionado y1 matrícula en el período. No se infiere vínculo con aspirantes. |
| ProgramOffers de Software143, período129 | 4 ofertas/niveles; primera1204-n1, segunda1204-n2. El adaptador valida el período explícito y acepta el listado. |

La clave no requiere otro reemplazo por los fallos siguientes. No se certifican por compartirla las escrituras de seguimiento/preinscripción ni las consultas Moodle ajenas a este recorrido CRM.

## Bloqueo 1: Programs aún omite el período del contrato nuevo

`GET /Api/CRM/v1/Commercial/Programs.aspx` y la misma consulta con `period_id=129` responden200 y25 elementos, pero sólo tienen estas claves raíz:

`schema_version`, `source_system`, `items`, `next_cursor`, `pagination`, `source_revision`, `generated_at`.

Faltan `period_id`, `offered_period_id` y `offered_period_source` documentados en la guía recibida. RinovaPlus presenta `siie_period_contract_required` en un modal y conserva sus datos; no afirma que un catálogo sin período pertenezca al ofrecido ni incorpora históricos por suposición.

Referencias del productor:

- Consulta predeterminada: `e39362247032433a859cf11ba2b72d83`.
- Consulta explícita129: `6cb5c083de954a2b911a672d0aa2c4cf`.

`ProgramOffers` sí identifica el período129 solicitado, pero todavía omite los metadatos `offered_period_id` y `offered_period_source` nuevos. Referencia inicial: `703cb771e84b4bf48e7339dd41fbd0d4`; lectura por el adaptador: `4e05ee371eed4b4b8927aa786dfe8113`.

**Acción del proveedor:** comparar los archivos efectivamente publicados de Commercial con la entrega del19-11, completar los campos de período y verificar que Programs filtra realmente la oferta del período. Devolver el período resuelto también cuando se use el predeterminado. No basta con publicar únicamente la autenticación compartida o cambiar el documento.

## Bloqueo 2: detalle financiero devuelve503, sin parcial

| Oferta real | HTTP/código | Referencia del productor |
|---|---|---|
| Software2027-A1204-n1 | 503 `catalog_unavailable`, `quotable=false`, sin `partial_offer`. | `899ca4ff10a040c2a4901613ea0b62f0` |
| Software2027-A1204-n2 | 503 `catalog_unavailable`, `quotable=false`, sin `partial_offer`. | `d0015fd1fa2b47c1b182c34278b88c0b` |
| Software2026-B1080-n1, contraste histórico | 503 `catalog_unavailable`, sin `partial_offer`. | `c40748f711e24e7b8ace7981b44be423` |

La guía prevé422 `source_data_incomplete` con datos parciales para requisitos de ingreso y condiciones financieras aún pendientes. El servidor no está entregando ese parcial: el503 impide siquiera revisar contado, abono, cuotas y fechas de las ofertas probadas.

**Acción del proveedor:** revisar los logs privados con las referencias anteriores y corregir el fallo de Commercial/Offer. Si los datos siguen incompletos, devolver422 con parcial/calidad conforme al contrato. Para cerrar la aceptación financiera de P16 hacen falta dos ofertas completas y revisables; no sustituir requisitos/condiciones por textos inventados ni vigencias por fechas académicas.

## Estado de aceptación

RinovaPlus está desplegado saludable y las consultas personales se validaron sin persistir filas en el CRM. El catálogo local de programas continúa vacío; no se publicaron precios ni hechos financieros para Gemini. **P16 sigue parcial,0/5 unidades completas aceptadas.** Acceso único y lecturas reales son progreso comprobado dentro de las unidades, no aceptación del catálogo/finanzas/sincronización/agentes.

Evidencia saneada: [revisión de clave única](../../artifacts/live/p16-single-key-review-20261119.json). Procedimiento: [conexión de clave única](P16_SIIE_SINGLE_KEY_20261119.md). El informe del18-11 se conserva como historia y no contradice la unificación comprobada hoy.
