# Fase 0 — Skeleton y diseño funcional local

**Fecha:** 2026-10-13, America/Bogota. **Estado:** **fase 0 completada al 100% del alcance acordado de skeleton y diseño funcional LOCAL**: checks, salud HTTP y revisión de navegador aprobados. [ADR-002](../decisions/ADR-002-local-functional-skeleton.md) define ese alcance. No significa producto terminado, réplica completa Scentra, aprobación visual humana, integración DB/API o seguridad productiva. Fases 1–7 no iniciadas; tema e idioma siguen provisionales.


## Qué se hizo

- React/TypeScript ejecutable, doce rutas del mapa y referencia separada de Creadores. Navegación móvil, ruta desconocida y tema claro/oscuro provisionales.
- Clientes: búsqueda/filtro, selección, creación/edición, validación, cancelación y guardado temporal. Ficha y contexto compartidos con Inbox.
- Inbox: selección, filtros, borrador por hilo, lectura y control humano/IA de demostración; compositor añade texto únicamente al hilo local bajo control humano. No envío ni ejecución IA.
- Formulario público: campos de ejemplo, errores asociados, validación, confirmación explícitamente local y reinicio. No registro de aspirante/matrícula.
- Ajustes: IA, Canales, APIs, Diagnóstico, Usuarios, Perfil y Seguridad; borradores IA/Perfil temporales. Credenciales, conexiones, invitaciones, 2FA, exportación y baja bloqueadas con motivo visible.
- Resumen de fixtures y superficies de alcance para revisión académica, conocimiento, memoria, acceso, retención y corporativo. Creadores muestra sus siete pestañas como referencia condicionada, no capacidades implementadas.
- Backend independiente de salud: `/health/live` 200 y `/health/ready` 503 con SQL Server, Redis, identidad y proveedores `not_configured`. La UI no consulta el backend.
- Tokens/controles comunes, fixtures sintéticos, reset con confirmación, sin almacenamiento del navegador o llamadas de negocio. Dependencias fijadas y comandos documentados.

## Evidencia local

Comandos ejecutados desde sus carpetas después de normalización. Son resultados de esta máquina, no CI, dispositivo, seguridad productiva o pruebas externas.

| Comprobación | Resultado |
|---|---|
| Node/npm | Node 24.20.0, npm 11.19.0; runtime bundled alternativo 24.19.0 identificado, no modificado. |
| Python | 3.12.14; entorno exclusivamente `backend/.venv`. |
| Instalación npm | 232 paquetes; audit al instalar: 0 vulnerabilidades reportadas en ese momento. No garantía futura. |
| Formato frontend | `npm run format`, luego `npm run format:check`: aprobado. |
| Lint/tipos frontend | `npm run lint`, `npm run typecheck`: aprobados. |
| Pruebas frontend | `npm test`: **13/13 aprobadas**, 2 archivos. Vitest/jsdom, no navegador real. |
| Build frontend | `npm run build`: aprobado, 25 módulos; JS 259.06 kB / gzip 79.78 kB, CSS 16.58 kB / gzip 3.93 kB tras corrección acotada de navegación. |
| Entorno Python | `python -m pip check`: sin requisitos rotos. Lock exacto de dependencias directas/transitivas. |
| Formato/lint backend | `python -m ruff format --check app tests` y `python -m ruff check app tests`: aprobados. |
| Pruebas backend | `python -m pytest -q`: **7/7 aprobadas** tras reparación/limpieza del entorno; última ejecución 0.33 s. |
| Detector mecánico de diseño | `impeccable detect --json frontend/src`: `[]`, una ejecución. No sustituye revisión visual. |
| Arranque local | Vite en `127.0.0.1:5173`; Uvicorn en `127.0.0.1:8000`, logs de arranque correctos. HTTP y navegador comprobados en el cierre, con evidencia separada abajo. |

Las pruebas cubren contratos de reset, búsqueda/etapas, validación, mensajes solo en modo humano, navegación/recuperación, edición compartida, borradores, formulario, siete Ajustes, bloqueo de acciones reales, selector de tema y ausencia de `fetch` de negocio durante el escenario comprobado. Backend cubre liveness/readiness, modo no permitido y ausencia de API de Clientes.

## Checklist de cierre

