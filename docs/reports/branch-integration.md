# Integración de ramas comprobada localmente

**Fecha:** 2026-10-14, America/Bogota. **Rama de trabajo:** `codex/integracion-coolify`. Se consolidaron las fuentes existentes sin commits, push, despliegue, conexiones SQL/proveedor ni cambios en las otras carpetas. **Resultado:** 1488 pruebas backend y 195 frontend aprobadas, además de formato, lint, tipos, exportación canónica y build. La aceptación de navegador de este conjunto corresponde a la siguiente comprobación del coordinador.

## Fuentes y conservación

| Fuente | Responsabilidad preservada | Archivos respaldados |
|---|---|---:|
| `E:\Nuevos_Proyectos\CRM_CBN`, antes de editar | V6, tokens, gráficos, borradores y movimiento; anterior rama `codex/disenos-ui` | 170 |
| `C:\Users\Developer_PC\.codex\worktrees\117d\CRM_CBN`, `codex/proveedores-ia` | IA, credenciales, conversación, voz/media/búsqueda | 162 |
| `C:\Users\Developer_PC\.codex\worktrees\8520\CRM_CBN`, `feat/phase-4-local` | Formulario, revisión, operación, Canales y contratos locales | 192 |
| `C:\Users\Developer_PC\.codex\worktrees\f615\CRM_CBN`, `feat/sqlserver-python-api` | Cuatro catálogos SQL de solo lectura y sus propuestas | 150 |

Las cuatro ramas partían del mismo HEAD `14d818a123118914990dc8951738ae3b8bf38bd7`; sus funcionalidades estaban sin commit. Por eso una fusión de referencias Git no incorporaba esos avances. Se compararon contenidos normalizando CRLF/LF y usando las bases reales de separación:

- Diseño/IA: `.local/ai-chat-isolation-20261014/working-files/`.
- Diseño/fase 4/SQL: `.local/worktree-separation-20261014/candidates/` y sus manifiestos de propiedad; HEAD solo cuando el archivo no tenía una versión de separación.

