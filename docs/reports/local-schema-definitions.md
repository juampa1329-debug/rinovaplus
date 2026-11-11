# Definiciones y validación de esquemas LOCAL — A-025 / P-038

**A-025/P-038 completados al 100% de las 135 definiciones y validaciones exclusivamente LOCAL**, con checks, HTTP independiente, navegador y readback comprobados. Los 13 cuerpos heredados siguen provisionales; los 148 contratos conectados permanecen `approval_pending`. No conexiones ni ejecución de negocio. Fase 1 continúa diferida y requiere autorización separada antes de personas/datos reales, proveedores, exposición o entorno compartido. A-024/P-037 permanece como snapshot histórico del inventario/stubs.

## Checklist previo a implementación

- [x] Reglas, alcance y últimos IDs A-024/P-037 comprobados; unidad nueva A-025/P-038.
- [x] Respaldo y hashes en `.local/local-schemas`, ignorados; inventario 151/148 y 13 cuerpos heredados congelados.
- [x] RED: prueba del registro ausente falla por `ModuleNotFoundError`; evidencia local `red.txt`.
- [x] Registro explícito de 148 contratos; 135 definidos localmente, 13 provisionales intactos.
- [x] 77 cuerpos nuevos significativos; 58 operaciones nuevas sin cuerpo; ejemplos sintéticos y resultados planeados tipados.
- [x] Validación positiva/negativa, respuestas 501/422 constantes y OpenAPI sin éxito ficticio de negocio.
- [x] Normalización seguida de backend/frontend y exportaciones; readback de archivos protegido en evidencia local.
- [x] HTTP propio del proceso nuevo en loopback; freeze de fuentes posterior a checks.
- [x] HTTP independiente y navegador del coordinador; cuatro capturas nativas, readback y cierre documental final.

## Límites

Las referencias, límites no derivados del demostrador y controles de revisión/idempotencia son propuestas LOCAL. No aprueban claves/columnas SIIE, auth/roles/2FA, producto de proveedor, licencia, scoring ni reglas académicas. No hay DB, SDK, almacenamiento de negocio, envíos, tokens, desafíos reflejados ni ACK.

## Entrega y comprobaciones técnicas

**Cierre al 100% de las 135 definiciones/validaciones LOCAL; no de contratos conectados ni ejecución real.** Inventario exacto: 151 operaciones, 148 negocio 501, 38 condicionales fase 7, 13 cuerpos heredados provisionales y 135 definidos LOCAL (57 GET, 69 POST, 5 PUT, 3 PATCH, un DELETE). Los 148 contratos conectados conservan `approval_pending`.

- Registro explícito: `local_registry.py`; 84 tipos de cuerpo distintos (10 heredados/74 nuevos), 142 resultados planeados, 13 query y 21 path: **260 modelos ligados**. Hay **261 ejemplos**: los 260 ligados y un fixture adicional de `OperationRecord`. No se exige una clase por operación.
- Fuentes `local_models.py`, `local_plans.py`, `local_samples.py`, `local_openapi.py`; catálogo frontend y OpenAPI/cobertura/ejemplos documentales generados por `tools/export_contracts.py`. UI cambia únicamente la etiqueta del estado de esquema en Canales, sin fetch o wiring.
- Backend: `pip check`, Ruff format/check sobre app/tests/tools, export `--check` y **1223 tests aprobados en 128,76 s** (315 previos conservados/adaptados a ejemplos requeridos + 908 nuevos). Windows TestClient requiere socketpair/loopback permitido; ejecución restringida interrumpida, no fallo de negocio.
- Frontend: `npm run check` aprobado: formato/lint/tipos, **139 tests/14 archivos** (137 previos + 2 regresiones metadata/UI), build Vite 8.3.4. Sin dependencias/config/CSS/Tailwind nuevos.
- HTTP propio: **456 probes**, 151 operaciones válidas, 148 negocio 501, 13 cuerpos heredados `{}` aún 501, **291 negativos 422 constantes**, cero fallos; OpenAPI vivo coincide con exportación actual. No equivale a comprobación independiente ni navegador. Evidencia `.local/local-schemas/http-probes.json`.
- Runtime backend propio nuevo 127.0.0.1:8765, PID 27396/launcher 14760, sin autoreload/proxy headers/access log; PIDs históricos 8152/35548 ya ausentes, no se detuvo ningún proceso ajeno. Verificar nuevamente identidad antes de cualquier parada; `.local/local-schemas/runtime.json` es evidencia, no autorización futura de PID.
- Después de checks/freeze se inició Vite propio, oculto y solo 127.0.0.1:5174 `--strictPort`, PID 9524/parent histórico 30288, Node 24.20.0 y entrypoint/carpeta de este worktree comprobados. El puerto estaba libre; no se tocó 5173/5175. Identidad en `.local/local-schemas/frontend-runtime.json`; el coordinador verificó nuevamente el proceso/listener real aunque el parent histórico ya no existía, sin detener procesos ajenos. Navegador comprobado en el cierre siguiente.
- Freeze **81 archivos**: identidad agregada de pares `path:sha256` **`7d17ce7a554651944eddc8d1a46aa4d5b6709434a6f08affa7a9a568c12d99e4`**, distinta del SHA-256 de los bytes del manifiesto `final-source-hashes.json`: **`833f7e26e05dbebb53f303b09b653bb8b5140359c24129a731bc46da0ab91f35`**. Readback posterior a runtime/verificación/navegador **81/81 intactos**. Línea base 70: 56 sin cambios y 14 deltas responsables autorizados; protegido histórico 18/19 intactos, excepción `main.py` por registro de OpenAPI autorizado. Config/health, lockfiles, modelo demo/Tailwind/fases previas intactos; detector de deltas no autorizados vacío.

