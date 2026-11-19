# Uso de la API CRM de SIIE

Esta guía permite al equipo de RinovaPlus configurar Postman y utilizar las once operaciones CRM de Admisiones y Catálogo comercial. Los ejemplos son ficticios. Los identificadores válidos se obtienen del ambiente elegido mediante las consultas indicadas.

La base documental es https://siieplus.online/SIIEWebPlus. Esta entrega documental no comprueba la disponibilidad de ese servidor ni confirma su versión desplegada.

## 1. Preparar Postman

1. Importar [SIIE_CRM.postman_collection.json](SIIE_CRM.postman_collection.json) mediante **Import → Files**.
2. Revisar la variable de colección baseUrl. Debe contener la raíz de la aplicación, sin barra final.
3. Completar admissionsKey con la clave GENERAL de Admisiones y catalogKey con la clave ORIGINAL exclusiva del catálogo. Usar valores locales o Postman Vault, sin compartir secretos al exportar.
4. Comenzar con las consultas de lectura. Copiar manualmente los IDs de sus respuestas a las variables correspondientes.
5. Preparar POST y PUT únicamente cuando se desee registrar o corregir un seguimiento real. Ambas operaciones escriben en SIIE.
6. Ejecutar las solicitudes individualmente. La colección no contiene scripts, captura automática de variables ni pruebas automáticas.

Las carpetas heredan autenticación **API Key**, nombre X-API-Key, ubicación Header. Admisiones usa {{admissionsKey}} y Catálogo usa {{catalogKey}}. Si se prefiere Bearer, configurar manualmente Authorization con el token original y retirar el otro mecanismo. Cuando se envían ambos, el servidor toma Bearer primero.

### Credenciales y transporte

| Grupo | Credencial que envía el cliente | Configuración del servidor |
|---|---|---|
| Admisiones | Clave GENERAL existente | Configuración general de ApiSecurity. |
| Catálogo comercial | Token ORIGINAL exclusivo del catálogo, de al menos 32 caracteres | El appSetting API_CRM contiene su SHA-256 hexadecimal de 64 caracteres. El hash permanece en SIIE. |

API_CRM habilita exclusivamente las tres consultas Commercial. No concede acceso a Admisiones. La clave general tampoco habilita Commercial.

API_CRM vacío o mal formado produce 503 catalog_credential_config_invalid. Si coincide con una clave general, Commercial devuelve 503 catalog_credential_scope_conflict. La presencia de API_CRM tiene prioridad sobre configuraciones anteriores de catálogo. El custodio gestiona generación, rotación y revocación. El cliente debe conservar la clave original porque el hash no permite recuperarla.

Los endpoints remotos requieren HTTPS. Postman no necesita enviar Origin para esta integración entre servidores. Si otro cliente envía Origin, SIIE exige que esté permitido en su configuración CORS. Las respuestas incluyen X-Correlation-ID para identificar una solicitud.

### Variables de colección

Las claves e IDs se entregan vacíos. Los parámetros opcionales están deshabilitados en cada solicitud hasta que el operador los necesite.

| Variable | Cómo completarla |
|---|---|
| baseUrl | Raíz HTTPS del ambiente autorizado. Valor documental inicial indicado arriba. |
| admissionsKey | Credencial general, entregada por el custodio. |
| catalogKey | Token original exclusivo de consulta, entregado por el custodio. |
| idPeriodo | data.items[].id obtenido de Periodos. |
| idPrograma, idJornada | Valores obtenidos de FiltrosAdmisiones para ese período. |
| idAspirante | data.items[].idAspirante obtenido de Aspirantes. |
| idEstadoSeguimiento | data.items[].id obtenido de EstadosSeguimiento. |
| offset | Desplazamiento de Admisiones. Inicialmente 0. |
| q | Texto opcional de búsqueda de aspirantes. |
| idSeguimiento | data.idSeguimiento recibido al crear el seguimiento. |
| idSeguimientoCrm | UUID propio del seguimiento en RinovaPlus. Se conserva durante todas sus correcciones. |
| createOperationId | UUID nuevo para una creación. Se conserva si se reintenta esa misma creación. |
| updateOperationId | UUID nuevo para una corrección. Se conserva si se reintenta esa misma corrección. |
| expectedRevision | Revisión vigente obtenida del comprobante o historial para PUT. |
| ocurridoUtc | Fecha y hora UTC del seguimiento. Se conserva durante el reintento de la misma operación. |
| autorCrmId, autorCrmNombre | Autoría declarada por el CRM autenticado. |
| programId | items[].program_id obtenido de Commercial/Programs.aspx. |
| commercialPeriodId | ID de período para filtrar Commercial/ProgramOffers.aspx, si se desea. |
| commercialOfferId | items[].offer_id completo obtenido de ProgramOffers. |
| programsCursor, offersCursor | next_cursor de la consulta comercial correspondiente. |

