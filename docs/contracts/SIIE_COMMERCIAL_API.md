## Estado actual: contrato recibido y solicitud consolidada — 2026-11-18

P16 fue retomada. El Catálogo ASPX real está autenticado y sus listados funcionan; falta clave General para Admisiones y el detalle de ofertas devuelve503en SIIE. Estudiantes aún no tiene rutas entregadas. La [solicitud consolidada y matriz de las once operaciones](../adaptation/P16_SIIE_PROVIDER_ISSUES_20261118.md) es la referencia actual para aspirantes, estudiantes/matrículas, programas ofrecidos en el período activo, contado y planes financiados. También distingue lo que debe ampliar SIIE de lo que falta construir en RinovaPlus.

La propuesta REST y los nombres de variables/rutas del documento inferior son **históricos, anteriores al contrato ASPX recibido**. Para configurar la integración actual usar `SIIE_API_BASE_URL`, `SIIE_API_HOSTS`, `SIIE_CATALOG_API_TOKEN` y, cuando se entregue, `SIIE_ADMISSIONS_API_TOKEN`, según el manual P16. No interpretar la afirmación histórica de «diferida» como estado vigente ni aquella exclusión de estudiantes como límite del alcance ahora solicitado por el propietario.

## Propuesta inicial conservada — 2026-11-17

# API SIIE → RinovaPlus: catálogo académico y financiero

**Estado vigente:** integración trasladada a [P16 y diferida por el propietario](../adaptation/P16_SIIE_INTEGRATION.md). Este contrato y la base implementada se conservan para retomarla; no bloquean P13 ni autorizan configurar credenciales ahora.

Solicitud institucional del 17 de noviembre de 2026. **Fuente oficial: API del sistema SIIE conectado con DBSIIE.** RinovaPlus no necesita usuario SQL ni acceso directo a sus tablas. El conector es de sólo lectura y está desactivado hasta configurar el endpoint y la credencial. No hay cobros, matrículas, creación de obligaciones ni escritura hacia SIIE.

## Qué pedir al equipo de SIIE

1. **URL HTTPS del ambiente de pruebas y producción**, certificados válidos, documentación OpenAPI y responsable técnico. Acordar versión, límites, tiempos de espera, códigos de error y ventana de mantenimiento.
2. **Credencial exclusiva de consulta** para RinovaPlus, con alcance de catálogo/ofertas/precios/planes, fecha de expiración y procedimiento de rotación/revocación. Puede entregarse el token Bearer por un canal seguro. Si SIIE requiere OAuth client_credentials o mTLS, adaptar ese transporte; no pegar contraseñas ni tokens en el chat.
3. **Identificadores estables** para programa, escuela, sede, jornada, modalidad y período/cohorte. Solicitar el ID de **oferta** que los combina: una tarifa de jornada/sede/período no debe aplicarse a otra oferta.
4. **Programas académicos**: código, nombre oficial, escuela, alias, descripción, modalidad, duración con unidad (meses/semestres/horas), jornadas, materias/módulos con su orden y requisitos. Indicar activo/inactivo y enlace oficial de inscripción/información.
5. **Contado**: valor, concepto exacto (matrícula, semestre, programa completo, etc.), moneda COP, vigencia desde/hasta y **costo total obligatorio completo**. Desglosar o declarar qué incluye/no incluye: inscripción, matrícula, mensualidades, materiales, seguros, certificación/grado y demás cargos aplicables. No confundir matrícula con el precio de todo el programa.
6. **Cada plan financiado**: ID y nombre, vigencia, abono inicial y fecha límite, número de cuotas, valor y vencimiento de **cada cuota**, costo total financiado y condiciones. El total oficial debe coincidir con abono + cuotas; pedir incluidos intereses y cargos, descuentos, requisitos y excepciones. No calcular fechas ni intereses en el CRM por suposición.
7. **Fechas y alcance de la cotización**: aclarar si el calendario pertenece a una cohorte o depende de una fecha de inicio/matrícula. Si depende del aspirante o de su fecha, solicitar un endpoint de **simulación sin escritura**, con la fecha base y oferta como entrada; no reutilizar un calendario personal como oferta general.
8. **Actualización y trazabilidad**: revisión/versión de origen, fecha de generación con zona horaria, fecha de última modificación, bajas y cambios de vigencia. Acordar consulta incremental/paginada (cursor/updated_since) y un webhook firmado de invalidación como ampliación. Pedir muestras de contratos reales anonimizadas de dos programas, incluyendo uno con varios planes y uno sin tarifa vigente.

No se necesitan datos de estudiantes, notas, historias clínicas, números de documento, pagos personales o credenciales SQL para esta integración. Si posteriormente se requiere consultar un estado de pago individual, tendrá un contrato y permisos separados.

## Endpoints propuestos para acordar con SIIE

| Endpoint de SIIE | Finalidad | Estado RinovaPlus |
|---|---|---|
| `GET /v1/crm/programs?cursor=...` | Catálogo paginado de programas y escuelas, con IDs y bajas. | Contrato propuesto; sincronización masiva pendiente. |
| `GET /v1/crm/programs/{program_id}/offers` | Sedes, jornadas, modalidades y períodos disponibles; devuelve IDs de oferta. | Contrato propuesto; selector de ofertas pendiente. |
| `GET /v1/crm/offers/{offer_id}` | Ficha académica y comercial completa, cotización general con planes de la cohorte. | Adaptador y preview implementados; sin llamadas hasta configurar. |
| Cotización/simulación sin escritura | Calendario dependiente de fecha base, si SIIE lo necesita. | Por definir con SIIE. No se sustituye por cálculos de IA. |