Pruebas RED/GREEN detectaron serialización de parches: `model_dump` completo reintroducía `null` en campos omitidos; ejemplos ahora conservan `exclude_unset=True`. Validación de listas rechaza texto vacío/solo espacios. `Literal[True]` acepta `1` en Pydantic aun con strict: guard explícito y negativos exigen booleano real, sin presentar esto como consentimiento o autorización productiva.

La congelación incluye fuentes/backend/frontend/config/manifiestos/exportaciones/guías de contrato; excluye logs/caches/venv/node_modules/dist y documentos pasivos de cierre (README, avance, pendientes, roadmap, este informe), que el coordinador puede completar sin modificar bytes funcionales. Inventario/hashes base, 13 mappings y 10 hashes de modelos heredados, scope guard y freeze en `.local/local-schemas`, ignorado. Una mutación posterior de fuente invalida la prueba que dependía de esos bytes.

## Aceptación independiente del coordinador

**Resultado `passed`**, sin modificaciones de fuente, pruebas repetidas ni normalizadores posteriores. Evidencia `.local/local-schemas/independent-probe.json`, SHA-256 **`f9394722b2b1a68a185f87b861d091f2693e517d3f0f231f69cbc5878d564a6e`**; readback de cierre `.local/local-schemas/closure-readback.json`. El estado pendiente en las guías/checks congelados corresponde al handoff técnico previo al coordinador; **este informe y los documentos pasivos de cierre establecen el estado vigente**, sin alterar esas fuentes de evidencia histórica.

| Comprobación independiente | Resultado |
|---|---|
| Una ejecución HTTP real en loopback | **3226 solicitudes / 43,407 s**: 3057 respuestas 422 constantes, 164 respuestas 501 (148 canónicas + 13 cuerpos heredados vacíos + tres variantes webhook), tres 200 (health live, metadata y OpenAPI), health ready 503 esperado y una ruta desconocida 404. |
| DTOs y alcance semántico | 409 validaciones positivas y 2975 negativas de modelos; 23 familias y 18 proyecciones de forma fuente revisadas. 317 componentes / 993 referencias resolubles, sin huérfanos ni objetos genéricos no tipados. |
| Compatibilidad y preservación | 13 mappings / 10 hashes de modelos heredados intactos; 77 cuerpos nuevos rechazan `{}`, 58 operaciones nuevas no tienen cuerpo. 81/81 hashes intactos antes/después de verificación y reconciliación; 18/19 protegidos, excepción autorizada `main.py`. |
| Runtime propio | Backend 127.0.0.1:8765 PID 27396/launcher 14760; frontend 127.0.0.1:5174 PID 9524. Identidad/listener corroborados; ningún otro proceso o puerto modificado. |

**Reconciliación del verificador, no defectos de producto:** se preservaron cinco expectativas inicialmente incorrectas y se resolvieron fuera de línea, sin repetir solicitudes ni cambiar fuentes. Una confundía identidad agregada con digest literal del manifiesto. Cuatro suponían que todo POST debía entregar un plan con `humanReview`: STT, TTS, evaluación y retrieval de knowledge son resultados computacionales planeados, con `execution: planned_not_executed` y, en evaluación, `outcome: not_evaluated`; no ejecutan ni autorizan negocio. Los planes de `local_plans.py` sí conservan revisión humana requerida. Todas estas rutas siguen 501 y `approval_pending`; no se añade una regla global para todos los POST.

