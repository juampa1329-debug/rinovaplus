# Esquemas definidos y validables LOCAL-v2

Las **135 operaciones antes pendientes tienen definición LOCAL**, no aprobación conectada: 77 cuerpos nuevos y 58 operaciones sin cuerpo (57 GET y un DELETE). Los 13 cuerpos heredados conservan modelos, opcionalidad y compatibilidad. El inventario sigue siendo 151 operaciones: 148 negocio siempre 501, dos health 200/503 y metadata 200. Fase 1 permanece diferida; no hay DB, proveedor, autenticación, escritura, envío ni almacenamiento de negocio.

## Ruta de revisión

1. [Cobertura generada](local-schema-coverage.md): modelos, campos y evidencia de las 148 operaciones.
2. [Ejemplos canónicos](local-schema-catalog.json): entrada válida sintética y resultado **planeado**, por operation ID.
3. [OpenAPI generado](local-openapi.json): restricciones, tipos anidados y referencias resolubles. Las respuestas de negocio solo son 501/422; `x-local-contract-ref` apunta al resultado planeado, no a una respuesta exitosa.
4. [Informe A-025/P-038](../reports/local-schema-definitions.md): checks, límites y aceptación independiente pendiente. [A-024 histórico](../reports/local-endpoint-contracts.md) conserva los conteos anteriores.

## Registro único y revisión compatible

`backend/app/contracts.py` conserva la única lista de métodos/rutas/operation IDs. `backend/app/local_registry.py` declara exactamente una vinculación por cada operación: cuerpo o ausencia explícita, query, path, resultado planeado, evidencia y ejemplos validados por Pydantic. No se reemplaza una entrada desconocida por un modelo vacío. El registro tiene modelos compartidos cuando la semántica coincide; **135 operaciones no significa 135 clases distintas**.

Los DTOs en `local_models.py` representan estructuras locales; `local_plans.py` contiene intenciones tipadas para mutaciones, con `execution: planned_not_executed` y revisión humana requerida. `local_samples.py` es la fuente canónica de fixtures de modelos; las exportaciones se generan desde el registro, no se mantienen tablas o payloads paralelos. Cada ejemplo se valida mediante `model_validate_json`, también para enums estrictos.

| Metadata | Significado |
|---|---|
| `schema_status: local_defined` | La forma LOCAL tiene DTO y validación; no implementa negocio. |
| `schema_status: provisional` | Uno de los 13 cuerpos anteriores, conservado sin endurecimiento. |
| `schema_revision: local-v2` | Revisión local intencional: `{}` ya no es válido en los 77 cuerpos nuevos. |
| `connected_status: approval_pending` | Las 148 operaciones todavía requieren aprobación y pruebas conectadas. |
| `evidence: local_source` | La intención/campos proceden del demostrador o especificación local, no aprobación de cada restricción añadida. |
| `evidence: local_proposal` | Forma sintética propuesta para transporte; no contrato real descubierto. |

**En ambos tipos de evidencia**, `DEMO-` y los controles/referencias añadidos, límites de listas/textos no derivados de fuente, las formas de eventos/webhooks y las propuestas de identidad/proveedor/core son propuestas LOCAL. No se han aprobado claves/columnas SIIE, catálogo académico, política de roles/2FA, proveedor, licensing, scoring, grants o ventanas de contacto.

## Qué se valida

- Cuerpos estrictos con campos requeridos significativos, tipos, textos/listas acotados, enums/discriminantes, elementos duplicados y valores vacíos. Los parches admiten solo modificaciones explícitas no vacías y rechazan `null` explícito; omitir campos no equivale a borrarlos.
- `idempotencyReference` sintética y `expectedRevision` entero no negativo cuando hay estado versionado. Activación vincula estructuralmente `testedRevision` con la revisión propuesta; registro core vincula `applicationRevision`. Esto **no comprueba** pruebas, autorización, idempotencia, estado actual ni concurrencia real.
- Query/path tipados, referencias path opacas con sintaxis anterior y channel de cinco valores. Estas referencias no son claves DB/SIIE aprobadas. Paginación `limit` 1–100 y `offset` 0–10000: límites/defaults de transporte, no política de negocio. Filtros adicionales se nombran por capacidad; fuente local o propuesta según la tabla.
- Query desconocida o repetida rechazada sin reflexión. GET/DELETE no tienen cuerpo documentado ni aceptan un cuerpo anunciado por Content-Length/Transfer-Encoding. No hay interpretación de challenges, códigos OAuth o firmas de proveedor.
- 422 contiene solamente `code: invalid_local_contract_input` y `mode: local_demo`, constantes. Nunca se publica valor, campo, ubicación, `errors()`, excepción o payload. Una entrada válida devuelve exclusivamente el 501 constante del catálogo; ninguna intención se aplica.

