# Contratos y stubs de endpoints exclusivamente locales — A-024

**Autorización vigente:** construir contratos/stubs de TODOS los endpoints locales y ampliar Ajustes → Canales con referencias API de Facebook, Messenger, Instagram, WhatsApp y TikTok. Sin DB, API real, identidad, envío, proveedor, despliegue o Git. Fase 1 sigue después y es obligatoria antes de activación o exposición real. Unidad delegada directa, no SDD. Fecha: 2026-10-14, America/Bogota.

## Checklist autorizado antes de implementar

- [x] Congelar inventario finito con fuente, fase, esquema provisional/pendiente, puerta y disposición de exclusiones.
- [x] Registrar rutas tipadas desde una única fuente; negocio válido devuelve 501; errores declarados 422 constantes sin reflejar entrada.
- [x] Preservar `/health/live` 200, `/health/ready` 503 y modo exclusivo `local_demo`; catálogo solo metadata 200.
- [x] Canales: cinco perfiles, referencias ficticias sin secretos, borrador/guardar/descartar aislados; acciones reales deshabilitadas.
- [x] Pruebas primero, normalización y checks; congelación/hashes y reversión acotada.
- [x] HTTP independiente y navegador por coordinador, corrección accesible revalidada y readback posterior; no derivar esa prueba de tests/build.

## Límite del contrato

Inventario de transporte local, no contrato final SIIE ni API de proveedor. Identidades, roles, claves core, concurrencia, catálogo académico, políticas y esquemas desconocidos requieren fase 1/discovery y autorización antes de activarse. Los cuerpos pendientes solo aceptan `{}`; no reciben credenciales. Condicionales de fase 7 permanecen propuestos, no implementados como negocio.

## Estado

**A-024/P-037 completados al 100% exclusivamente como inventario/stubs LOCAL y referencias de Canales.** Código/checks/HTTP propio e independiente, navegador y corrección accesible revalidados por coordinador; readback final 67/67. **No 100% de esquemas/contratos conectados:** 13 cuerpos provisionales y 135 operaciones con esquema pendiente; sin activación real. Fases previas conservan sus snapshots/evidencia histórica; esta unidad no repite su aceptación ni modifica sus informes.

## Entrega y límites

| Entrega | Evidencia |
|---|---|
| Inventario único | `backend/app/contracts.py`: 151 operaciones método/ruta = 148 negocio 501 + 2 health 200/503 + catálogo metadata 200. 38 rutas fase 7 son condicionales; 110 pertenecen al vocabulario base. |
| Cuerpos y validación | `backend/app/schemas.py`: 13 operaciones con cuerpo provisional de fuente local, 135 pendientes. PendingRequest vacío, extra forbid; channel path enum de cinco valores; otros path obligatorios tipados y query de listas acotadas. No claves/políticas core inventadas. |
| OpenAPI coherente | Firmas explícitas generadas desde catálogo comprobadas contra OpenAPI; solo 501/422 en negocio, sin falsa respuesta exitosa. Rutas estáticas registradas antes de paramétricas. `tools/export_contracts.py --check` compara metadata UI/OpenAPI JSON estructuralmente y Markdown íntegro. |
| Canales | Cinco perfiles inspector, 19 posibles etiquetas ficticias según producto; estado no conectado/no verificado, recursos/grants/login/version/evidencia pendientes. Facebook Pages y Messenger DM separados; Instagram/TikTok producto aún pendiente. Tupla de cuatro transportes Inbox intacta. |
| Estado local | App conserva solo referencias guardadas por perfil al navegar. Cambiar perfil/sección/ruta descarta lo pendiente; guardar/descartar por separado. Recarga y reset confirmado eliminan todo; cancelar reset conserva. Sin fetch/storage de negocio. |
| Referencias externas | Fuentes primarias con fecha/límites en [Canales](../contracts/channel-references.md); Graph Pages/posts/webhooks exactos no accesibles 429 y pendientes. Sin Graph version/cuotas/SLA/permisos concedidos ficticios. |

### Evidencia de pruebas primero y checks

- Backend RED: importación de `app.contracts` todavía inexistente. GREEN inicial 162 pruebas; final ampliado: **315 tests en 54.84 s**, incluidos los siete health históricos. `backend/.venv/Scripts/python.exe -m pip check`: sin dependencias rotas; `ruff format --check app tests tools` y `ruff check app tests tools`: aprobados, nueve archivos. Lockfile/paquetes existentes conservados.
- Frontend RED: módulo `shared/channels` todavía inexistente. GREEN enfocado siete tests. Check inicial detectó una regresión real de los encabezados/indicadores de los cuatro canales históricos; se conservaron sin modificar la prueba previa. Check previo a la corrección **136 tests/13 archivos**, formato/lint/tipos/build aprobados mediante `npm run check`; son 129 históricos + siete nuevos. No modificar manifests/dependencias/tokens/CSS para resolverlo.
- Normalización acotada Ruff/Prettier y generación antes del freeze; export `--check` aprobado. Detector Impeccable previo a la corrección `[]` después de restaurar filas/heading históricas; no se presenta como inspección visual ni como nueva ejecución sobre la corrección semántica.
- Entorno Python 3.12.14 bundled verificado; `.venv` propia. Primer ensurepip bloqueado bajo sandbox, resuelto con escalación estándar e instalación del lockfile sin cambios. TestClient sandbox interrumpido por socketpair Windows; ejecución loopback autorizada aprobó los checks. Un intento npm desde raíz sin package.json falló por cwd y se corrigió al `frontend`; un npx `--no-install` desde raíz se canceló sin instalar paquetes. Estos intentos no prueban fallos de negocio ni se ocultan como pruebas aprobadas.
- Logs/comprobaciones/backups ignorados: `.local/endpoint-contracts/frontend-check.log`, `backend-check.log`, `http-check.json`, `baseline.json`, `backup/`, `protected-readback.json`, `final-source-hashes.json`, `runtime.json`. No secretos/datos personales.

