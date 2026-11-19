# SIIE → RinovaPlus: datos requeridos y estado de cada endpoint

Actualizado el18 de noviembre de2026, America/Bogota, con la aclaración del propietario. Este es el documento consolidado para entregar al responsable de SIIE. Las rutas marcadas como propuestas requieren confirmación/desarrollo del proveedor; no son endpoints disponibles ni autorizan ejecutar escrituras. La guía y la colección recibidas se conservan sin modificar en `docs/contracts/SIIE_PROVIDER_GUIDE_20261118.md` y `docs/contracts/SIIE_CRM.postman_collection.json`.

## 1. Alcance que necesita RinovaPlus

1. Consultar los aspirantes desde su fuente de aspirantes, con identidad, contacto y relación académica.
2. Consultar los estudiantes desde su fuente de estudiantes/matrículas, sin deducirlos de una confirmación de aspirante.
3. Consultar los programas realmente **ofrecidos en el período activo**, con escuela, jornada, modalidad, nivel y sede.
4. Para cada oferta aplicable, consultar el **valor oficial de contado y cada plan financiado**: abono, cuotas, fechas, total y condiciones.

SIIE resuelve sus tablas y relaciones detrás de la API HTTPS. RinovaPlus no necesita una conexión SQL a DBSIIE. La tabla de aspirantes está identificada en la guía como ACAspirante; la tabla y el vínculo oficiales de estudiantes/matrículas no están descritos en el contrato recibido y debe precisarlos el responsable de SIIE.

La cartera individual —deuda, pagos y recibos de una persona— es otra consulta. **No es necesaria para mostrar el precio de contado y los planes comerciales** y no se añade como requisito de este recorrido. Tampoco se confunde la entidad estudiante con una cuenta de acceso de usuario del CRM.

## 2. Qué entrega cada una de las once operaciones recibidas

Base: `https://siieplus.online/SIIEWebPlus/Api/CRM/v1/`.

| Operación | Credencial | Qué entrega según el contrato | Situación actual |
|---|---|---|---|
| GET `Periodos.aspx` | General de Admisiones | Períodos con ID, nombre y activo; `idPeriodoActivo` sólo si hay exactamente uno; `requiereSeleccion` en caso contrario. | Documentado; falta clave General. El token de Catálogo fue rechazado en esta consulta. |
| GET `EstadosSeguimiento.aspx` | General | IDs y nombres oficiales de resultados de seguimiento de ACEstadoSeguimiento. | Documentado; no probado con una clave General válida. No son estados de matrícula ni las etapas comerciales del CRM. |
| GET `FiltrosAdmisiones.aspx?idPeriodo=...` | General | Programas y jornadas **que ya tienen aspirantes** en ese período. | Documentado; falta clave General. No sustituye el catálogo completo de programas ofrecidos: omite una oferta que aún no tenga aspirantes. |
| GET `Aspirantes.aspx?idPeriodo=...` | General | Hasta25 aspirantes por página, búsqueda `q`, filtros de programa/jornada, `offset`, `limit` y `hasMore`. Incluye campos académicos del aspirante. | Consumidor de lectura construido en RinovaPlus; falta clave General para validar datos reales. |
| GET `Aspirante.aspx?idAspirante=...&idPeriodo=...` | General | Nombre, IDs de aspirante/período/oferta/programa, nombres académicos, jornada del programa, fecha de registro, confirmación de origen, último seguimiento y jornadas de la oferta. | Documentado; falta clave General. **No entrega teléfono, correo ni documento en el contrato actual.** `confirmadoOrigen` no demuestra matrícula. |
| GET `HistorialSeguimiento.aspx?idAspirante=...&idPeriodo=...` | General | Seguimientos paginados: observación, estado, fechas, próximo contacto y autoría/revisión cuando existen. Señala notas truncadas e historial ajeno a esta integración. | Consumidor de lectura construido; falta clave General. No acredita estado de estudiante. |
| POST `Seguimientos.aspx` | General | Crea un seguimiento y devuelve comprobante, ID SIIE, UUID CRM, operación y revisión. | Documentado por SIIE; **escritura no habilitada en RinovaPlus**. No hace falta para empezar la consulta de aspirantes. |
| PUT `Seguimientos.aspx?idSeguimiento=...` | General | Corrige un seguimiento de esta integración con revisión esperada y operación idempotente; devuelve comprobante. | Documentado; escritura no habilitada. Requiere gestión de conflictos y revisión, no un PUT automático del catálogo. |
| GET `Commercial/Programs.aspx?cursor=...` | Catálogo original | Programa, código, escuela, modalidad, jornada y duración en niveles; IDs y paginación de25. `active=null` porque la fuente de programas no declara estado propio. | **Probado y funcionando**, incluidas dos páginas en la UI. No tiene filtro de período en el contrato recibido y no garantiza que cada programa esté ofrecido en el período activo. |
| GET `Commercial/ProgramOffers.aspx?program_id=...&period_id=...&cursor=...` | Catálogo | Ofertas por programa, período opcional y nivel; ID completo `oferta-nNivel`, jornada/modalidad, metadatos de tarifas/planes y calidad. `active` se basa en el estado del período. | **Probado y funcionando**; cuatro páginas de Software. El filtro de período está documentado y admitido por el adaptador; la UI debe seleccionarlo con un período oficial, no inferirlo del año. No entrega el detalle completo de precios o cuotas. |
| GET `Commercial/Offer.aspx?offer_id=...` | Catálogo | Ficha y datos comerciales: valor ordinario, alcance, vigencia, contado, materias y planes con abono/cuotas/total, procedencia y calidad. La guía prevé422con `partial_offer` mientras falten mapeos. | **Bloqueado en origen**: pruebas reales devuelven503`catalog_unavailable`, incluso para Software2026-B `1080-n1`; no se recibió detalle financiero ni objeto parcial. Correlaciones al final. |

