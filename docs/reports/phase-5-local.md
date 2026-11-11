# Fase 5 — revisión humana funcional LOCAL

**2026-10-14, America/Bogota. Estado: completada al 100% del alcance LOCAL.** Código/checks, navegador escritorio/móvil emulado/temas/teclado y readback posterior comprobados; no integración ni aprobación visual humana final. Autorización explícita del propietario: «Continua fase 5 LOCAL y funcional 100%, sin DB/APIs, done/next report». Esta autorización acota el flujo demostrativo; no aprueba reglas académicas, catálogos institucionales, escritura core, Git o despliegue.

## Qué se hizo

`#/review` ahora contiene cola de tres fixtures independientes, búsqueda por texto/identificador y filtros de estado/programa. Lista y detalle reutilizan componentes, tokens, Tailwind y composición de Clientes. Se extiende el español neutral de preview, sin cambiar la aprobación visual pendiente.

- Cinco datos provisionales visibles: nombre/correo ficticios, programa/jornada del catálogo demo existente y confirmación de datos ficticios. Un fixture tiene correo ausente; se presenta como dato incompleto, no como una regla de elegibilidad.
- Estados **Pendiente → En revisión → Revisada / Observada / Rechazada**. Iniciar es explícito; el resultado requiere motivo de 5–600 caracteres, validación asociada/foco y confirmación distinta. Ese límite es de interacción local, no una regla académica.
- **Revisada no significa aprobada, elegible, matriculada o pagada.** Observar/rechazar no envía ninguna notificación. Registro SIIE permanece deshabilitado con su puerta P-011/fase 1 visible.
- Reabrir exige motivo y confirmación, retorna a Pendiente y conserva todas las entradas previas. No permite sobrescribir un resultado terminal sin reapertura. Historial append-only en memoria, con actor demo y hora real para las acciones; eventos de fixture sin fecha rotulados sintéticos. No auditoría durable.
- Razón/confirmación vinculadas al fixture y su versión local (longitud del historial/contexto). Cambiar selección/filtro/ruta invalida los borradores y confirmaciones; el motivo no pasa a otro caso. Un caso excluido por filtros no conserva detalle operable oculto.
- App conserva resultados/historial temporales al navegar. Reset confirmado y recarga descartan los cambios; cancelar reset los conserva. Solo la preferencia visual preexistente se persiste.
- **Fase 4 no alimenta la cola.** `ApplicationForm.tsx` y `shared/application.ts` permanecen exactos frente a baseline; confirmar allí no crea persona/solicitud/registro. La cola es deliberadamente independiente y rotulada, conforme al roadmap de fixtures.

## Aceptación local

| Criterio | Evidencia y estado |
|---|---|
| Autorización y límites de revisión humana sin integración | Registrados arriba; A-022/P-035. |
| Cola, búsqueda/filtros, vacío, detalle y dato incompleto | Pruebas de reglas/UI aprobadas. |
| Inicio explícito, resultados con motivo/validación y confirmación distinta | Pruebas de reglas/UI aprobadas; no aprobación automática. |
| Reapertura con motivo e historial preservado; rechazo de transición improcedente | Pruebas de reglas/UI aprobadas. |
| Invalidación de confirmación por selección/filtro/navegación y ausencia de fuga de motivos | Pruebas UI aprobadas. |
| Estado temporal al navegar, reset/cancelación y nuevo montaje | Pruebas UI y navegador aprobados: recarga real devuelve fixtures iniciales. |
| Sin fetch ni almacenamiento de negocio | Spies negativos y lectura del flujo; solo estado React. |
| Regresiones anteriores, formato/lint/tipos/build | Suite completa: 101 tests en 10 archivos aprobados. |
| Escritorio/móvil emulado, claro/oscuro/teclado, consola/geometría, reset/recarga real | Comprobados por el coordinador sobre fuente congelada, con evidencia sintética abajo. |
| Documentación, siguiente unidad y readback de hashes después del navegador | Documentos actualizados y enlaces comprobados; readback posterior 47/47 fuente/config y 14/14 protegidos intactos. |

## Evidencia de código

Rama/carpeta verificadas: `feat/phase-4-local`, `C:\Users\Developer_PC\.codex\worktrees\8520\CRM_CBN`. Se preservan los cambios previos y el aislamiento A-021/P-034; no trabajo en la carpeta de diseño o SQL. Dependencias existentes, sin reinstalación/paquetes/backend nuevos. Línea base histórica restaurada: 78 tests; no se repite esa instalación o check íntegro antes de añadir el corte.