idPrograma y programId pertenecen a los dos contratos HTTP distintos. Admisiones usa camelCase en español. Commercial usa snake_case en inglés. Mantener exactamente esos nombres.

## 2. Índice de operaciones

Todas las rutas de esta tabla se agregan a {{baseUrl}}/Api/CRM/v1/.

| Método | Ruta | Credencial | Resultado esperado |
|---|---|---|---|
| GET | Periodos.aspx | General | 200 |
| GET | EstadosSeguimiento.aspx | General | 200 |
| GET | FiltrosAdmisiones.aspx | General | 200 |
| GET | Aspirantes.aspx | General | 200 |
| GET | Aspirante.aspx | General | 200 |
| GET | HistorialSeguimiento.aspx | General | 200 |
| POST | Seguimientos.aspx | General | 201 |
| PUT | Seguimientos.aspx | General | 200 |
| GET | Commercial/Programs.aspx | Catálogo | 200 |
| GET | Commercial/ProgramOffers.aspx | Catálogo | 200 |
| GET | Commercial/Offer.aspx | Catálogo | 422 parcial con el mapeo actual |

Las operaciones admiten OPTIONS para CORS. Commercial permite únicamente GET/OPTIONS. IIS puede rechazar otros verbos con 404.6 antes de ejecutar la página.

## 3. Consultar Admisiones

Las respuestas satisfactorias de Admisiones tienen la forma {"status":"ok","data":...}. Los IDs numéricos de consulta son enteros positivos hasta 2147483647. No repetir un mismo parámetro numérico en la URL.

### GET Periodos.aspx

Sin parámetros. Devuelve data.items con id, nombre y activo. idPeriodoActivo contiene el ID únicamente cuando existe un solo período activo; en otro caso es null y requiereSeleccion es true.

Ejemplo ficticio de respuesta completa

~~~json
{
  "status": "ok",
  "data": {
    "items": [
      { "id": 900001, "nombre": "Período de ejemplo", "activo": true }
    ],
    "idPeriodoActivo": 900001,
    "requiereSeleccion": false
  }
}
~~~

Elegir un período explícito si requiereSeleccion es true. El período de Admisiones corresponde a ACAspirante.Id_Periodo.

### GET EstadosSeguimiento.aspx

Sin parámetros. Devuelve data.items con id y nombre desde dbo.ACEstadoSeguimiento.

~~~json
{
  "status": "ok",
  "data": {
    "items": [
      { "id": 900002, "nombre": "Resultado ficticio para ilustración" }
    ]
  }
}
~~~

No codificar esos valores ficticios ni una lista propia en RinovaPlus. Consultar el catálogo del destino. La tabla dbo.ACSeguimiento guarda el ID elegido en su columna Estado. Estos estados representan resultados de seguimiento; no acreditan matrícula ni una condición académica oficial.

### GET FiltrosAdmisiones.aspx?idPeriodo={{idPeriodo}}

idPeriodo es obligatorio. Devuelve programas y jornadas que tienen aspirantes en ese período.

~~~json
{
  "status": "ok",
  "data": {
    "idPeriodo": 900001,
    "items": [
      {
        "idPrograma": 900003,
        "programa": "Programa ficticio",
        "idJornada": 900004,
        "jornada": "Jornada ficticia"
      }
    ]
  }
}
~~~