### Freeze y HTTP propio del ejecutor

- Freeze **67 archivos source/config/export**, rutas relativas y SHA-256: `.local/endpoint-contracts/final-source-hashes.json`; SHA-256 del manifiesto final corregido `c10197f41a207cb69abfe8efee4d7c1c38282f3278f473ca043229292299c0fc`. No source editado después del freeze final corregido. El freeze anterior se conserva en `pre-correction-source-hashes.json` con SHA-256 `b9bcd17ab4e732b744fcd53dcd930873089c53f8dfe4b3640d9151a45b08a386`.
- Baseline propia: 56 archivos antes de la unidad. Solo fuentes existentes responsables `frontend/src/App.tsx`, `frontend/src/features/Settings.tsx`, `backend/app/main.py` cambiaron, además de README/progress/pending/roadmap autorizados. Dominios/styles/tests previos/manifests/health/config originales intactos.
- Protección histórica fase 6: **18/19 intactos**; único cambio `backend/app/main.py` expresamente responsable de registrar stubs. No fingir 19/19: las 18 fuentes restantes conservan hash. La lista anterior incluía backend antes limitado a health.
- Helper nuevo Uvicorn oculto `http://127.0.0.1:8765`, listener PID **8152**, launcher **35548**; relación parent/proceso/cwd/binding comprobada, metadata en `runtime.json`. Flags `--host 127.0.0.1 --port 8765 --no-proxy-headers --no-access-log`. No detener servidor ajeno 8000 ni Vite existente 5174.
- HTTP propio por loopback: **151 rutas declaradas + cuatro casos inválidos 422**; status exacto, sin Cookie/Location, `/health/live` 200, `/health/ready` 503, metadata 200, negocio 501; OpenAPI igual al snapshot generado; **67/67 hashes intactos**. No DB/API externa. Esta evidencia no sustituye HTTP independiente/navegador del coordinador.

## Corrección acotada de accesibilidad tras navegador

Hallazgo comprobado por coordinador: un campo con etiqueta ficticia inválida mostraba el aviso general, pero no `aria-invalid`/`aria-describedby` ni foco en el primer campo inválido. Causa: `ChannelSettings` guardaba solo un error general y no pasaba el contrato `error` del componente `Field` compartido. No es fallo de backend ni de verificación HTTP.

Única corrección: `frontend/src/features/ChannelSettings.tsx` identifica campos mediante el validador local existente, reutiliza `Field.error` (ID de error y descripción constantes sin entrada reflejada) y enfoca el primero inválido según orden visible. Editar/descartar/cambiar perfil limpia aviso e indicadores; sección/ruta/reset confirmado los descartan por desmontaje. Sin CSS, dependencias, cambio de validators/DTOs/catálogo o backend.

Regresión primero en `frontend/src/test/channels.test.tsx`: RED mostró `aria-invalid=false` y foco retenido por Guardar; GREEN comprueba dos campos inválidos, asociación a mensajes saneados, primer foco y luego segundo, limpieza al editar/descartar/perfil/sección/ruta/reset. Scoped Prettier antes de `npm run check`: **137 tests/13 archivos**, formato/lint/tipos/build aprobados. Logs `correction-red.log`, `correction-green.log`, `frontend-correction-check.log`.

Freeze final de 67 archivos y readback **67/67**; `correction-source-delta.json` muestra exclusivamente componente y prueba nuevos. Backend/schemas/catálogo/OpenAPI/lockfiles/protegidos no cambiaron; suites backend/HTTP no repetidas porque su evidencia sigue vinculada a bytes intactos. Revalidación de navegador por coordinador aprobada y P-037 cerrado **al 100% exclusivamente como inventario/stubs LOCAL y referencias Canales**, no contratos/esquemas conectados.

HTTP independiente del coordinador aprobado: **765 probes / 690 checks / 606 respuestas 422 saneadas**, sin fallos; `.local/endpoint-contracts/independent-http.json`, SHA-256 `16407cf4ebf6751eaad1ac80191fd0356c81e3bdde1d0735267f925d7bbfcf0d` leído/verificado por ejecutor. Navegador inicial comprobó cinco perfiles, draft/guardar/descartar/perfil/sección/ruta/reset cancelar-confirmar/recarga/móvil sin overflow/acciones deshabilitadas/APIs151 y smoke de fases 3–6; el coordinador revalidó exclusivamente la aceptación afectada por la corrección, aprobada.

