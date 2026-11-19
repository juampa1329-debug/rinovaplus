# Uso de la API CRM de SIIE

Esta guía permite al equipo de RinovaPlus configurar Postman y utilizar las catorce operaciones CRM de Admisiones y Catálogo comercial. Los ejemplos son ficticios. Los identificadores válidos se obtienen del ambiente elegido mediante las consultas indicadas.

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
| idPeriodo | data.idPeriodoOfrecido de Periodos para POST/PUT; habilitarlo en GET sólo al seleccionar otro período explícitamente. |
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
| commercialPeriodId | ID de período para filtrar Commercial/Programs.aspx y Commercial/ProgramOffers.aspx, si se desea. |
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
| GET | Estudiantes.aspx | General | 200 |
| GET | Estudiante.aspx | General | 200 o 404 si no hay matrícula del período |
| GET | FiltrosEstudiantes.aspx | General | 200 |
| GET | Commercial/Programs.aspx | Catálogo | 200 |
| GET | Commercial/ProgramOffers.aspx | Catálogo | 200 |
| GET | Commercial/Offer.aspx | Catálogo | 422 parcial con el mapeo actual |

Las operaciones admiten OPTIONS para CORS. Commercial permite únicamente GET/OPTIONS. IIS puede rechazar otros verbos con 404.6 antes de ejecutar la página.

## 3. Consultar Admisiones

Las respuestas satisfactorias de Admisiones tienen la forma {"status":"ok","data":...}. Los IDs numéricos de consulta son enteros positivos hasta 2147483647. No repetir un mismo parámetro numérico en la URL.

### GET Periodos.aspx

Sin parámetros devuelve sólo el período ofrecido en data.items, con id, nombre y activo. Para ver todos los períodos, habilitar incluirHistoricos=1. idPeriodoOfrecido identifica el predeterminado y fuentePeriodoOfrecido informa GEParametros:38 o GEPeriodo.EstadoPeriodo. idPeriodoActivo conserva exclusivamente el significado académico: ID único con EstadoPeriodo=1 o null. requiereSeleccion=false indica resolución satisfactoria del ofrecido.

Ejemplo ficticio de respuesta completa

~~~json
{
  "status": "ok",
  "data": {
    "items": [
      { "id": 900001, "nombre": "Período de ejemplo", "activo": true }
    ],
    "idPeriodoActivo": 900001,
    "idPeriodoOfrecido": 900001,
    "fuentePeriodoOfrecido": "GEParametros:38",
    "requiereSeleccion": false
  }
}
~~~

El período de Admisiones corresponde a ACAspirante.Id_Periodo. Para consultar históricos, obtener sus IDs con incluirHistoricos=1 y habilitar idPeriodo explícitamente. Las lecturas sin período usan el valor numérico de GEParametros.Valor para Id_Parametro=38 (PERIODO OFRECIDO), siempre que exista en GEPeriodo.Id_Periodo. Ese parámetro tiene prioridad aunque EstadoPeriodo sea 0. Si está ausente, no es válido o apunta a un período inexistente, se usa únicamente el período con EstadoPeriodo=1 cuando existe uno solo. Sin resolución inequívoca se devuelve 503 offered_period_unavailable; nunca se escoge el primero de varios períodos.

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

idPeriodo es opcional; sin él se usa el período ofrecido. Devuelve programas y jornadas que tienen aspirantes en ese período.

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
| idPeriodo | No | Entero positivo | Predeterminado ofrecido; un ID explícito permite históricos. |
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

idAspirante es obligatorio. idPeriodo es opcional y usa el ofrecido si se omite. Ambos admiten enteros positivos. El servidor comprueba la pertenencia del aspirante al período efectivo, incluso al consultar históricos.

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

idPeriodoOferta se devuelve por separado porque puede diferir de idPeriodo. Los campos enlazados pueden ser null cuando falta la relación de origen. Esta ficha no incluye documento; ahora incluye telefono, celular y correo nativos, sin normalización y con blancos null.

