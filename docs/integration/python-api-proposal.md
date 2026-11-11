# Propuesta de APIs Python: primer catálogo académico de lectura

**Estado vigente:** cuatro de las siete rutas verificadas con SQL/HTTP/navegador real: `periods` (32), `schools` (12), `modalities` (2) y `programs` (228) con filtros opcionales escuela/modalidad. [Cierre de programas y permisos mínimos](../reports/programs-local-api.md). DTO Program aprobado para este corte: únicamente `id`, `label` nullable, `schoolId`, `modalityId`; no `code` ni `sourceStudyShiftId` de la propuesta original más amplia. Permanecen propuestas `offerings`, `study-shifts` y `offerings/{offeringId}/study-shifts`, con autorización/contrato/permisos propios pendientes. El texto y snapshots siguientes son históricos; no describen automáticamente la frontera actual del lector ni aprueban IAM/fase 1.

**Actualización del primer corte:** períodos completado y verificado con 32 filas reales, TLS/permisos mínimos, doce casos HTTP y navegador páginas 25+7. El propietario autorizó la implementación y posteriormente el lector `crm_catalog_reader` con SELECT exclusivo y denegaciones heredadas, sin modificar tablas/datos/PUBLIC. [Contrato ejecutable y recuperación](periods-local-runbook.md), [informe y aprobación literal](../reports/periods-local-api.md). Las otras seis rutas y controles empresariales siguen propuestos. El texto siguiente conserva la propuesta original anterior a esa implementación; no amplía automáticamente permisos o endpoints.

**Estado: propuesto, pendiente de aprobación; no implementado.** **Fecha:** 2026-10-14, America/Bogota. Se propone conectar React con FastAPI mediante un primer contrato GET de catálogo SIIE, preservando SQL Server como fuente única. La base no se modifica; no se crean tablas, migraciones, usuarios SQL o endpoints en esta entrega.

La evidencia es el [inventario de DBSIIE](../reports/dbsiie-schema-inventory.md), captura `2026-10-14T16:20:04.8577744Z`. Separamos estructura observada de semántica pendiente: un programa, su oferta por período y una jornada asociada a esa oferta son identidades distintas.

## Corte propuesto y estado actual

El backend actual ofrece únicamente [salud](../../backend/app/main.py); [configuración](../../backend/app/config.py) admite solo `local_demo`. React mantiene fichas, hilos, comentarios y configuración en [estado local de App](../../frontend/src/App.tsx). Estos documentos no habilitan otro modo ni conectan ese estado a SQL.

Primer corte: catálogos sin datos de personas, con autenticación y autorización de servidor antes de exponerlos a usuarios o entorno compartido. No incluye aspirantes, estudiantes, contacto, pagos, matrícula, formularios POST, conversaciones, tareas, IA o proveedores. No hay contrato probado de persistencia CRM para esos recursos.

Arquitectura alineada con la [base aceptada](../architecture.md): React → transporte FastAPI → caso de uso autorizado → adaptador de lectura → SQL Server con TLS validado. Las rutas no ejecutarán SQL ni resolverán reglas académicas por su cuenta. El driver/ORM y sus versiones siguen pendientes de selección, ADR cuando corresponda y prueba Python; no se adopta una dependencia por esta propuesta.

## Recursos v1 y consultas permitidas

Prefijo propuesto: `/api/v1/catalog`. Todas las listas usan `limit` y `offset`; los filtros siguientes son el allowlist completo de cada ruta. Los IDs son enteros de rango SQL `int`, no etiquetas ni posiciones del select. No asumir que toda PK sea positiva hasta verificar el contrato de datos.

