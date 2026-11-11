> **Estado vigente LOCAL-v2:** 135 operaciones definidas localmente, 13 cuerpos heredados provisionales; cero esquemas pendientes LOCAL y 148 aprobaciones conectadas pendientes. [Guía actual](local-schema-guide.md), [cobertura](local-schema-coverage.md) y [ejemplos](local-schema-catalog.json). Los conteos de 135 pendientes en el texto siguiente describen el snapshot A-024, no el estado actual.

# Contratos de transporte LOCAL: qué existe y qué falta

**151 operaciones método/ruta:** 148 stubs de negocio siempre 501 para entradas declaradas válidas, dos health (200/503) y un catálogo 200 de metadata. No hay autenticación, lectura/escritura SIIE, proveedor, envío, ACK de webhook ni éxito simulado. [Cobertura generada](local-endpoint-coverage.md), [OpenAPI generado](local-openapi.json), [informe A-024](../reports/local-endpoint-contracts.md).

## Fuente única y comprobación

`backend/app/contracts.py` posee método, ruta, operación única, fuente, capacidad, fase, estado de esquema, disposición, puerta y respuesta. FastAPI registra desde ese catálogo con firmas explícitas tipadas; OpenAPI describe los mismos parámetros/cuerpos y solo 501/422 en negocio. Las rutas concretas preceden las paramétricas. El frontend importa metadata generada, no consulta backend.

```powershell
Set-Location 'C:\Users\Developer_PC\.codex\worktrees\8520\CRM_CBN'
backend\.venv\Scripts\python.exe backend\tools\export_contracts.py --check
# Si cambia el catálogo: exportar SIN --check antes de normalizar/verificar.
```

JSON se compara estructuralmente para admitir el formato de Prettier sin mantener inventarios escritos por duplicado. Markdown se compara íntegro. La tabla/catálogo/OpenAPI son artefactos generados, no un API independiente.

## Estados de certeza

| Estado | Significado y siguiente puerta |
|---|---|
| `provisional` | Campos del demostrador local tipados; opcionales porque no se decidió contrato conectado/creación/patch. No validación académica ni identidad SIIE. |
| `pending` | Esquema de negocio/proveedor desconocido; mutación acepta exclusivamente objeto vacío `{}`. No pedir contraseña, OTP, token, PIN o URL para fingir un contrato completo. |
| `local_stub_only` | Vocabulario de transporte del corte base; no negocio implementado. |
| `conditional_proposal` | 38 rutas de 7A–7F incluidas para cobertura/discovery; no nueva expansión implementada ni comprometida. |

Los cuerpos fuente son ficha Cliente local (tipo libre, sin enum financiero), configuración CRM (etapas/probabilidad 0–100, etiquetas y ocho tipos de campos), texto de mensaje, workflow/tarea local, cinco campos provisionales del formulario, decisión humana (revisada no aprobada/matriculada), IA/perfil locales y etiquetas ficticias Canales. Los IDs path son referencias opacas de transporte, **no claves core aprobadas**. La demo relaciona hilo por `clientId`; `conversation_id` futuro no implica ID de conversación/DB descubierto.

Listas usan límites provisionales `limit` 1–100 y `offset` 0–10000; no política/paginación de negocio aceptada. Los errores 422 devuelven solo `code` y `mode` constantes, sin `errors()`, valor, campo desconocido, query, payload, excepción ni localización reflejados. Los stubs 501 contienen solo operación/estado/puerta constantes del catálogo. No hay cookies, tokens, redirecciones o respuestas 200/201/202 de negocio.

## Antes de conectar

Fase 1 requiere identidad/roles/sesiones/2FA/auditoría/secretos/entornos, contrato SQL/SIIE y privacidad; cada capacidad requiere contratos/permisos/versionado/concurrencia/idempotencia/rollback probados en ambiente autorizado. Core registration permanece 501. Auth/recovery/2FA/roles no implementan políticas ni credenciales por la existencia de una ruta. Catálogo académico y horarios no contienen nombres de columnas SIIE inventados. Diagnóstico backend no es la telemetría ni los fixtures operativos de fase 6 frontend.

Voz/media/fallback/recordatorios/RAG/memoria/retención/corporativo/creadores quedan pendientes. Contact-plan no envía correo; URL de recurso no carga archivos; revisión de derechos no concede licencia; Spark-preflight no publica anuncio. Visión/búsqueda/inteligencia/fusión requieren discovery; pagos/proveedor de referencia/Industria/Plan están excluidos. Conflictos de tipo/pago de referencias siguen en P-027. No se agregan CRUD arbitrarios.

## Seguridad local: límite de evidencia

Solo `local_demo`, loopback, sin CORS nuevo, sin DB/network clients/SDK/driver, sin secretos ni carga automática de entorno. Es aislamiento verificable de esta unidad, **no seguridad productiva aprobada**. El callback/webhook de proveedor exige HTTPS público autorizado y contrato exacto; localhost no es validación de proveedor. GET webhook no eco de challenge; POST no ACK de éxito. Tamaño global de body, rate limits, firma/replay, TLS expuesto y permiso servidor siguen pendientes de fase 1/contrato conectado, antes de exposición real.

Frameworks del lockfile existente conservados: [FastAPI](https://fastapi.tiangolo.com/reference/fastapi/), [errores FastAPI](https://fastapi.tiangolo.com/tutorial/handling-errors/) y [Pydantic ConfigDict](https://docs.pydantic.dev/latest/api/config/). Referencias primarias revisadas 2026-10-14; sin agregar/actualizar dependencias; instalación local del lockfile existente.