Las respuestas de Admisiones utilizan `status/data` y nombres camelCase en español; Commercial usa datos en la raíz y snake_case. No mezclar los dos contratos ni sus claves. El token guardado está validado para Catálogo; falta la clave General de ApiSecurity. La presencia de una clave no acredita el acceso al otro grupo.

## 3. Período activo: cómo debe funcionar

1. Obtener el ID del período oficial. Si SIIE declara varios o ninguno activo, el responsable debe seleccionar uno; no elegir automáticamente el año más reciente.
2. Obtener las ofertas de ese período y los programas asociados, incluyendo ofertas con cero aspirantes o cero estudiantes. Un programa del catálogo histórico no implica oferta vigente.
3. Mantener separados `idPeriodo` del aspirante y `idPeriodoOferta`: el contrato dice expresamente que pueden ser distintos. SIIE debe permitir distinguir y filtrar ambos cuando corresponda. No reasignar un aspirante a otra cohorte para hacerlo coincidir.
4. Para estudiantes, separar período de matrícula, período/cohorte de ingreso y período de la oferta. Mantener la matrícula que relaciona persona, programa y período.
5. El estado del período y las fechas académicas no acreditan la vigencia de un precio o plan. La cotización necesita sus fechas comerciales oficiales.

### Programas ofrecidos: flujo existente y mejora opcional

Con las rutas actuales se puede obtener el período oficial, recorrer el catálogo de programas y consultar las ofertas de cada uno con `period_id`, conservando sólo los que tengan una oferta en ese período. Esto es una composición del consumidor, no una ruta directa ya disponible. **No es indispensable crear otro endpoint para el piloto**; falta implementar ese flujo de período activo en RinovaPlus y habilitar la lectura de Periodos con la clave General.

Para evitar una consulta por cada programa al crecer el catálogo, mejora opcional a acordar: GET `Commercial/PeriodPrograms.aspx?period_id=...&cursor=...`, o una ampliación compatible de `Programs.aspx` con filtro de período. **Ninguna está entregada actualmente.** Si se elige esta opción, debe devolver todos los programas ofrecidos, sus IDs de oferta/nivel, escuela, sede, jornadas y modalidades; distinguir activo/baja y declarar si la lista es un catálogo vivo o una instantánea. No basarla en la existencia de aspirantes.

## 4. Aspirantes: qué ampliar

La consulta ya existe; no hace falta crear otra tabla ni otra API paralela para listar aspirantes. Se necesita:

| Grupo | Datos requeridos para el CRM | Lo recibido / pendiente |
|---|---|---|
| Identidad | ID estable de aspirante y, si SIIE dispone de él, ID de persona para vincular un futuro estudiante sin unir por nombre. | ID de aspirante documentado; vínculo de persona/estudiante por confirmar. |
| Contacto | Nombre completo, teléfono normalizado con país y correo, con fecha/origen y estado de validación cuando existan. | Nombre sí; teléfono y correo no están expuestos. Solicitar ampliación o consulta de contacto autorizada. No hace falta exponer el documento completo para lograr el vínculo si existe un ID estable. |
| Relación académica | IDs de programa/oferta, escuela, sede, modalidad, jornada elegida, nivel si aplica, período del aspirante y período de oferta. | Parte documentada; referencias/elección individual incompletas o nulas deben declararse. La jornada del programa no prueba una elección individual ni cupo disponible. |
| Seguimiento | Estado oficial de seguimiento, fecha, responsable de origen, historial y próximo contacto. | Rutas existentes; pendientes de prueba con clave General. Las etapas comerciales de RinovaPlus mantienen un mapeo propio y no sustituyen estados académicos. |
| Contactabilidad | Restricción de contacto y preferencias/autorizaciones de cada canal, cuando SIIE las gestione, con su procedencia. | No documentadas. Ser aspirante o disponer de su teléfono no equivale a autorizar campañas comerciales; el CRM conserva su propia comprobación. |

Si se requiere segmentar por edad, género o ubicación, pedir sólo los campos disponibles y necesarios para esa finalidad, sus definiciones y nulabilidad. No deducirlos del nombre ni añadirlos como condición para consultar al aspirante. No se presupone que ya estén en la API.

## 5. Estudiantes y matrículas: consultas que faltan

La API recibida no tiene endpoints de estudiantes. SIIE debe **crear o documentar y entregar, si ya existen**, estas consultas. Nombres propuestos, no implementados:

- GET `Estudiantes.aspx?idPeriodo=...&idPrograma=...&idJornada=...&estado=...&q=...&offset=...`: listado paginado, con filtros y alcance de período explícitos.
- GET `Estudiante.aspx?idEstudiante=...&idPeriodo=...`: ficha de persona y sus matrículas/programas aplicables al período.
- Catálogo de estados académicos y filtros de estudiantes, o metadatos equivalentes en un contrato acordado; no reutilizar los resultados de seguimiento de aspirantes.

Datos mínimos a acordar:

- ID de estudiante/persona, nombre, teléfono y correo autorizados para la operación del CRM; vínculo con `idAspirante` si existe. La clave de relación debe ser oficial, no una coincidencia aproximada.
- ID de matrícula y de programa/oferta/período; escuela, sede, modalidad, jornada y nivel/semestre con su unidad.
- Estado académico/matrícula oficial, sus fechas y el catálogo de significados. Conservar estados desconocidos para revisión en vez de traducirlos a «activo» por suposición.
- Distinguir una persona con varios programas o matrículas: no perder relaciones al deduplicar un contacto del CRM.
- Fechas de creación/modificación y estado de baja/anulación, para actualizar sin crear duplicados ni borrar la historia local.

No se requieren notas, calificaciones ni asistencia para el alcance de orientación y consulta de precios aquí solicitado. Su incorporación sería otra necesidad explícita, no «toda la información» indiscriminadamente.

## 6. Contado y cada plan financiado

`Commercial/Offer.aspx` es el endpoint existente destinado a este detalle: **hay que repararlo y completar su mapeo**, no empezar creando otra API financiera sin revisar éste.