La jornada consultada es la del programa. No demuestra selección individual de jornada ni disponibilidad de cupos.

### GET Aspirantes.aspx?idPeriodo={{idPeriodo}}

| Parámetro | Obligatorio | Tipo y límite | Comportamiento |
|---|---|---|---|
| idPeriodo | Sí | Entero positivo | Restringe a ese período del aspirante. |
| q | No | Texto, máximo 100 caracteres después de recortar espacios exteriores | Busca coincidencia contenida en nombre/apellidos o documento. Vacío consulta el período sin búsqueda. |
| idPrograma | No | Entero positivo | Filtra por el programa de la oferta del aspirante. |
| idJornada | No | Entero positivo | Filtra por la jornada del programa. |
| offset | No | Entero de 0 a 1000000 | Predeterminado 0. Desplazamiento de filas. |

Devuelve hasta 25 elementos, ordenados por fecha de registro e ID descendentes. Si hasMore es true, repetir con offset anterior + limit. Mantener período y filtros mientras se pagina.

Respuesta completa para una búsqueda sin coincidencias

~~~json
{
  "status": "ok",
  "data": { "items": [], "offset": 0, "limit": 25, "hasMore": false }
}
~~~

Cada elemento de items tiene los mismos campos de aspirante enumerados en la siguiente consulta. Un listado vacío es un resultado válido.

### GET Aspirante.aspx?idAspirante={{idAspirante}}&idPeriodo={{idPeriodo}}

Ambos parámetros son obligatorios y enteros positivos. El servidor comprueba que el aspirante pertenezca al período solicitado.

Ejemplo ficticio de respuesta completa

~~~json
{
  "status": "ok",
  "data": {
    "aspirante": {
      "idAspirante": 900005,
      "nombre": "Aspirante ficticio",
      "idPeriodo": 900001,
      "periodo": "Período de ejemplo",
      "idOferta": 900006,
      "idPeriodoOferta": 900001,
      "periodoOferta": "Período de ejemplo",
      "idPrograma": 900003,
      "programa": "Programa ficticio",
      "jornadaPrograma": "Jornada ficticia",
      "fechaRegistro": "2026-01-15T00:00:00",
      "confirmadoOrigen": true,
      "idEstadoSeguimiento": null,
      "estadoSeguimiento": null
    },
    "jornadasOferta": [
      { "id": 900007, "idJornada": 900004, "nombre": "Jornada ficticia" }
    ]
  }
}
~~~

estadoSeguimiento e idEstadoSeguimiento provienen del último ACSeguimiento, ordenado por FechaSeguimiento e Id_Seguimiento descendentes. Pueden ser null si no hay seguimiento. confirmadoOrigen refleja Cnfrmdo de ACAspirante y no equivale por sí solo a matrícula.

idPeriodoOferta se devuelve por separado porque puede diferir de idPeriodo. Los campos enlazados pueden ser null cuando falta la relación de origen. Esta ficha no incluye documento, teléfono ni correo del aspirante.

### GET HistorialSeguimiento.aspx?idAspirante={{idAspirante}}&idPeriodo={{idPeriodo}}

idAspirante e idPeriodo son obligatorios. offset es opcional, de 0 a 1000000, con valor inicial 0. Devuelve bloques de 25, con offset, limit y hasMore. Ordena por fecha e ID de seguimiento descendentes.

Ejemplo ficticio con un seguimiento creado por el CRM

~~~json
{
  "status": "ok",
  "data": {
    "items": [
      {
        "revision": 1,
        "idSeguimientoCrm": "11111111-1111-4111-8111-111111111111",
        "autorCrmId": "autor-ficticio",
        "autorCrmNombre": "Autor de ejemplo",
        "ocurridoUtc": "2026-01-15T15:00:00+00:00",
        "idSeguimiento": 900008,
        "idEstadoSeguimiento": 900002,
        "estado": "Resultado ficticio para ilustración",
        "observacion": "Observación ficticia.",
        "observacionTruncada": false,
        "fechaSeguimiento": "2026-01-15T00:00:00",
        "proximoContacto": null,
        "usuarioOrigen": "RinovaPlus",
        "hora": "10:00:00",
        "agenda": false
      }
    ],
    "offset": 0,
    "limit": 25,
    "hasMore": false
  }
}
~~~