Estas rutas son la propuesta que entiende el adaptador inicial, **no se afirma que SIIE ya las tenga**. Si el proveedor expone otras rutas o nombres de campos, se mapea su contrato en `backend/app/institutional/siie_catalog.py`.

## Respuesta de la oferta: `siie-crm-commercial-v1`

| Campo | Contenido requerido |
|---|---|
| `schema_version` | `siie-crm-commercial-v1` |
| `source_system`, `source_revision`, `generated_at` | `DBSIIE`, revisión no vacía y fecha ISO8601 con zona horaria. El preview inicial exige respuesta generada hace menos de 24 horas. |
| `offer_id`, `program_id`, `period_id`, `campus_id`, `shift_id` | IDs como strings; `offer_id` debe coincidir con el solicitado. |
| `currency`, `active` | `COP` y estado real de la oferta. Inactiva se rechaza. |
| `name`, `school`, `schedule` | Nombres oficiales de programa, escuela y jornada. |
| `commercial.duration`, `.modality`, `.syllabus`, `.requirements` | Hechos explícitos de duración, modalidad, materias y requisitos. |
| `commercial.price_cop`, `.price_concept`, `.price_valid_from`, `.price_valid_until` | Valor del concepto declarado y vigencia. Sin concepto/vigencia no se utiliza como precio en respuestas de IA. |
| `commercial.full_cost_cash_cop` | Costo obligatorio total de contado. Importes en pesos enteros COP; nunca en centavos ambiguos. |
| `commercial.cost_inclusions`, `.cost_exclusions` | Conceptos incluidos y excluidos, expresados claramente. |
| `commercial.financial_plans[]` | Máximo 12 planes por oferta. Cada plan contiene los campos indicados abajo. |

Cada plan:

- `external_id`, `name`, `valid_from`, `valid_until`.
- `initial_payment_cop`, `initial_payment_due_date`.
- `total_cost_cop`, `conditions`.
- `installments[]`: `number` consecutivo empezando en 1, `amount_cop`, `due_date`. Máximo 120 cuotas. Las fechas son `YYYY-MM-DD`, ordenadas y posteriores o iguales al abono.

El servidor valida `initial_payment_cop + sum(installments.amount_cop) == total_cost_cop`; rechaza discrepancias en vez de “corregirlas” con IA. Los planes futuros o vencidos quedan fuera del contexto de respuesta. El esquema completo ejecutable es `SiieOffer` y sus modelos de `program_commercial.py`.

## Qué hacemos de este lado

1. Entregar este contrato a SIIE y confirmar transporte, rutas y alcance de oferta. Probar un programa y después la segunda oferta con jornada/período diferentes.
2. En **Coolify → backend → Environment Variables → Production**, guardar con Runtime activo:

   - `SIIE_CATALOG_API_URL`: URL base HTTPS, sin `/v1/crm/...` ni parámetros.
   - `SIIE_CATALOG_API_HOSTS`: host autorizado exacto, sin esquema; admite lista separada por comas.
   - `SIIE_CATALOG_API_TOKEN`: token de sólo lectura. Guardarlo únicamente en Coolify; no en frontend, Git o chat.

3. Redeploy del backend. No hace falta nueva tabla SQL: la ficha comercial mantiene su JSON versionado existente. El token queda en el entorno del backend y no se devuelve a la interfaz.
4. Ir a **Académico → Consultar catálogo comercial de SIIE**, introducir un ID de oferta válido y pulsar **Consultar SIIE**. La API interna `POST /api/v1/agents/programs/import-siie` exige `agents.manage`, usa el transporte fijo GET hacia SIIE y devuelve `draft`, `source`, `review_required=true`, `saved=false`, `siie_written=false`.
5. Revisar diferencias, costo total, abono, cuotas, fechas y vigencias. **Aplicar al borrador** no guarda. El editor responsable revisa y pulsa **Guardar programa** para incorporarlo al catálogo de Gemini.
6. Probar consulta por nombre, continuación de conversación, contado vs financiado, costo completo, datos faltantes, vigencia vencida y toma de control Humano; contrastar cada cifra con la API. Luego aceptar el piloto P13.

El adaptador mantiene TLS, dominio autorizado, una sola consulta, sin redirecciones ni proxy de entorno, límite de respuesta de 512 KiB y timeout de 12 segundos. No sigue URLs recibidas del usuario ni registra la credencial. Un fallo no altera las fichas guardadas. El ejemplo de integración no valida por sí solo el mapeo completo de DBSIIE.

## Pendientes después de esta base

Conexión real y contrato final; listado paginado/selector de ofertas; vínculo estable oferta externa ↔ ficha local; sincronización revisada y baja/expiración; reconciliación de modificaciones manuales; autenticación alternativa si SIIE la exige; aceptación de dos programas. Hasta acordar el vínculo de oferta, conservar una ficha por oferta de sede/jornada/período para no mezclar planes. El conector inicial no sincroniza en segundo plano ni sobreescribe precios.