- [x] Autorización local, ADR y alcance sin integraciones.
- [x] Tooling/versiones/locks y comandos locales reproducibles documentados.
- [x] Salud de proceso y readiness honesta comprobadas por TestClient.
- [x] Responsabilidades reales, sin dominio/adaptadores vacíos o SQL/LLM en rutas.
- [x] Navegación, componentes/tokens, fixtures y flujos locales comprobados por tests.
- [x] Formato/lint/tipos/pruebas/build después de normalización.
- [x] Navegador escritorio/móvil: flujos, navegación, ruta desconocida, tema, foco/teclado y ausencia de overflow comprobados con evidencia.
- [x] Informe final de fase registrado con evidencia de navegador y siguiente paso para entrega.

## Incidencias encontradas y resueltas

1. Consultas de registry en sandbox fallaron DNS `ENOTFOUND` / `getaddrinfo`; las descargas públicas funcionaron con escalación autorizada. Sin bypass TLS.
2. Primer install: TypeScript 7.0.2 incompatible con peer de typescript-eslint 8.71.2 (`>=4.8.4 <6.1.0`). Se eligió TypeScript 6.0.3 compatible verificado; sin `--force` o `--legacy-peer-deps`.
3. Tipos de tests rechazaron `exact` en `getByRole`; corregido. Un test encontró el mensaje tanto en preview como log; acotado al log. No se silenciaron checks.
4. TestClient en sandbox se bloqueó en `asyncio`/socketpair de loopback. Pruebas locales fuera del sandbox pasaron. Starlette 1.8.0 recomendó httpx2; se adoptó 2.13.1 y se retiró transporte anterior.
5. Desinstalación inicial sandbox dejó residuos `~ttpx` por WinError 5 al mover ejecutable a Temp. Se reparó/desinstaló dentro de `.venv` con Temp local, se verificaron y retiraron exclusivamente los dos residuos locales y se repitieron `pip check`/tests satisfactoriamente.

## Primera revisión de navegador y corrección acotada

El coordinador reportó desde CUA: flujos Clientes/Inbox/formulario/Ajustes, trece rutas, ruta desconocida y reset comprobados; sin overflow a 1440/390 px, sin errores/avisos de consola. Esto no es aceptación visual humana ni integración real.

Hallazgo único: el botón móvil aparecía en escritorio con contraste inadecuado. Causa comprobada en CSS: `.mobile-nav-toggle { display: none }` tenía igual especificidad que `.button { display: inline-flex }`, definida después; la cascada anulaba el ocultamiento. Se acotaron las reglas a `.sidebar .mobile-nav-toggle`, conservando la media query móvil y el estilo previsto del control dentro del sidebar. No cambió comportamiento/producto ni backend.

Después de la corrección: normalización, formato/lint/tipos, **13/13 tests** y build frontend nuevamente aprobados. Snapshot `.local/source-hashes.json` renovado: único source modificado `frontend/src/shared/styles.css`. Evidencia backend anterior reutilizable sin cambios. **Segunda/final confirmación CUA aprobada**: botón oculto en escritorio y visible/operable por teclado en móvil. Sin nuevas correcciones de source.

## Evidencia final y cierre del alcance local

| Capa comprobada | Evidencia / resultado |
|---|---|
| HTTP backend local | Peticiones controladas a `127.0.0.1:8000`: `/health/live` **200** con `alive/local_demo`; `/health/ready` **503** con `not_ready` y `sql_server`, `redis`, `identity`, `providers` **not_configured**. Solo loopback, sin llamada externa. |
| Fuente después de checks | Los **20 SHA256** de `.local/source-hashes.json` coinciden con source actual; ninguna mutación posterior a la corrección/verificación final. |
| CUA escritorio | 1440×1024: botón móvil `isVisible=false`; main x=240/ancho1200; documento scrollWidth1440, sin overflow horizontal. |
| CUA móvil emulado | Viewport solicitado/comprobado 390×844: botón visible; Enter abre/cierra navegación y actualiza `aria-expanded`; foco verde `rgb(128,214,174)` sólido3px; texto `rgb(240,245,241)`; scrollWidth375 ≤390. |
| Recorridos CUA | Trece rutas y encabezados, siete Ajustes, creación/edición/validación/búsqueda vacía Clientes, filtros/control humano/respuesta solo local Inbox, formulario inválido/válido, borrador IA local, ruta desconocida y reset5→4: aprobados. Consola sin errores ni avisos en la revisión. |
| Capturas actuales | Dos JPEG válidos, firma y decodificación comprobadas: escritorio **1440×1024**, móvil **375×812**. Son dimensiones de los archivos, no se confunden con el viewport solicitado. Desktop corresponde al estado corregido; la captura previa desactualizada no se usa como prueba. |