## Reversión acotada

No commit/reset global ni borrado de trabajo previo. Verificar primero identidad actual del helper/listener antes de detener solo PID propio. Restaurar desde `.local/endpoint-contracts/backup/` únicamente App/Settings/main y README/progress/pending/roadmap afectados por esta unidad. Quitar exclusivamente nuevas fuentes `backend/app/contracts.py`, `schemas.py`, `tests/test_contracts.py`, `tools/export_contracts.py`, `frontend/src/features/ChannelSettings.tsx`, `shared/channels.ts`, `shared/endpointCatalog.json`, `test/channels.test.tsx` y documentos `docs/contracts/`/este informe; no retirar archivos de otras fases ni su runtime. Resolver siempre paths absolutos dentro del worktree antes de cualquier limpieza. No hay datos/DDL/migraciones que revertir; `.venv` y logs son locales ignorados.

## Navegador corregido y evidencia nativa

Escritorio 1440×1024 y móvil emulado 390×844, claro/oscuro/teclado. Cinco perfiles separados con productos/pendientes, anchors oficiales inspeccionados sin abrir/conectar, metadata API151 y listado de endpoints propios 501; solo campos DEMO, sin password, acciones reales deshabilitadas. Facebook guardado aislado de Messenger; Messenger pendiente descartado por cambio de perfil; TikTok guardado preservado por sección/ruta, no pendientes. Cancelar reset conserva; confirmar reset y recarga eliminan referencias. Mini CRM/Inbox de cuatro transportes preservados y superficies de formulario/revisión/diagnóstico previas accesibles con límites core, sin repetir su aceptación histórica.

Corrección: dos campos desktop inválidos tuvieron `aria-invalid=true`, IDs `aria-describedby` resolvibles y mensajes constantes; foco en `channel-facebook-appReference`, edición limpia error/indicadores; nuevo submit enfoca `channel-facebook-assetReference`; descarte limpia. Móvil WhatsApp WABA inválida enfoca `channel-whatsapp-wabaReference` con descripción; corregir a etiqueta DEMO y guardar no afirma conexión. Tab navega perfiles/disclosure; no overflow en WhatsApp oscuro ni TikTok claro (ancho de documento 375 ≤ viewport 390), consola sin warnings/errores. Reset final comprobó campos vacíos, inválidos 0 y sin overflow; viewport restituido, entregable en 5174/settings y tab de usuario 5173 intacto.

| Captura nativa del coordinador | Dimensiones JPEG verificadas en header | Alcance |
|---|---|---|
| [Desktop completo](evidence/endpoint-contracts/desktop-channels.jpg) | 1425×2632 | Inspector/referencias LOCAL. |
| [Desktop viewport](evidence/endpoint-contracts/desktop-preview.jpg) | 1440×1024 | Viewport inspeccionado limpio. |
| [WhatsApp móvil oscuro](evidence/endpoint-contracts/mobile-dark-whatsapp.jpg) | 375×4219 | Captura completa móvil emulado. |
| [TikTok móvil claro](evidence/endpoint-contracts/mobile-light-tiktok.jpg) | 375×5066 | Productos pendientes/contratos 501. |

Archivos nativos existentes, sin recreación/edición. Capturas completas largas pueden mostrar costuras del sticky/skip-link; el viewport real inspeccionado no tuvo esos artefactos, no se atribuyen como bug de producto. Dimensiones/hashes en `.local/endpoint-contracts/capture-metadata.json`. No teléfono físico, proveedor real, producción ni aprobación visual humana definitiva.

## Siguiente paso tras el cierre local

HTTP independiente, navegador y revalidación acotada comprobados; cierre exclusivamente documental con evidencia saneada y hashes finales, sin nueva normalización ni suites reejecutadas. Fase 1 es el siguiente corte, **no implementado por esta unidad** y requiere autorización específica; refinar schemas/discovery antes de activar/exponer. No fase 7 implementada, piloto, aprobación visual humana, teléfono físico ni publicación Git.

Readback documental de cierre: **363 enlaces locales en 38 archivos Markdown, sin faltantes**; headers/hashes de los cuatro JPEG coinciden, fuente congelada 67/67 y baseline propio 49/56 sin cambios fuera de los siete autorizados. `git diff --check` aprobado, con advertencias históricas LF/CRLF sin normalización ni escritura Git. Evidencia ignorada actualizada en `.local/endpoint-contracts/closure-readback.json`; informes de fases previas conservados.

Engram estuvo bloqueado durante la implementación por host Codex no registrado. Posteriormente, el coordinador confirmó el registro autoritativo del host y los guardados 1439–1441 de checkpoint/entrega/corrección. Ese bloqueo histórico no sigue vigente para el cierre del coordinador; no se inventaron IDs ni se reutilizó su identidad como atribución de un agente hijo. No se modificó configuración global para cerrar esta documentación.