Las observaciones históricas se exponen hasta 4000 caracteres; observacionTruncada indica recorte. revision, idSeguimientoCrm, autorCrmId, autorCrmNombre y ocurridoUtc pueden ser null en registros históricos ajenos a esta integración o cuando faltan las tablas auxiliares.

## 4. Registrar y corregir un seguimiento

POST y PUT requieren la clave general, Content-Type application/json y el cuerpo siguiente. Los ejemplos son ficticios y deben reemplazarse antes de enviarlos.

### Campos del cuerpo

| Campo | Obligatorio | Tipo y validación |
|---|---|---|
| operationId | Sí | UUID no vacío, único por operación. |
| idSeguimientoCrm | Sí | UUID no vacío del seguimiento CRM, estable entre correcciones. |
| idAspirante | Sí | Entero positivo existente y perteneciente a idPeriodo. |
| idPeriodo | Sí | Entero positivo del período del aspirante. |
| idEstadoSeguimiento | Sí | Entero positivo existente en ACEstadoSeguimiento. |
| expectedRevision | Sí | Entero mayor o igual a 0. POST exige 0. PUT exige la revisión vigente. |
| observacion | Sí | Texto de 1 a 2000 caracteres después de recortar espacios. |
| proximoContacto | No | Fecha exacta YYYY-MM-DD o null. Si se omite en PUT se guarda null. |
| ocurridoUtc | Sí | Fecha/hora ISO 8601 con segundos y zona UTC Z o +00:00. Admite fracciones hasta 7 dígitos; años de 1753 a 9998. |
| autorCrmId | Sí | Texto de 1 a 128 caracteres después de recortar espacios. |
| autorCrmNombre | Sí | Texto de 1 a 200 caracteres después de recortar espacios. |

Se rechazan propiedades desconocidas. El cuerpo tiene límite de 16384 bytes cuando Content-Length está informado y lectura acotada a 16384 caracteres. Enviar una carga pequeña y UTF-8.

La autoría es una declaración del CRM autenticado. El campo Usuario del registro nativo se guarda como RinovaPlus. ocurridoUtc se conserva en UTC en los metadatos y se convierte a fecha/hora de Colombia en ACSeguimiento.

### POST Seguimientos.aspx

El POST no admite idSeguimiento en la URL.

~~~json
{
  "operationId": "22222222-2222-4222-8222-222222222222",
  "idSeguimientoCrm": "11111111-1111-4111-8111-111111111111",
  "idAspirante": 900005,
  "idPeriodo": 900001,
  "idEstadoSeguimiento": 900002,
  "expectedRevision": 0,
  "observacion": "Observación ficticia.",
  "proximoContacto": null,
  "ocurridoUtc": "2026-01-15T15:00:00Z",
  "autorCrmId": "autor-ficticio",
  "autorCrmNombre": "Autor de ejemplo"
}
~~~

Respuesta ficticia 201

~~~json
{
  "status": "ok",
  "data": {
    "idSeguimiento": 900008,
    "idSeguimientoCrm": "11111111-1111-4111-8111-111111111111",
    "idAspirante": 900005,
    "idPeriodo": 900001,
    "revision": 1,
    "operationId": "22222222-2222-4222-8222-222222222222",
    "recibidoUtc": "2026-01-15T15:00:01.0000000Z"
  }
}
~~~

Guardar el comprobante en RinovaPlus. idSeguimiento es el ID asignado por SIIE y difiere del UUID idSeguimientoCrm.

### PUT Seguimientos.aspx?idSeguimiento={{idSeguimiento}}

PUT reemplaza los campos editables del seguimiento y recibe el cuerpo completo. Conservar idSeguimientoCrm, idAspirante e idPeriodo. Crear un operationId nuevo y enviar la revisión vigente.