| Método/ruta propuesta | Filtros adicionales | Fuente y orden fijo | DTO |
|---|---|---|---|
| `GET /periods` | Ninguno | `dbo.GEPeriodo`, `Id_Periodo ASC` | `Period` |
| `GET /schools` | Ninguno | `dbo.ACEscuela`, `Id_Escuela ASC` | `School` |
| `GET /modalities` | Ninguno | `dbo.ACModalidad`, `Id_Modalidad ASC` | `Modality` |
| `GET /programs` | `schoolId?: int`, `modalityId?: int` | `dbo.ACProgramas`, `Id_Programa ASC` | `Program` |
| `GET /offerings` | `periodId: int` requerido; `programId?: int`, `schoolId?: int` | `ACProgramaOfrecido`; unir `ACProgramas` para escuela; `Id_PrgOfrecido ASC` | `Offering` |
| `GET /study-shifts` | Ninguno | `dbo.ACJornada`, `Id_Jornada ASC` | `StudyShift` |
| `GET /offerings/{offeringId}/study-shifts` | Ninguno | `ACDetalleJornada` unido a `ACJornada`; `Id_DetalleJornada ASC` | `OfferingStudyShift` |

Las rutas de la tabla se concatenan al prefijo. `offset` predeterminado 0, mínimo 0; `limit` predeterminado 25, entre 1 y 100. Son límites propuestos, pendientes de aceptación/carga. La lista devuelve un máximo de `limit` elementos; obtener uno adicional para `hasMore` mantiene el trabajo acotado sin conteos completos. Un offset máximo de 10.000 es propuesta de protección; evaluar cursor antes de ampliar ese límite.

No se admiten `sort`, nombres de tabla/columna, SQL libre, filtros arbitrarios o parámetros desconocidos. Parámetros duplicados/ambiguos, tipos inválidos, límites excedidos o falta de `periodId` producen 422. Parametrizar valores; el adaptador usa columnas y orden definidos en servidor. Un filtro válido sin coincidencias devuelve 200 y lista vacía.

Sin filtro implícito «activo», año actual o fecha actual. `GET /periods` conserva las fechas de origen y su bit de estado sin reinterpretarlo; `GET /offerings` exige período elegido explícitamente. Antes de mostrar estas opciones como inscribibles se requiere confirmar la regla de disponibilidad. Un catálogo no equivale a autorización de inscripción.

## DTOs mínimos y mapeo SQL

Nombres de contrato en inglés; etiquetas son valores del catálogo, no traducciones ni enums derivados de la UI. `?` indica campo nullable, no campo que se omite. Cada DTO mantiene claves SIIE estables; no renumera registros. Tipos y columnas están comprobados en el inventario; significado y exposición son propuestas.

| DTO | Campos JSON propuestos → origen SQL |
|---|---|
| `Period` | `id: int → GEPeriodo.Id_Periodo`; `label: string(20) → Periodo`; `startDate: date → FechaInicio`; `endDate: date → FechaFinal`; `sourceState: boolean → EstadoPeriodo` |
| `School` | `id: int → ACEscuela.Id_Escuela`; `label: string(100) → NomEsla` |
| `Modality` | `id: int → ACModalidad.Id_Modalidad`; `label: string(20) → Modalidad` |
| `Program` | `id: int → ACProgramas.Id_Programa`; `code: string(10) → CodigoPrograma`; `label: string(200)? → NombrePrograma`; `schoolId: int → Id_Escuela`; `modalityId: int → Id_Modalidad`; `sourceStudyShiftId: int? → Id_Jornada` |
| `Offering` | `id: int → ACProgramaOfrecido.Id_PrgOfrecido`; `programId: int → Id_Programa`; `periodId: int → Id_Periodo` |
| `StudyShift` | `id: int → ACJornada.Id_Jornada`; `label: string(15) → DetalleJornada` |
| `OfferingStudyShift` | `id: int → ACDetalleJornada.Id_DetalleJornada`; `offeringId: int → Id_PrgOfrecido`; `studyShiftId: int → Id_Jornada`; `label: string(15) → ACJornada.DetalleJornada` |

La longitud indicada procede de tipos `varchar`; no convertirla ciegamente en una validación universal de caracteres Unicode sin comprobar codificación/collation y traducción del driver. Conservar etiquetas NULL donde el origen lo permite: no sustituir por «sin nombre», inferir código o descartar el registro silenciosamente. La UI puede mostrar un fallback visual sin alterar la identidad ni el DTO.