## Navegador y capturas nativas

Coordinador: escritorio **1440×1024**, móvil **emulado 390×844**, claro/oscuro y teclado. Cinco perfiles Canales: doce etiquetas `local_defined`/una provisional en el listado general, quince/una en WhatsApp; todas con «Conexión pendiente» y 501. OAuth/test/activación reales siguen deshabilitados. API conserva 151 operaciones; Inbox mantiene WhatsApp/Facebook/Instagram/TikTok y mini CRM determinista, no modelo IA.

Se comprobaron campo app inválido con error constante asociado, `aria-invalid`/`aria-describedby` y foco; corrección/guardado sintético `DEMO-SCHEMA-LOCAL` aislado de Messenger; diferencia de producto Instagram y permisos/conexión pendientes. En móvil TikTok: guardar `DEMO-TIKTOK-V2`, descartar pendientes y recuperar valores al cambiar ruta/sección; teclado a siguiente summary. Cancelar reset conserva, confirmar elimina y recargar limpia. Sin overflow: documento 1425 px en viewport 1440 y 375 px en viewport 390.

**Consola, sin ocultar historia:** la pestaña histórica conservó dos errores de reconexión WebSocket de Vite (`@vite/client`, 20:36:39 UTC), al recargar después de desaparecer/reiniciarse los servidores propios. No eran errores React ni de esquema. La pestaña nueva repitió ajustes/recarga/etiquetas y tuvo **cero warnings/errores**. Se cerró la pestaña de agente histórica y se conservó la pestaña del usuario. No se modificó HMR/config/CORS para ocultar el transporte; no se afirma consola histórica vacía ni aceptación HMR. Viewport restablecido al entregar.

Capturas JPEG nativas del coordinador, sintéticas y sin datos reales. Dimensiones verificadas en header, **distintas del viewport cuando corresponde**; capturas móviles largas pueden incluir elementos sticky/skip propios de captura completa, no evidencia de un defecto del layout del viewport. Escritorio inspeccionado visualmente por el coordinador; no aprobación estética humana definitiva.

| Captura | Dimensiones reales JPEG | SHA-256 |
|---|---|---|
| [Escritorio: etiquetas de contrato](evidence/local-schemas/desktop-contract-labels.jpg) | 1425×1013 | `2700314b651a939585e5365e2a46dd6fa85a66eb1c023cc1467227f7ad4bbb45` |
| [Móvil oscuro: contratos](evidence/local-schemas/mobile-dark-contracts.jpg) | 375×5121 | `c2e1070ce9b6876181030a89e7a330e0319de3b19841c2829e104f3622c2b3ab` |
| [Móvil claro: WhatsApp](evidence/local-schemas/mobile-light-whatsapp.jpg) | 375×5290 | `b84766b14ac115c50d313d06b8721e7c91d9f8b807f1eaa077260ca6c7b7b4f5` |
| [Escritorio actual: pestaña limpia tras restablecer viewport](evidence/local-schemas/desktop-current-labels.jpg) | 1265×712; no es captura 1440×1024 | `d6467abd39827eaf331406d3169d748159d7f3fdc4002d18b86c7776ebfa33d3` |

No teléfono físico, proveedor, auth/permisos, paridad integrada, escritura SIIE, matrícula, idempotencia o concurrencia real comprobados. Engram del host quedó registrado y el cierre guardado por los actores mediante su contexto automático; el bloqueo histórico de registro no es un bloqueo actual.

## Reversión

Restaurar solo los archivos responsables desde `.local/local-schemas/backups`, retirar los archivos nuevos de esta unidad y regenerar metadata con el exportador restaurado. Nunca usar reset global ni alterar fases anteriores. `local-v2` rechaza `{}` en los 77 cuerpos nuevos: los consumidores locales deben adoptar ejemplos válidos; los 13 cuerpos heredados conservan compatibilidad. No migración productiva ni cambio de API conectada.

## Siguiente paso

Unidad A-025/P-038 cerrada al 100% exclusivamente para las 135 definiciones/validaciones LOCAL. **Fase 1 sigue diferida y requiere autorización explícita propia** antes de cualquier seguridad/runtime conectado, exposición, personas/datos reales, proveedor o entorno compartido. Los contratos conectados/core/producto/identidad/permisos continúan pendientes; fase 7 no implementada. No conexión, Git ni despliegue automáticos.