### GET HistorialSeguimiento.aspx?idAspirante={{idAspirante}}&idPeriodo={{idPeriodo}}

idAspirante es obligatorio; idPeriodo es opcional y usa el ofrecido si se omite. Un período explícito permite históricos. offset es opcional, de 0 a 1000000, con valor inicial 0. Devuelve bloques de 25, con offset, limit y hasMore. Ordena por fecha e ID de seguimiento descendentes.

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

Sin parámetros obligatorios. period_id es opcional y debe ser un entero positivo hasta 2147483647. Al enviarlo, devuelve únicamente programas vinculados con ACProgramaOfrecido en ese período. Al omitirlo, restringe al período ofrecido: parámetro 38 válido, con respaldo en un único académico activo. Si no puede resolverlo, devuelve 503 offered_period_unavailable. Un ID explícito permite históricos. cursor es opcional, opaco y admite hasta 128 caracteres; queda ligado al período efectivo; reiniciar paginación si cambia el predeterminado. Para la primera página, omitirlo; para continuar, copiar next_cursor a programsCursor y mantener period_id.

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
| period_id | No | Entero positivo. Omitido usa el período ofrecido; explícito permite históricos. |
| cursor | No | Cursor opaco, máximo 128 caracteres, devuelto para el mismo programa y filtro de período. |

Copiar next_cursor a offersCursor para avanzar. Mantener program_id y period_id. Cada página contiene hasta 25 referencias.

Respuesta ficticia completa sin ofertas

~~~json
{
  "schema_version": "siie-crm-commercial-v1",
  "source_system": "DBSIIE",
  "program_id": "900003",
  "period_id": "900001",
  "offered_period_id": "900001",
  "offered_period_source": "GEParametros:38",
  "items": [],
  "next_cursor": null,
  "pagination": "keyset_live_catalog",
  "source_revision": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "generated_at": "2026-01-15T15:00:00Z"
}
~~~

Cada elemento incluye offer_id, source_offer_id, program_id, period_id, period_name, period_active, level, tariff_count, plan_count, unbound_plan_count, shift_id, schedule, modality_id, modality, active, active_basis, campus_id, quotable y data_quality.

offer_id combina la oferta original y el nivel, por ejemplo 900006-n1. Copiar el ID devuelto completo a commercialOfferId. Si no hay nivel tarifado válido, offer_id y level son null y data_quality explica el problema.

active es true si el período de la oferta coincide con offered_period_id; active_basis es offered_period. period_active conserva por separado GEPeriodo.EstadoPeriodo. Una oferta futura configurada en el parámetro 38 puede estar ofrecida aunque su indicador académico sea false. No representa una vigencia financiera. La oferta se define por programa, período y nivel. campus_id permanece null porque la sede no integra esa identidad comercial; no genera una incidencia ni bloquea la completitud. quotable=false en el listado indica que la ficha comercial requiere revisión.

### GET Commercial/Offer.aspx?offer_id={{commercialOfferId}}

offer_id es obligatorio y debe ser el valor completo devuelto por ProgramOffers. Su formato es Id_PrgOfrecido-nNivel. La parte de oferta debe caber en un entero positivo de 32 bits y el nivel admite hasta cuatro dígitos positivos.

**Con el código actual, toda oferta resoluble devuelve 422 source_data_incomplete.** El código marca expresamente como pendientes requisitos de admisión y condiciones de planes. Las vigencias comerciales null son opcionales y no bloquean. La sede no integra la identidad comercial de esta oferta y campus_id=null no constituye un bloqueo. Habilitar una clave o cargar filas existentes no elimina ese estado. Se requiere completar y validar el mapeo institucional.

Fragmento ficticio de respuesta, reducido para explicar su uso