Los fixtures de lectura conservan campos relevantes del demostrador: Cliente (mapa **tipado** de valores personalizados, no `Any`), hilo relacionado por `clientId`, mensajes/tareas/workflow/timeline, Comentarios Facebook/Instagram/TikTok, ocho tipos CRM, estados de enlace y cinco estados de revisión. El `type` de Cliente sigue libre: no se incorpora el enum financiero de la referencia. En Perfil, `profileName`/`position`/`timezone` proceden del demo; email/foto/identidad/verificación son referencias sintéticas propuestas por el alcance de Ajustes, no nuevos datos autenticados.

## Capacidades y límites específicos

| Familia | Forma definida y límite |
|---|---|
| Identidad/usuarios/perfil/seguridad | Intenciones y referencias de identidad/política/revisión/evidencia; sin passwords/PIN/OTP/tokens, cookies, 2FA configurada o algoritmo de grants. |
| Overview/clientes/CRM | Conteos pueden ser `null`: falta de dato no significa cero. Configuración/lecturas locales; desactivación es solicitud revisada. |
| Conversaciones/comentarios | Lecturas y control/read/sugerencia/análisis/reacción propuestos; análisis determinista local, no inferencia IA o envío/publicación. |
| Catálogo/formulario/revisión | Referencias/display/disponibilidad; no columnas SQL, precio o horario exacto inventado. Enlace sin URL/token; revisada no significa aprobada/matriculada; core registration 501. |
| IA/canales/proveedores | Revisión/prueba/publicación separadas y referencias de capability/credencial/versión/evidencia. Cinco perfiles conservan las 19 etiquetas ficticias; ningún grant, conexión o calidad se considera probado. |
| Webhooks | Unión discriminada **LOCAL sintética** message/delivery/reference, con channel coherente con path. No payload Meta/TikTok ni firma real. GET nunca refleja challenge, POST nunca ACK. |
| Diagnóstico | Cuatro escenarios y tres checks de fuente, referencias saneadas, disponibilidad pendiente; no métricas/colas/telemetría o recovery ejecutados. |
| Media/seguimientos/knowledge | Metadata y referencias de texto/modelo/política; sin bytes/archivos/URLs/fetch, jobs, STT/TTS, índices, retrieval real o scoring. Fuentes/citas/evaluación/publicación planeadas. |
| Retención/corporativo/creadores | 38 rutas condicionales preservadas: contacto/relación/organización y entidades separadas de creador/campaña/recurso/audit. Derechos requieren referencias a contrato/revisión/periodo; no licencia de seis meses, email o anuncio Spark. |

## OpenAPI y generación

`local_openapi.py` extiende la salida/cache de FastAPI, sin rutas temporales de éxito. `model_json_schema(ref_template=...)` produce referencias `#/components/schemas/…` pero deja definiciones anidadas en `$defs`; el helper las mueve a componentes y detecta colisiones. Conserva la serialización `exclude_none` de `get_openapi`, sin sobrescribir schemas heredados. Pruebas comprueban referencias, ausencia de huérfanos, caché y app nueva.

Dependencias originales conservadas: FastAPI 0.143.0 y Pydantic 2.14.1. Fuentes primarias revisadas mediante Context7 y contrastadas con la instalación: [extensión OpenAPI FastAPI](https://fastapi.tiangolo.com/how-to/extending-openapi/), [caché OpenAPI](https://fastapi.tiangolo.com/reference/fastapi/), [refs Pydantic](https://docs.pydantic.dev/latest/concepts/json_schema/), [validación JSON estricta](https://docs.pydantic.dev/latest/concepts/json/) y [uniones discriminadas](https://docs.pydantic.dev/latest/concepts/unions/). No librerías nuevas ni cambio de stack.

Desde `backend`, exportar con `.venv\Scripts\python.exe tools\export_contracts.py`; `--check` solo compara. Normalizar/exportar **antes** de las comprobaciones finales; generar después cambia la evidencia. Los ejemplos usan serialización de campos explícitos para no reintroducir `null` en parches dispersos.

## Reversión y siguiente puerta

La reversión restaura únicamente archivos responsables de A-025 y sus exportaciones desde el respaldo ignorado, retira los nuevos archivos de esta unidad y vuelve a comprobar inventario/hashes. No reset global ni modificación de fases previas. Consumidores locales de los 77 cuerpos nuevos deben pasar de `{}` a los ejemplos canónicos; los 13 cuerpos heredados siguen aceptando `{}`. No cambio ni migración de API productiva.

Tras la comprobación independiente LOCAL, las aprobaciones/contratos conectados permanecen abiertos. **Fase 1 requiere autorización propia** antes de personas/datos reales, integración/proveedores, exposición o entorno compartido. Esta unidad no la inicia ni publica Git/despliega.