Separar IDs y etiquetas: escuela y modalidad se resuelven contra sus propios catálogos. `sourceStudyShiftId` conserva un FK nullable del programa; el nombre evita declararlo jornada predeterminada. La lista por oferta usa `ACDetalleJornada`, no ese FK del programa. El formulario futuro conservará `offeringId` y la identidad de la relación elegida, tras confirmar el contrato de inscripción.

No publicar `Id_Plan`, `Semestres` o fechas del programa hasta definir su uso. No convertir jornadas en horarios exactos de clases. No hardcodear códigos de estado a partir de etiquetas frontend: `EstadoPeriodo` se expone como bit de origen, sin afirmar `true = inscribible`. Si se aprueba un enum futuro, tendrá códigos estables y traducción explícita respaldada por negocio.

Fechas SQL `date`: cadena ISO `YYYY-MM-DD`, sin zona ni hora inventadas. Un futuro `datetime` no implica UTC; su zona requerirá contrato. Importes `decimal/numeric` futuros conservarán precisión/escala y una política decimal explícita; no exponerlos como float por defecto. Estas rutas iniciales no contienen importes.

## Relaciones y comportamiento observable

- Oferta → programa por `Id_Programa`; oferta → período por `Id_Periodo`; programa → escuela/modalidad por sus FK. El filtro `schoolId` en ofertas se aplica mediante el programa.
- Oferta–jornada → oferta y jornada por FK. Cada item devuelve `Id_DetalleJornada`; pueden existir dos items con igual par oferta/jornada porque no hay UNIQUE de ese par acreditado.
- `ACProgramaOfrecido` sí declara UNIQUE `(Id_Periodo, Id_Programa)`. No extrapolarlo a matrícula, aspirantes o fichas CRM.
- Para `/offerings/{offeringId}/study-shifts`, un ID de oferta inexistente devuelve 404; oferta existente sin relaciones devuelve 200 con lista vacía. Comprobar existencia con lectura acotada y el mismo permiso.
- Cada solicitud puede observar cambios entre páginas: offset y orden fijo no son un snapshot de negocio. No mantener transacciones entre solicitudes ni prometer consistencia histórica. Cambios de schema invalidan el mapeo y se revisan antes de continuar.

Ejemplo completamente sintético, sin valores de filas de DBSIIE:

```json
{
  "items": [{ "id": 101, "programId": 201, "periodId": 301 }],
  "page": { "limit": 25, "offset": 0, "hasMore": false }
}
```

Los IDs del ejemplo no acreditan existencia. No añadir `total` sin una consulta/contrato de coste aprobados. DTOs y envelope se documentarán en OpenAPI cuando se autorice implementar.

## Seguridad, errores y operación propuestos

Autenticación de servidor y permiso propuesto `catalog:read` para las siete rutas; tecnología, roles concretos y asignación siguen P-017/P-026. Ningún dato personal se expondrá anónimamente. Un formulario público futuro necesita un contrato separado de catálogos publicables, token/consentimiento y límites; no hereda acceso a personas ni a todo SIIE.

Principal SQL de mínimo privilegio, permisos de lectura exclusivamente sobre fuentes aprobadas, sin DDL/DML ni EXECUTE general. No se crea ni modifica ese principal ahora. Permisos de metadata del colector y autenticación Windows de la prueba TLS no son permisos de runtime backend.

TLS obligatorio con validación del certificado; [evidencia actual](../reports/local-sql-tls.md) acredita solo memoria compartida desde sesión Windows. Configuración por ambiente fuera de Git, secretos por mecanismo aprobado, sin cadenas reales de conexión en documentación/logs. La prueba Python debe acreditar el driver elegido, identidad efectiva, cifrado, nombre validado y permisos; no se soluciona con `TrustServerCertificate=True`.

Timeout total SQL propuesto de cinco segundos y respuesta HTTP de diez segundos, ambos por validar con medición/driver; concurrencia/pool limitados mediante capacidad aprobada. No retry automático ilimitado ni escalar permisos ante errores. Hasta definir frescura, sin caché que haga parecer vigente una oferta antigua. CORS restringido al origen frontend aprobado; no habilitar comodín con credenciales.