Ejemplo ficticio de corrección después del POST anterior

~~~json
{
  "operationId": "33333333-3333-4333-8333-333333333333",
  "idSeguimientoCrm": "11111111-1111-4111-8111-111111111111",
  "idAspirante": 900005,
  "idPeriodo": 900001,
  "idEstadoSeguimiento": 900002,
  "expectedRevision": 1,
  "observacion": "Observación ficticia corregida.",
  "proximoContacto": "2026-01-20",
  "ocurridoUtc": "2026-01-15T16:00:00Z",
  "autorCrmId": "autor-ficticio",
  "autorCrmNombre": "Autor de ejemplo"
}
~~~

La respuesta 200 tiene el mismo formato del comprobante, con revision incrementada a 2 y el nuevo operationId. Solo se pueden corregir seguimientos creados por esta integración. Si SIIE modificó directamente el registro, la API devuelve native_followup_changed para revisión humana.

### Reintentos, revisiones y concurrencia

- Si hay timeout o respuesta transitoria, repetir el mismo método, URL, operationId y contenido de la operación. El servidor recupera el comprobante persistido.
- Un POST reintentado satisfactoriamente sigue respondiendo 201; PUT sigue respondiendo 200.
- Reutilizar operationId con otro contenido produce 409 operation_changed.
- Una corrección nueva necesita un UUID de operación nuevo. Mantener el UUID del seguimiento.
- No usar {{$guid}} directamente en operationId en Postman, porque generaría otro valor al reenviar.
- Si revision_changed devuelve 409, consultar el historial, revisar los cambios y preparar una nueva corrección con revisión y operationId nuevos.
- El registro nativo, la referencia y la auditoría se confirman en una única transacción. Un error revierte esa transacción.

## 5. Consultar el catálogo académico y comercial

Estas tres consultas usan catalogKey y devuelven el contenido en la raíz JSON, sin envoltura status/data en los resultados 200.

| Campo común | Interpretación |
|---|---|
| schema_version | siie-crm-commercial-v1 |
| source_system | DBSIIE |
| source_revision | sha256: seguido de 64 caracteres hexadecimales. Huella del contenido, excluyendo generated_at; no es rowversion SQL. |
| generated_at | Instante UTC de generación. |
| items y next_cursor | En los dos listados. next_cursor=null finaliza la paginación. |
| pagination | keyset_live_catalog en los listados. No garantiza una instantánea inmutable entre páginas. |

### GET Commercial/Programs.aspx

Sin parámetros obligatorios. cursor es opcional, opaco y admite hasta 128 caracteres. Para la primera página, omitirlo; para continuar, copiar next_cursor a programsCursor y habilitar el parámetro.

Ejemplo ficticio de respuesta completa sin elementos

~~~json
{
  "schema_version": "siie-crm-commercial-v1",
  "source_system": "DBSIIE",
  "items": [],
  "next_cursor": null,
  "pagination": "keyset_live_catalog",
  "source_revision": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "generated_at": "2026-01-15T15:00:00Z"
}
~~~

Cada elemento contiene program_id, code, name, school_id, school, modality_id, modality, shift_id, schedule, duration_levels, active, active_basis, description, aliases y registration_url.

Los IDs se expresan como strings y pueden ser null si falta una referencia. duration_levels deriva de Semestres de la fuente y se presenta como niveles. active es null porque ACProgramas no tiene una columna de estado propia. description, aliases y registration_url son null en el mapeo actual.

### GET Commercial/ProgramOffers.aspx?program_id={{programId}}

| Parámetro | Obligatorio | Tipo y uso |
|---|---|---|
| program_id | Sí | Entero positivo hasta 2147483647, obtenido de Programs. |
| period_id | No | Entero positivo hasta 2147483647 para limitar al período. |
| cursor | No | Cursor opaco, máximo 128 caracteres, devuelto para el mismo programa y filtro de período. |

Copiar next_cursor a offersCursor para avanzar. Mantener program_id y period_id. Cada página contiene hasta 25 referencias.