| Grupo | Qué debe entregar SIIE |
|---|---|
| Oferta aplicable | IDs de programa, oferta, período, sede, jornada, modalidad y nivel. Una tarifa de otra oferta no se reutiliza por compartir nombre. |
| Contado oficial | Valor COP entero, concepto exacto, alcance (nivel/semestre/programa), vigencia y condiciones. Confirmar cuál es el precio real de contado; el valor ordinario y el descuento de pronto pago no son intercambiables. |
| Inclusiones | Conceptos/cargos obligatorios incluidos y excluidos; valor de cada cargo cuando se pretenda afirmar costo completo. Un extra sin valorar se declara pendiente. |
| Planes | ID y nombre de cada plan ofrecido para esa oferta, tipo y condiciones, vigencia y referencias de origen. Un plan que no aplica no se mezcla con otra jornada o período. |
| Abono | Valor inicial y su fecha límite, sin deducirlos del nombre del plan. |
| Cuotas | Número de cuotas y, para cada una, número, valor COP y fecha de vencimiento; no asumir cuotas iguales. |
| Total financiado | Total oficial, reconciliado con abono y todas las cuotas/cargos según el alcance; explicitar intereses, descuentos o cargos incorporados. No inferir una tasa por diferencia de precios. |
| Calendario | Precisar si es una oferta general de cohorte o si depende de la fecha de matrícula. Si depende de la fecha, entregar una simulación de sólo lectura con fecha base; no inventar vencimientos en Gemini. |
| Trazabilidad/calidad | Revisión de origen, fecha de generación, vigencias, `quotable` y problemas de calidad con campos concretos. Datos ausentes quedan nulos y no se anuncian como valores confirmados. |

**Límite del mapeo actual:** la guía atribuye `price_cop` y `full_cost_cash_cop` a `ValorOrdinaria`, enseñanza del semestre/nivel, con alcance `semester_tuition_only`. No es el precio total de todo el programa ni el costo global con materiales, uniformes u otros extras. Los planes tienen fechas históricas y algunas condiciones/vigencias nulas. Aunque se repare el503y vuelva el422parcial, faltará completar y revisar esas condiciones antes de cotizar.

## 7. Qué falta crear, ampliar o corregir

| Prioridad | Responsable SIIE | Trabajo pendiente en RinovaPlus |
|---|---|---|
| 1 · Acceso a aspirantes | Entregar clave General válida y confirmar permisos de lectura. | Guardarla directamente en `SIIE_ADMISSIONS_API_TOKEN` Runtime y probar períodos, aspirantes, filtros, ficha e historial. El consumidor ya está construido. |
| 2 · Detalle financiero | Corregir503`catalog_unavailable`; completar contado, planes, vigencias, sede y requisitos. Entregar dos ofertas completas/vigentes y ejemplos de ausencias. | Revisar cada cifra/calendario con la API; mantener borrador y publicar hechos aprobados para el agente. Hoy los precios no se cargan desde el detalle fallido. |
| 3 · Estudiantes | Exponer listado y ficha, relaciones de matrícula, filtros y estados; documentar la tabla/relación de origen oficial. | Construir consumidor, vista y vínculo CRM sobre el contrato recibido. La pestaña actual indica que la API falta; no es un conector de estudiantes activo. |
| 4 · Oferta del período | Habilitar Periodos con la clave General. Consulta agregada por período opcional para reducir solicitudes. | Implementar selector de período oficial y composición de Programs + ProgramOffers con `period_id`; no usar automáticamente toda la historia ni sólo programas con aspirantes. No exige por sí sola otro endpoint para el piloto. |
| 5 · Contacto y actualización | Ampliar contacto/vínculos de persona, documentar versiones, bajas, paginación y actualización incremental; límites, errores y claves por alcance. | Sincronización revisada y vínculos estables, sin sobreescribir notas/correcciones humanas; información autorizada y vigente para agentes. |

Pedir OpenAPI y Postman actualizados con tipos, nulabilidad, filtros, permisos y ejemplos sin datos personales reales. No enviar claves ni archivos de base de datos por el chat. Acordar casos de prueba del período activo y las referencias de dos programas/ofertas.

## 8. Orden de prueba y aceptación

Primero clave General y período oficial; luego un aspirante y su historial; después estudiantes con matrícula real de prueba autorizada; catálogo ofrecido de ese período; contado y dos planes completos; finalmente publicación revisada y preguntas del agente comparadas cifra por cifra con SIIE. Antes de automatizar actualizaciones se verifican duplicados, bajas, cambios de período y revocación de acceso.

P16 mantiene0/5 unidades aceptadas. Listar programas y ofertas prueba acceso parcial, no permite afirmar que ya se consultan estudiantes o precios oficiales. La evidencia original y las correlaciones del503se conservan abajo.

---

## Evidencia de conexión y fallos observados

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