~~~json
{
  "status": "error",
  "code": "source_data_incomplete",
  "message": "La fuente contiene datos pendientes para habilitar la cotización.",
  "quotable": false,
  "data_quality": [
    {
      "field": "commercial.requirements",
      "code": "admission_requirements_missing",
      "message": "No hay requisitos de admisión confirmados en esta fuente."
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

syllabus es texto de hasta 2500 caracteres. syllabus_details conserva referencias de hasta 500 materias activas del nivel y requiere un único plan educativo vigente. El orden por ID sirve para mostrar datos de forma estable. Cada materia incorpora evaluation_plan_id y evaluation_plan_name desde ACAsignaturaPlan y ACPlanEvaluativo, como datos opcionales de evaluación académica. Los porcentajes de ACDetallePlanEvaluativo describen evaluaciones y no se convierten en requisitos de ingreso ni condiciones financieras. requirements es null porque no se confirmó una fuente de requisitos de admisión.

ValorOrdinaria representa únicamente la enseñanza del semestre o nivel ofertado. price_cop y full_cost_cash_cop tienen ese alcance. Los uniformes y otros elementos o cargos adicionales quedan excluidos, sin valoración en esta fuente. No es el precio de todo el programa ni el costo global de estudiar con todos los extras.

### Planes financieros de la oferta

financial_plans admite hasta doce planes. Un plan no resoluble se informa mediante null y data_quality. Los importes válidos son pesos COP enteros positivos, sin redondeo implícito.

| Campo del plan | Uso |
|---|---|
| external_id | ID compuesto de oferta, nivel y plan. |
| source_plan_id, source_tariff_id | Referencias de AFPlanes y AFTarifas. |
| name, source_plan_type | Nombre y tipo de origen. |
| valid_from, valid_until | Permanecen null, opcionales y no bloqueantes por decisión del propietario. |
| conditions | Permanece null y bloquea mientras no haya fuente confirmada. |
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
7. Con catalogKey, consultar Programs sin period_id para usar el período ofrecido; habilitar period_id sólo para una consulta explícita, y copiar programId. Consultar ProgramOffers con ese mismo período y copiar commercialOfferId. Consultar Offer e inspeccionar el 422 parcial esperado.
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


## 9. Definición institucional de oferta por período

La oferta comercial pertenece al programa y al semestre/período de ACProgramaOfrecido. Los horarios físicos y sus sedes no crean otras ofertas.
Se conservan las referencias Id_PrgOfrecido-nNivel para distinguir el nivel tarifado de cada período. campus_id se mantiene null por compatibilidad de formato y no genera data_quality.
Un consumidor que exigía una sede no nula debe ajustar esa validación a esta definición institucional. La compatibilidad de ese consumidor no se comprobó en esta entrega.

La investigación de tablas, claves y módulos SIIE confirmó que AFPlanes publica nombre, tipo, importes y FechaPago, y que AFPlanesSUDI filtra por período.
No hay en esas columnas un intervalo confirmado de vigencia comercial ni condiciones contractuales del financiamiento.
AFPlanesConPrograma no contiene filas en la base local consultada y no se utiliza para completar asociaciones.
La fuente financiera permanece en la asociación AFTarifas por programa/período/nivel con AFPlanes del mismo período.

ACPlanEducativo aporta el currículo vigente y las materias del nivel, aunque el período de creación del currículo sea anterior.
ACPlanEvaluativo aporta el nombre del esquema evaluativo de cada materia, por ejemplo un esquema porcentual de evaluaciones. Ese dato no acredita requisitos de admisión ni términos financieros.

Siguen pendientes una fuente confirmada para requisitos de ingreso y condiciones de los planes. Offer conserva el 422 parcial por esos bloqueos; las vigencias comerciales null son opcionales. Se necesita completar el mapeo, no rellenarlos con fechas académicas, vencimientos de cuotas o texto supuesto.
## Período predeterminado: compatibilidad y verificación

Programs y ProgramOffers devuelven period_id efectivo, offered_period_id y offered_period_source. Offer también expone offered_period_id, offered_period_source y period_active. Los ejemplos de query con idPeriodo son selecciones explícitas opcionales; en Postman quedan deshabilitadas inicialmente. El cuerpo de POST/PUT mantiene idPeriodo obligatorio, sin cambios de idempotencia o revisión.

Compilación y 15 comprobaciones aisladas del resolver satisfactorias; 34 aserciones GET en IIS local satisfactorias el 19 de noviembre de 2026. El caso futuro/inactivo académico se validó de forma aislada, sin modificar la base. Offer conserva 422 por requisitos y condiciones financieras faltantes; las vigencias comerciales null no bloquean y no se completan con fechas de GEPeriodo. La disponibilidad del servidor público y la integración del consumidor no se verificaron.

## Vigencias comerciales opcionales — 19 de noviembre de 2026

Por decisión del propietario, se omite por ahora la validación de intervalos de vigencia comercial. price_valid_from, price_valid_until y valid_from/valid_until de cada plan se conservan como null por compatibilidad y no generan incidencias ni bloquean la completitud del productor. No se derivan de GEPeriodo ni de mínimos/máximos de pagos.

Las fechas reales de abono y cuotas, source_payment_date y academic_start/academic_end permanecen intactas. También se conservan las fechas de seguimiento. Requisitos de admisión y condiciones financieras siguen siendo bloqueos reales: Offer conserva el 422 parcial mientras falten. El consumidor externo debe aceptar vigencias null para usar esta compatibilidad; no se ha verificado su adaptación ni su ejecución.

## Estudiantes y contactos nativos — 19 de noviembre de 2026

Entrega local del 19 de noviembre de 2026. Tres consultas de sólo lectura, bajo /Api/CRM/v1/, usan la credencial General de Admisiones. El token exclusivo de Commercial no las autoriza. No matriculan personas ni consultan cartera, notas o asistencia.

## Consultas

| GET | Parámetros | Resultado |
|---|---|---|
| Estudiantes.aspx | idPeriodo, idPrograma, idJornada, idEstadoMatricula, q, offset opcionales | Hasta 25 registros nativos con matrícula real en el período. Orden por idEstudiante e idMatricula. |
| Estudiante.aspx | idEstudiante obligatorio; idPeriodo opcional | estudiante y matriculas[] del registro nativo y período solicitado. 404 student_not_in_period si no tiene matrícula en él, incluido ID inexistente. |
| FiltrosEstudiantes.aspx | idPeriodo opcional | programas, jornadas, niveles y estadosMatricula observados entre las matrículas del período. |

Las respuestas satisfactorias son {status:"ok",data:{...}}. El listado incluye idPeriodo, items, offset, limit=25, hasMore y procedencia. Para continuar, sumar limit al offset y conservar filtros. Es una consulta viva, no una instantánea. El índice único nativo de estudiante/período impide repetir ese vínculo; personas con otros registros de estudiante no se fusionan.

idPeriodo omitido usa CrmOfferedPeriod: parámetro 38 válido y existente; en su defecto, único académico activo. Un período explícito permite históricos. Los IDs aceptan enteros positivos; idEstadoMatricula acepta 0 hasta 2147483647 porque su columna real es int. offset admite 0..1000000. q admite 100 caracteres, busca nombre o documento y no devuelve el documento. Parámetros numéricos duplicados y q duplicado devuelven 400. idEstadoMatricula filtra GEEstudiante.EstadoMtla actual, incluso en períodos históricos; no expresa un estado histórico de cada matrícula.

## Datos y límites

- Identidad: idEstudiante corresponde a GEEstudiante.Id_Estudiante. Nombre y telefono/celular/correo proceden exclusivamente de Nombres/apellidos, Telefono/Celular/Mail. Se recortan espacios exteriores y vacío se devuelve null. No se normaliza país, no se valida contacto ni se declara consentimiento.
- Matrícula: idMatricula de GEMatricula, idPeriodo y periodo de esa matrícula; idOferta e idPeriodoOferta de la oferta ligada al registro de estudiante; programa, escuela y modalidad de sus relaciones oficiales. nivel y fechaMatricula proceden de GEMatricula. idJornada/jornada usan GEMatricula.Id_Jornada y ACJornada, sin suplir una ausencia con la jornada del programa.
- idPersona e idAspirante permanecen null: no hay FK oficial verificada entre estos registros. No se unen personas por documento, nombre, correo o teléfono. idPeriodoIngreso e idSede permanecen null sin fuente confirmada. No se inventan creación/modificación, versión ni baja.
- El estado se devuelve en el registro de estudiante/listado y en procedencia, no como historia de cada elemento de matriculas[]. Nombre del estado reproduce el CASE ejecutable de GEEstudianteSUDI: 0 Inscrito, 1 Plan Asignado, 2 Matriculado, 3 Retirado. Otros códigos o estado ausente se conservan con nombre null y requiereRevisionEstado=true; en el filtro el indicador es requiereRevision. El comentario del SP contiene otra enumeración y no se usa como contrato. No se usa GEEstados: es catálogo geográfico. No se utiliza ACEstadoSeguimiento.
- ACInscripcion tiene FK de estudiante y jornada, pero no período y puede contener varios registros. No se elige arbitrariamente una inscripción para completar cohorte o matrícula. La ficha no incorpora matrículas de otro idEstudiante por coincidencias personales.

## Ampliación compatible de aspirantes

Aspirantes.aspx y Aspirante.aspx agregan telefono, celular y correo al SELECT compartido, desde ACAspirante.Telefono/Celular/Mail, con el mismo tratamiento de blancos. No cambia ningún campo anterior, período, filtro ni comprobación de pertenencia. POST/PUT, sus cuerpos, idempotencia y revisiones no se modifican. Esta ampliación no incluye vínculos nuevos ni permite escribir datos personales.

## Errores y seguridad

GET/OPTIONS únicamente; otro método devuelve 405. ApiSecurity general conserva HTTPS, CORS, límites, correlación y 401 por credencial inválida o de Catálogo. 400 indica parámetros inválidos; 404 período inexistente o estudiante sin matrícula del período; 503 offered_period_unavailable indica falta de resolución inequívoca, y students_unavailable un fallo SQL sin exponer su contenido. idEstadoMatricula desconocido es un filtro válido y puede devolver lista vacía; nunca se transforma en activo.

## Verificación y publicación

Compilación .NET Framework/Roslyn satisfactoria; 92 aserciones HTTP/SQL focalizadas y dos comprobaciones adicionales de estado 0 y un código real sin etiqueta. Contactos y vínculos se compararon con SQL sólo en memoria. Los recibos guardan afirmaciones y conteos, sin nombres, documentos, teléfonos, correos ni IDs personales. Se probaron páginas, filtros, histórico explícito, 400/404/401, PUT rechazado y OPTIONS. No hubo DDL/DML, fixtures ni escrituras POST/PUT. Producción e integración del consumidor siguen pendientes.

El documento Students.openapi.json describe el transporte. La colección manual conserva credenciales vacías y contiene ahora 14 operaciones. La publicación y reversión por FTP se detallan en LEEME del paquete; no requieren comandos IIS/PowerShell ni editar configuración.

### Ejemplo ficticio de identidad

~~~json
{"idEstudiante":900001,"nombre":"Persona ficticia","telefono":null,"celular":null,"correo":null,"idEstadoMatricula":2,"estadoMatricula":"Matriculado","idPersona":null,"idAspirante":null,"requiereRevisionEstado":false}
~~~

Los IDs y nombres del ejemplo son ficticios. Completar manualmente idEstudiante con el ID de Estudiantes. idEstadoMatricula queda vacío hasta seleccionar un código de FiltrosEstudiantes; 0 es válido. El idPeriodo de estos GET permanece deshabilitado inicialmente para usar el ofrecido.