Respuesta ficticia completa sin ofertas

~~~json
{
  "schema_version": "siie-crm-commercial-v1",
  "source_system": "DBSIIE",
  "program_id": "900003",
  "period_id": null,
  "items": [],
  "next_cursor": null,
  "pagination": "keyset_live_catalog",
  "source_revision": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "generated_at": "2026-01-15T15:00:00Z"
}
~~~

Cada elemento incluye offer_id, source_offer_id, program_id, period_id, period_name, period_active, level, tariff_count, plan_count, unbound_plan_count, shift_id, schedule, modality_id, modality, active, active_basis, campus_id, quotable y data_quality.

offer_id combina la oferta original y el nivel, por ejemplo 900006-n1. Copiar el ID devuelto completo a commercialOfferId. Si no hay nivel tarifado válido, offer_id y level son null y data_quality explica el problema.

active refleja GEPeriodo.EstadoPeriodo y active_basis declara esa fuente. No representa una vigencia financiera. campus_id permanece null y quotable=false con los mapeos actuales.

### GET Commercial/Offer.aspx?offer_id={{commercialOfferId}}

offer_id es obligatorio y debe ser el valor completo devuelto por ProgramOffers. Su formato es Id_PrgOfrecido-nNivel. La parte de oferta debe caber en un entero positivo de 32 bits y el nivel admite hasta cuatro dígitos positivos.

**Con el código actual, toda oferta resoluble devuelve 422 source_data_incomplete.** El código marca expresamente como pendientes sede, requisitos de admisión y vigencia comercial, además de condiciones de planes. Habilitar una clave o cargar filas existentes no elimina ese estado. Se requiere completar y validar el mapeo institucional.

Fragmento ficticio de respuesta, reducido para explicar su uso

~~~json
{
  "status": "error",
  "code": "source_data_incomplete",
  "message": "La fuente contiene datos pendientes para habilitar la cotización.",
  "quotable": false,
  "data_quality": [
    {
      "field": "campus_id",
      "code": "source_relationship_missing",
      "message": "SIIE no identifica la sede de esta oferta."
    }
  ],
  "partial_offer": {
    "schema_version": "siie-crm-commercial-v1",
    "source_system": "DBSIIE",
    "offer_id": "900006-n1",
    "source_offer_id": "900006",
    "program_id": "900003",
    "period_id": "900001",
    "level": 1,
    "currency": "COP",
    "campus_id": null,
    "quotable": false,
    "commercial": {
      "price_cop": 1000000,
      "price_scope": "semester_tuition_only",
      "full_cost_cash_cop": 1000000,
      "full_cost_scope": "semester_tuition_only",
      "price_valid_from": null,
      "price_valid_until": null,
      "requirements": null
    }
  }
}
~~~

La respuesta real incluye otros campos y más incidencias en ambos data_quality. Para inspección manual, leer partial_offer; no tratar el 422 como una cotización completa ni aplicarlo automáticamente a un catálogo aprobado.

| Grupo de campos de partial_offer | Datos |
|---|---|
| Trazabilidad | schema_version, source_system, source_revision, generated_at, source_offer_id, source_tariff_ids. |
| Referencias | offer_id, program_id, period_id, period_name, level, school_id, shift_id, modality_id, campus_id. |
| Ficha | name, code, school, schedule, currency, active, active_basis, academic_start, academic_end. |
| Calidad | quotable y data_quality con field, code y message. |
| commercial | duration, modality, syllabus, syllabus_details, syllabus_scope, syllabus_order_basis, requirements, price_cop, price_concept, price_scope, price_valid_from, price_valid_until, full_cost_cash_cop, full_cost_scope, cost_inclusions, cost_exclusions, financial_plans. |

syllabus es texto de hasta 2500 caracteres. syllabus_details conserva referencias de hasta 500 materias activas del nivel y requiere un único plan educativo vigente. El orden por ID sirve para mostrar datos de forma estable. requirements es null porque los prerrequisitos entre materias no se consideran requisitos de admisión.