Prueba primero: `reviewDomain.test.ts` falló por módulo todavía inexistente (RED); después pasó **12 tests** de reglas. Enfocado reglas/UI: **21 tests/2 archivos** aprobados antes de añadir una prueba de nuevo montaje. Resultado final: **23 pruebas nuevas + 78 anteriores = 101 tests/10 archivos**, formato/lint/tipos/build aprobados. Logs locales ignorados: `.local/phase-5/red-domain.txt`, `green-domain.txt`, `focused-check.txt`, `normalization.txt`, `frontend-check.txt`, `detector.txt`. Detector una vez: `[]`, exit 0.

```powershell
Set-Location 'C:\Users\Developer_PC\.codex\worktrees\8520\CRM_CBN\frontend'
npm exec -- prettier --write src/App.tsx src/shared/navigation.ts src/shared/styles.css src/shared/review.ts src/features/AcademicReview.tsx src/test/review.test.tsx src/test/reviewDomain.test.ts
npm run check
# Servidor de esta carpeta; 5173 corresponde al trabajo de diseño.
npm run dev -- --port 5174
# http://127.0.0.1:5174/#/review
```

Freeze completo después del check: `.local/phase-5/final-source-hashes.json`, **47 archivos frontend fuente/configuración**, con rutas relativas y SHA-256. Se amplía el inventario de evidencia a todos los archivos actuales de `src` y los siete archivos raíz de configuración/manifiestos; no reinterpretar el antiguo inventario de 40 como pérdida de integridad. Baseline `.local/phase-5/baseline-hashes.json`; delta `.local/phase-5/source-delta.json`. Cambian cuatro fuentes existentes (`App.tsx`, `navigation.ts`, `styles.css`, `PlannedModule.tsx`) y aparecen cuatro nuevas (`AcademicReview.tsx`, `review.ts`, `review.test.tsx`, `reviewDomain.test.ts`).

`.local/phase-5/protected-hashes.json` conserva **14 archivos protegidos**: diez backend fuente/configuración/manifiestos, dos fuentes del formulario y dos manifiestos frontend, sin cambios. Backend no reejecutado; sus siete pruebas históricas no son prueba renovada. El build y jsdom no acreditan navegador, concurrencia real, permisos, datos reales, DB/API, identidad autenticada o teléfono físico. Sin revisión receipt-driven ni aprobación fabricada.

## Corrección acotada tras navegador

El coordinador comprobó el flujo local completo, filtros/fixture incompleto, motivos/confirmaciones, reaperturas/historial, invalidación por selección/filtro/ruta, navegación/reset/recarga, móvil oscuro/teclado y que el formulario no alimenta la cola. Detectó una ambigüedad de copy en el bloque heredado de planificación: «Alcance previsto», «Fase 5 · Pendiente» y «P-011 y fase 4 pendientes» podían confundirse con el estado de las fases LOCALES ya implementadas.

Causa: aviso previo a la implementación conservado sin distinguir aceptación local y conectada. Única corrección: `PlannedModule.tsx` identifica «Alcance conectado pendiente», «Integración pendiente» y fase 1/P-011/aceptación **conectada** 4–5. Otros módulos y transiciones no cambian. La prueba de regresión del copy primero falló (RED); normalización acotada antes del check final. El snapshot inicial **100 tests/10 archivos** queda conservado en `.local/phase-5/pre-correction/` y sustituido por **101 tests/10 archivos**. Fuente congelada renovada; detector no repetido por corrección exclusivamente textual. El coordinador revalidó el aviso corregido, smoke/capturas y hashes; no cambió el source después del check final.

## Evidencia de navegador y cierre

El coordinador comprobó IAB `http://127.0.0.1:5174/#/review` sobre la fuente final: escritorio **1440×1024 claro** y móvil emulado **390×844 claro/oscuro**. Sin teléfono físico ni aprobación visual definitiva.