Antes de editar se copiaron y verificaron **674/674 archivos fuente** en `E:\Nuevos_Proyectos\CRM_CBN\.local\integration-20261014\sources\`. `source-manifest.json` registra origen, rama, HEAD y SHA-256. Se excluyeron `.local`, secretos/archivos `.env`, dependencias, cachés y `.atl`. No se leyeron ni copiaron claves, configuración IA operativa, cuentas SQL, PIDs o logs de las carpetas originales.

La comprobación final `source-preservation.json` confirmó **162/162 IA, 192/192 fase 4 y 150/150 SQL exactos**, sin altas o bajas en sus listas fuente; las cuatro copias de respaldo permanecen intactas. `integration-source-freeze.json` identifica **114 archivos de código/configuración/pruebas** integrados. Estos manifiestos y logs son locales ignorados.

## Conflictos resueltos

- El shell conserva V6 y sus propietarios de estado. Integra los flujos 4–6, el chat IA y Conocimiento sin sustituir Clientes/Inbox ni sus borradores. Los paneles de alcance conectado continúan visibles junto a los demostradores correspondientes.
- Ajustes combina presentación V6, referencias de Canales, diagnóstico operativo y las funciones IA actuales. Los ajustes/modelos/voz pendientes permanecen en `WorkspaceSession`; los campos de claves siguen siendo transitorios y se limpian al salir de APIs.
- Estilos, dependencias y pruebas exclusivas se incorporaron por responsabilidad. Los puertos locales unificados son Vite 5173 y backend 8000; la guardia IA también conserva los puertos aislados anteriores 5175/8002 y preview 4173. No se amplió a hosts remotos.
- Existe **una sola** ruta `GET /api/v1/catalog/programs`, perteneciente al adaptador de lectura. El inventario publica 147 stubs + cuatro catálogos optativos + tres rutas health/metadata = **154 operaciones**. El banco IA conserva su namespace independiente `/api/ai`.
- Las **148 propuestas** y sus 135 definiciones locales permanecen en el registro de planificación. La propuesta de programas se conserva en `superseded_proposals` y en la extensión OpenAPI `x-local-superseded-proposals`; no oculta el DTO real ni anuncia una respuesta 501 para su ruta operativa.
- El handler 422 devuelve el envelope IA o el de contrato local según la ruta; ninguno refleja valores recibidos. Los catálogos deshabilitados continúan devolviendo 503 antes de SQL.
- Los dos documentos ADR-005 conservan títulos y nombres completos distintos: `ADR-005-tailwind-appearance.md` y `ADR-005-local-period-catalog.md`. Los IDs A/P de informes paralelos también requieren su contexto de origen.

## Comprobaciones ejecutadas

| Capa | Resultado nuevo |
|---|---|
| Backend | `python -m pip check`, `python -m ruff format --check app tests tools` y `python -m ruff check app tests tools`: aprobados. Única dependencia añadida a la venv: `pyodbc==5.3.0`, ya fijada por la rama SQL. |
| Exportación | `python tools/export_contracts.py` antes de verificar; `python tools/export_contracts.py --check` aprobado. OpenAPI, metadata frontend y documentación generada coherentes. |
| Pruebas backend | `python -m pytest -q --basetemp='../.local/integration-20261014/pytest-final'`: **1488 aprobadas en 152,55 s**. TestClient ejecutado con socketpair/loopback permitido en Windows. |
| Frontend | `npm run format` antes del pase; `npm run check`: formato, ESLint, TypeScript, **195 pruebas en 21 archivos** y build Vite aprobados. Vitest con `maxWorkers: 2`, sin aumentar timeouts. |
| Integridad | `git diff --check` salida 0; cero marcadores de conflicto en código/docs; fuentes originales y backups comprobados por SHA-256. |

`backend/tests/conftest.py` retira configuración/credenciales heredadas del proceso antes de collection, bloquea conexión SQL/red real y lectura de los archivos IA del operador. Las fixtures temporales se permiten únicamente dentro del directorio de pruebas; los tests de proveedores y SQL usan transports/adaptadores simulados. No se reutilizan las aceptaciones históricas como prueba nueva de conectividad real.

Logs locales: `backend-focused.log`, `backend-tests.log`, `frontend-tests.log`, `frontend-check.log` y `frontend-check-final.log` bajo `.local/integration-20261014/`.

### Incidencias conservadas

1. TypeScript detectó un import de tipo IA omitido al resolver el conflicto; se restituyó antes de la suite. `pyodbc` faltaba en la venv de diseño; se instaló la versión del lockfile. Ruff normalizó imports/formato antes de la comprobación final.
2. Primer pase backend enfocado: **33 fallos, 225 aprobadas y 19 errores**. La nueva protección de estado rechazaba también los temporales sintéticos situados dentro de `.local`; se restringió la excepción al `basetemp` propio. Otro test no recorría los routers incluidos de FastAPI y contaba cero rutas SQL; se corrigió la inspección de unicidad. Ninguna clave o conexión real se habilitó para resolverlo.
3. Primer pase frontend: **6 fallos y 189 aprobadas**. Se restauró un panel de alcance conectado omitido al ensamblar App. Se actualizaron las expectativas del banner y del inventario integrado; los controles de ausencia de IO de Canales/Operación ahora permiten exclusivamente la lectura `GET /api/ai/settings` que ya forma parte del módulo IA, conservando el rechazo de cualquier otra llamada.
4. Siguiente pase con paralelismo automático: **193 aprobadas y dos fallos**; el primer caso de fase 2 agotó 5000 ms y afectó al siguiente. Concurrencia limitada a dos workers, conservando los mismos casos y timeout: el `npm run check` final pasó íntegramente. No se presentan los intentos previos como aprobados.

## Reversión y siguiente unidad

Para revisar o revertir un archivo concreto, contrastar su ruta y hash con `source-manifest.json` y recuperar la versión del origen correspondiente en `sources/`. La carpeta `sources/design` conserva el estado del checkout inmediatamente anterior a integrar; los originales de las otras ramas permanecen disponibles. Retirar únicamente archivos añadidos por esta unidad usando `merge-events.json` y el diff revisado. No usar `reset --hard`, borrar worktrees o sustituir `.local` del operador como parte implícita de esta reversión.

La siguiente unidad es el empaquetado Docker para revisión privada y su verificación en contenedor/navegador. No se crea un contenedor SQL: SIIE continúa externo. El SQL actual está fijado a `localhost\SQLEXPRESS`/`DBSIIE` y se verificó históricamente por memoria compartida; TCP, conectividad privada desde Oracle y confianza TLS necesitan su propio trabajo autorizado. DPAPI es exclusivo de Windows, y la guardia loopback no sirve como autenticación empresarial detrás de un dominio público.

No se probaron Docker, Oracle, SQL remoto, proveedores reales, canales, teléfono físico ni acceso compartido en esta unidad. Fase 1, privacidad, operaciones conectadas y exposición conservan sus puertas. RDD estaba deshabilitado; no se ejecutó revisión nativa ni se declara una aprobación de ese tipo.