ValorOrdinaria representa únicamente la enseñanza del semestre o nivel ofertado. price_cop y full_cost_cash_cop tienen ese alcance. Los uniformes y otros elementos o cargos adicionales quedan excluidos, sin valoración en esta fuente. No es el precio de todo el programa ni el costo global de estudiar con todos los extras.

### Planes financieros de la oferta

financial_plans admite hasta doce planes. Un plan no resoluble se informa mediante null y data_quality. Los importes válidos son pesos COP enteros positivos, sin redondeo implícito.

| Campo del plan | Uso |
|---|---|
| external_id | ID compuesto de oferta, nivel y plan. |
| source_plan_id, source_tariff_id | Referencias de AFPlanes y AFTarifas. |
| name, source_plan_type | Nombre y tipo de origen. |
| valid_from, valid_until, conditions | Permanecen null cuando no hay fuente confirmada. |
| initial_payment_cop, initial_payment_due_date | Importe y fecha del abono inicial almacenado. |
| installments | Hasta 120 cuotas, cada una con number, amount_cop y due_date. |
| total_cost_cop | Suma exacta de abono y cuotas almacenadas cuando el calendario es coherente; null si no lo es. |
| total_cost_basis | sum_of_stored_schedule. |
| schedule_valid | Comprueba cantidad y numeración consecutiva de cuotas, importes y fechas ordenadas. |
| cash_price_cop | Valor ordinario de la enseñanza del nivel asociado al plan. |
| source_prices_cop | pronto_pago de ValorDescuento, pago_oportuno de ValorOrdinaria y extraordinaria de ValorExtradinaria. |
| source_payment_date | FechaPago de origen; no acredita vigencia comercial. |

Las fechas se conservan como YYYY-MM-DD, incluidos calendarios anteriores. No se inventan intereses ni se regeneran vencimientos. La vigencia académica y una fecha de cuota pasada no establecen por sí solas la vigencia comercial del plan.

## 6. Flujo completo recomendado en Postman

1. Consultar Periodos y EstadosSeguimiento con admissionsKey. Completar idPeriodo e idEstadoSeguimiento con IDs reales.
2. Consultar FiltrosAdmisiones. Activar idPrograma/idJornada solo si se desea filtrar.
3. Consultar Aspirantes y seleccionar idAspirante. Abrir Aspirante y su historial para revisar el contexto.
4. Cuando corresponda registrar un seguimiento, preparar UUID estable idSeguimientoCrm y UUID nuevo createOperationId. Completar autoría, ocurridoUtc y observacion. Revisar el cuerpo y enviar POST una vez.
5. Guardar idSeguimiento y revision. Si hubo una falla transitoria, repetir exactamente esa solicitud. No regenerar UUID ni fecha.
6. Consultar el historial para comprobar el registro. Para corregir, usar updateOperationId nuevo, conservar las referencias y fijar expectedRevision a la revisión vigente; revisar y enviar PUT.
7. Con catalogKey, consultar Programs y copiar programId. Consultar ProgramOffers y copiar commercialOfferId. Consultar Offer e inspeccionar el 422 parcial esperado.
8. Registrar las incidencias de data_quality pendientes de mapeo antes de habilitar cotizaciones en RinovaPlus.

## 7. Errores y límites

Las respuestas de error de autenticación pueden contener únicamente status y message. Los errores del endpoint añaden code. Commercial puede incluir quotable=false.