| HTTP | Código de contrato propuesto | Condición |
|---|---|---|
| 200 | — | Lista acotada, incluso vacía. |
| 401 | `AUTHENTICATION_REQUIRED` | Sesión ausente o inválida. |
| 403 | `CATALOG_ACCESS_DENIED` | Falta de permiso/ámbito. |
| 404 | `OFFERING_NOT_FOUND` | Oferta no existente en la ruta anidada. |
| 422 | `INVALID_REQUEST` | Parámetros desconocidos, duplicados, mal tipados o fuera de límites. |
| 503 | `CATALOG_UNAVAILABLE` | Timeout, conexión/TLS o contrato SQL no disponible. |

Error mínimo: `code`, `message` genérico y `correlationId`; no incluir SQL, nombres internos de servidor, credenciales, parámetros personales o stack. Correlación generada/validada en servidor; registrar ruta, duración y código sin cadenas de conexión. Errores inesperados de aplicación mantienen 500 genérico `INTERNAL_ERROR`, sin reclasificar todos los bugs como caída de SQL.

`/health/live` sigue salud del proceso. El futuro cambio de `/health/ready` requiere contrato explícito; no hacerlo 200 por encontrar el archivo de inventario o validar solo una cuenta elevada. `local_demo` conserva sus bloqueos hasta autorizar modo conectado, no mezclar fallback sintético con datos reales sin señalización.

## Contratos diferidos

`ACAspirante`, `ACAspirantePorOferta` y `GEEstudiante` tienen identidades/columnas distintas. No unirlos automáticamente por documento, teléfono o correo, ni convertir Clientes demo en estudiantes. Antes de cualquier GET con datos personales se necesitan finalidad/retención, test anonimizados, autorización por recurso, paginación y protección contra enumeración. Antes de POST/PATCH se necesitan además contrato de transacción, idempotencia, concurrencia, auditoría y reversión no productiva con aprobación específica.

`APIProgramasConJornada`, `APICatalogosPreinscripcionPLUS` y `GEProgramaOfrecidoSelectActivo` son procedimientos observados, sin cuerpo ni resultados revisados. No invocarlos ni asumir efectos de lectura por sus nombres. El primer adaptador propuesto usa SELECT acotados explícitos sobre columnas aprobadas, nunca reflexión automática de todas las tablas, `create_all` o migraciones SIIE.

Hilos, comentarios, tareas, Ajustes y prospectos CRM requieren contrato de almacenamiento independiente dentro de las invariantes SSOT. No hay adopción implícita de tablas `CRM_`, Redis como autoridad, JWT de referencias externas o decisiones SQL emitidas por IA.

## Aceptación futura y orden de implementación

1. Propietario/DBA confirma fuentes permitidas, diferencia programa/oferta/jornada, semántica de período/estado y reglas de elegibilidad. El catálogo inicial describe opciones; la decisión de inscripción sigue separada.
2. Cerrar naturaleza/aislamiento de datos de prueba, roles y acceso mínimo; acordar driver, configuración, modo conectado y seguridad antes de leer datos desde API. P-001/P-004/P-005/P-006/P-017/P-026 conservan partes abiertas.
3. Autorizar una primera unidad pequeña: `GET /api/v1/catalog/periods`, DTO, caso de uso y adaptador de lectura. No crear todos los endpoints ni infraestructura futura de una vez.
4. Verificar en copia autorizada con datos sintéticos: mapeo de tipos/NULL, fechas, orden/paginación, límites, filtros desconocidos/duplicados, inyección, 401/403, caída/timeout y error minimizado. Acreditar ausencia de DML/DDL/EXECUTE y TLS validado desde Python con permisos efectivos mínimos.
5. Ampliar a escuelas/modalidades/programas/ofertas/jornadas tras aceptar ese corte; probar FK, oferta inexistente y relaciones duplicadas. React recibe DTOs tipados con carga/vacío/error explícitos y conserva selecciones por ID, no por etiqueta.

Esta entrega verifica estructura documental, referencias locales y correspondencia offline con metadata. Ninguna prueba Python/SQL/API, instalación, build, commit, push o despliegue se ejecutó para esta propuesta. La aprobación del documento autoriza su contrato únicamente si el propietario lo expresa; implementar y conectar requieren la autorización correspondiente.