| Recorrido | Resultado observado |
|---|---|
| Cola/filtros/datos | Tres fixtures independientes; búsqueda sin coincidencias 0/3, filtro combinado estado/programa B 1/3, correo ausente visible. Selección excluida oculta detalle y solicita elegir caso visible. |
| Inicio/motivos/confirmación | A inicia explícitamente; motivos vacío/corto rechazan y enfocan `review-reason`. Editar confirmación conserva motivo antes de nueva revisión. Revisada/observada/rechazada requieren motivo y confirmación distinta, sin aprobación ni escritura. |
| Reapertura e historial | Reaperturas motivadas preservan nueve entradas en el recorrido de A; ningún resultado anterior se sobrescribe. |
| Aislamiento de borradores | Cambiar a B/filtro/ruta invalida confirmación y vacía motivo; resultados confirmados sobreviven navegación. |
| Reset/recarga | Cancelar reset conserva historial; confirmar reset o recarga real devuelve fixtures iniciales. |
| Teclado/temas | Móvil oscuro/claro inspeccionados; Tab desde motivo llega a revisión de acción y foco visible. |
| Geometría/consola | Ancho de contenido escritorio 1425px ≤ 1440px; móvil 375px ≤ 390px, sin overflow horizontal. Consola errores/advertencias `[]`; viewport restablecido y `#/review` limpio abierto. |
| Contrato fase 4 | Captura/revisión/confirmación real del formulario sigue siendo temporal y no alimenta la cola de tres fixtures. Validación del formulario vacío repetida después de la corrección de copy. |
| Regresiones acotadas | Clientes con cuatro fixtures/mini CRM, controles operativos Inbox, Comentarios de tres redes y Asistente compartido visibles. Smoke, no repetición completa de aceptación de fases 2/3. |
| Aviso conectado | Encabezado/badge y gate corregidos distinguen fase 1/P-011/aceptación conectada 4–5 de fases LOCALES terminadas. |

Dos incidencias de automatización no fueron fallos de producto: el locator de heading usó una propiedad no soportada y se corrigió a nombre exacto/espera de navegación; una consulta de status por igualdad falló al incluir el nodo texto adicional, y la lectura de todos los status confirmó el copy correcto. No se aplicaron correcciones funcionales por esos locators. La única corrección de producto fue el aviso heredado ambiguo descrito arriba.

### Capturas sintéticas

Tres JPEG nativos nuevos presentes; el coordinador inspeccionó la captura completa de escritorio y móvil oscuro. Dimensiones de archivo verificadas con `System.Drawing`, distintas del viewport DOM; no prueba de teléfono físico.

| Archivo | Dimensiones JPEG |
|---|---|
| [Confirmación escritorio](evidence/phase-5/desktop-confirmation.jpg) | 1425×2204 |
| [Reapertura móvil oscura](evidence/phase-5/mobile-dark-reopen.jpg) | 375×3864 |
| [Cola móvil clara](evidence/phase-5/mobile-light-queue.jpg) | 375×3324 |

Readback posterior: **47/47 hashes frontend fuente/config y 14/14 protegidos intactos**. Cierre exclusivamente documental, sin nuevo cambio de source ni reejecución innecesaria de tests. **Fase 5 y P-035 completados al 100% LOCAL**; no bloqueos locales restantes. Source/paquetes/backend/otros worktrees preservados; Vite propio PID 20848 en loopback 5174, sin detener procesos ajenos.

## Límites y reversión

Sin DB/API, identidad/proveedor auth, contratos/persistencia/canales/core, reglas académicas/eligibilidad, aprobación/matrícula/pago, notificaciones o datos personales. No simular carga/conflicto de servidor inexistente. Transiciones locales inválidas se rechazan, pero eso no prueba concurrencia ni autorización server-side. Engram continúa bloqueado por host no registrado: no se inventó sesión ni modificaron archivos de memoria.

Rollback acotado, preparado pero no ejecutado: restaurar únicamente `frontend/src/App.tsx`, `shared/navigation.ts`, `shared/styles.css`, `features/PlannedModule.tsx` desde `.local/phase-5/before`; retirar solo las cuatro fuentes nuevas del corte. Restaurar las adiciones documentales de fase 5 sin borrar cierres/evidencia A-021 o fases anteriores (los cuatro documentos previos también tienen respaldo en `before`). Retirar solo el informe nuevo si se revierte este alcance. Nunca `git reset`, rollback global, revert de Tailwind ni acceso a otros worktrees. No commit/push/PR/despliegue.

## Qué prosigue

Fase 5 LOCAL cerrada al 100%. Sigue **fase 1 — base segura y contratos de datos**, por autorización específica de alcance, o una expansión local expresamente seleccionada por el propietario. No se conecta ahora por el cierre de esta fase. No fase 6/piloto automático. Antes de DB/API/datos reales/entorno compartido: P-001/002/004/005/006/017/026 y contratos conectados; P-011 mantiene toda escritura core bloqueada. P-003/P-015 y aprobación visual final siguen pendientes.