| HTTP | Código o situación | Acción |
|---|---|---|
| 400 | invalid_request, invalid_parameter, invalid_cursor, offer_level_required | Revisar nombres, tipos, UUID, fechas, revisión e ID completo. |
| 401 | Credencial ausente, incorrecta o de otro grupo | Revisar la variable y el alcance de la clave. |
| 403 | HTTPS requerido u Origin rechazado | Corregir transporte u origen autorizado. |
| 404 | period_not_found, applicant_not_in_period, invalid_followup_state, crm_followup_not_found | Consultar nuevamente el catálogo o referencia de Admisiones. |
| 404 | program_not_found, offer_not_found, offer_level_not_found | Consultar Programs y ProgramOffers del ambiente. |
| 404.6 IIS | Método bloqueado antes de la página | Usar el método permitido para esa carpeta. |
| 405 | method_not_allowed cuando llega a la página | Consultar el índice de métodos. |
| 409 | operation_changed, followup_exists, followup_binding_changed, revision_changed, native_followup_changed | Revisar comprobante/historial. No sobreescribir automáticamente ni reutilizar la operación con otro cuerpo. |
| 413 | body_too_large | Reducir el cuerpo de seguimiento. |
| 415 | json_required | Enviar Content-Type application/json. |
| 422 | unsupported_note_characters | Ajustar los caracteres que la columna VARCHAR nativa no puede conservar. |
| 422 | source_data_incomplete | Revisar partial_offer y resolver el mapeo institucional. |
| 422 | ambiguous_tariff_mapping, source_plan_limit, source_cardinality_invalid, source_response_too_large | Solicitar revisión de la fuente comercial. No truncar ni mezclar planes. |
| 429 | Límite de solicitudes | Esperar Retry-After. |
| 503 | retry_operation | Reintentar el mismo método/URL/operationId/cuerpo después de Retry-After. |
| 503 | storage_not_configured, connection_not_configured, admissions_unavailable, followup_id_exhausted, catalog_unavailable, catalog_connection_missing, catalog_deadline_exceeded, catalog_limit | Solicitar revisión operativa. No asumir que hubo una escritura confirmada. |
| 503 | catalog_credential_config_invalid, catalog_credential_scope_conflict o seguridad sin configurar | Solicitar al custodio que revise la configuración de ese grupo. |
| 500 | internal_error | Conservar X-Correlation-ID y comunicarlo al responsable técnico. |

Los límites son por clave, IP y ruta en una ventana de un minuto. Admisiones GET permite 120 solicitudes, Seguimientos POST/PUT comparte 30 y cada ruta Commercial permite 60. X-RateLimit-Limit y X-RateLimit-Remaining informan el cupo.

Commercial limita la respuesta a 512 KiB y utiliza un presupuesto de consulta de nueve segundos después de autenticar, con timeout de conexión de cinco segundos dentro del recorrido. Esto no garantiza un tiempo HTTP total en la red. Admisiones limita sus listados a 25 filas e historial observado a 4000 caracteres por nota.

## 8. Requisitos del servidor y alcance verificado

El responsable de SIIE debe comprobar el sitio HTTPS, sus claves y ConexionSQL. Antes de usar POST/PUT, debe revisar la disponibilidad de CRMApiAdmisionSeguimiento y CRMApiAdmisionOperacion junto con el script de instalación 001_admisiones.sql del proveedor. La documentación y colección no ejecutan ese script.

POST/PUT guardan datos en ACSeguimiento y metadatos de integración. El asignador actual de Id_Seguimiento usa una transacción SERIALIZABLE y bloqueo de tabla. Los clientes antiguos que calculen IDs fuera de transacción requieren validación de concurrencia. PUT conserva auditoría y rechaza cambios nativos ajenos a la revisión recibida.

El catálogo comercial consulta ACProgramas, ACEscuela, ACModalidad, ACJornada, ACProgramaOfrecido, GEPeriodo, AFTarifas, AFPlanes, AFDetallePlanPago, ACPlanEducativo, ACAsignaturaPlan y ACAsignatura. No necesita una migración nueva.

Esta entrega cotejó las once operaciones con sus páginas ASPX, las clases CrmAdmissionsApi, CrmCommercialApi y ApiSecurity, y las guías/OpenAPI de origen. Solo se realizó lectura de código y validación estructural de los documentos. No se ejecutaron solicitudes HTTP, SQL ni escrituras de seguimiento durante su preparación.

La simulación dependiente de fecha y los webhooks de invalidación comercial siguen pendientes. La integración del consumidor RinovaPlus y la disponibilidad de los endpoints en el servidor público requieren comprobación en sus respectivos ambientes.