Capturas verificadas: [Inbox escritorio claro](evidence/phase-0/inbox-desktop-light.jpg) y [Inbox móvil oscuro](evidence/phase-0/inbox-mobile-dark.jpg).

SHA256 de imágenes: escritorio `8de53ad785f4c33933b64bfa5388a982a74f29a4166ff606bb03aff5b033f0f5`; móvil `494bc5c9b22cd72beb335e8d1e5f427a4305ee5fc1638a5106dde747fa6d40bd`.

**Límite de prueba:** Vitest/jsdom comprueba componentes/estado; CUA comprueba navegador desktop/móvil emulado y capturas. No se probó un teléfono físico, lector de pantalla completo, conformidad WCAG certificada, concurrencia distribuida, auth, SQL Server/Redis/Meta/IA o persistencia. No sustituye aprobación humana del diseño. Preview restablecido con fixtures iniciales para inspección del propietario.

## Herramientas y tradeoffs

| Elección | Razón y límite |
|---|---|
| React 19.3.0, TypeScript 6.0.3, Vite 8.3.4/plugin-react 6.1.2 | Stack React aceptado; build local simple, tipos y tooling compatibles comprobados. No framework full-stack adicional. |
| Hash routing nativo | Navegación/volver/enlace directo sin servicio de rutas o dependencia adicional; reemplazable si routing conectado lo necesita. |
| CSS semántico y controles React propios | Sin kit pesado, fuentes externas o iconos decorativos; una única fuente de tokens, estados y etiquetas. No certificación accesible. |
| Vitest 5.0.4/jsdom 30.1.2/Testing Library | Prueba de interacción/estado local; geometría, focus visible y comportamiento real siguen requiriendo navegador. |
| ESLint 10.12.0/typescript-eslint 8.71.2/Prettier 3.9.10 | Normalización y checks independientes; versiones exactas, sin mezclar formateadores. |
| FastAPI 0.143.0/Uvicorn 0.54.0, pytest 9.1.1/Ruff 0.17.0/httpx2 2.13.1 | Backend salud mínimo y tests; ninguna librería SQL, worker, driver, auth o proveedor instalada por anticipación. |

Documentación consultada: [Vite](https://vite.dev/guide/), [React](https://react.dev/learn/adding-interactivity), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/) y Context7 Vite; compatibilidad final probada en versiones fijadas. Registry/npm y metadatos pip usados para versiones, no para inferir aceptación productiva.

## Límites y reversión

No representa réplica funcional completa de Scentra. P-027 conserva contratos/diferencias pendientes; pagos, campos personalizados dinámicos, concurrencia, scoring, media, permisos y persistencia no se implementan en esta fase. Sin personas/datos reales, DB/API de negocio, credenciales, cuentas, Git/publicación, despliegue, llamadas IA, envío, workers, colas o cambios core.

Recargar o confirmar reset elimina cambios temporales; cada pestaña tiene fixtures propios. Tema provisional sin persistencia. La reversión técnica retira `frontend/`, `backend/`, archivos locales de runtime/configuración y nuevas instrucciones, preservando originales PNG/JSON, ADR e historial. No existe dato remoto/migración a revertir. Los PIDs/logs de revisión están en `.local/`, ignorado, y se detienen tras revisión o cuando el propietario deje de necesitar el preview.

## Qué prosigue

**Ahora:** el propietario revisa el diseño funcional en `http://127.0.0.1:5173/#/overview` y registra ajustes/aceptación visual de P-003/P-015/P-018 y paridad/contratos de P-027. El cierre técnico local no los acepta automáticamente.

**Después:** fase 1 — identidad, seguridad y contratos DB/API, con inventario saneado y autorizaciones específicas P-001/P-006/P-017/P-026 y partes restantes P-002/P-004/P-005. La integración permanece expresamente diferida y no iniciada; no conectar, consultar o crear objetos automáticamente. Git/publicación/despliegue requieren autorización aparte. Cada fase conservará el mismo cierre: qué se hizo, evidencia, límites y qué prosigue.
