# Frontend: pruebas y compilación recuperadas — 2026-10-21

**APROBADO:** la verificación independiente final ejecutó **231/231 pruebas en 38 archivos** y `npm run build` con salida 0, sin diagnósticos TypeScript. No hay pruebas omitidas, pendientes, `todo` ni errores no manejados. Las 155 fuentes/configuraciones del corte permanecieron estables durante esa comprobación y los 23 archivos de la reparación conservaron sus hashes. [Resultado final](../../artifacts/qa/frontend-repair/final-checks.json).

Este cierre acredita pruebas automatizadas y compilación. No sustituye las comprobaciones visuales del [informe UI/responsive](ui-responsive-crm.md), ni acredita navegador, SQL, proveedores, autenticación o dispositivos físicos.

## Resultado y alcance

| Corte | Pruebas | TypeScript/build | Evidencia |
|---|---|---|---|
| Baseline de esta reparación | 228: 173 aprobadas, 55 fallidas; 14 errores no manejados | Seis diagnósticos TypeScript; build fallido | [Baseline](../../artifacts/qa/frontend-repair/baseline-checks.json) |
| Entrega del escritor, normalizada | 228/228 aprobadas en 37 archivos | TypeScript y build aprobados; 96 módulos | [Implementación, 23 paths y SHA antes/después](../../artifacts/qa/frontend-repair/implementation.json) |
| Verificación independiente estable | 231/231 aprobadas en 38 archivos; cero omitidas, pendientes, `todo` o errores no manejados | TypeScript y build aprobados; 97 módulos | [Verificación final](../../artifacts/qa/frontend-repair/final-checks.json) |

El aumento de tres pruebas y un archivo corresponde al nuevo wrapper de Asistente incorporado por trabajo concurrente, conservado en el corte final. No se eliminaron casos para alcanzar el resultado: la verificación comparó los 37 archivos originales y confirmó que ninguno perdió cantidad de pruebas.

## Causas y correcciones

La reparación modificó **dos archivos de producto y 21 de pruebas/fixtures**. El listado exacto de los 23 paths, sus SHA previos/finales y los comandos está en [implementation.json](../../artifacts/qa/frontend-repair/implementation.json).

| Causa comprobada | Corrección aplicada | Conservación |
|---|---|---|
| Bindings sin lectura: `Settings.setSection` e `Inbox.options` | Se omite únicamente el binding no usado de cada tupla. Inbox recibió además formato local. | Hooks, setters, consulta de opciones y efectos intactos. |
| Fixtures de Inbox incompletos frente a los tipos públicos | Se completan `destinations`, `miniCrm`, `operation`, SLA `firstResponseDueAt` y metadatos de entrega/adjuntos de mensajes. Se reutiliza el fixture tipado en merge. | No se vuelven opcionales los contratos productivos; identidad, canal, conflictos y operaciones siguen comprobándose. |
| Componentes montados sin el propietario real de sesión | Assistant y Agentes se envuelven con `WorkspaceSessionProvider`, como en la aplicación. | Sin mocks de hooks ni fallback de estado; borradores y aislamiento de sesión conservados. |
| Selectores/textos y navegación de pruebas desactualizados | Se usan nombres vigentes, el botón único de tema, las regiones correctas de navegación y los mensajes actuales de guardado. | No se cambió App ni se restauraron controles retirados para satisfacer expectativas antiguas. |
| Pruebas API basadas en un editor inline retirado | Se abre el proveedor, su modal de credencial y sus acciones de catálogo/modelo; al remontar se reabre el editor transitorio y se comprueba el catálogo/borrador de sesión. Mocks de canales y conversación corresponden a sus contratos. | Se mantienen secretos de solo escritura, rechazo `outbound_disabled` del servidor y ausencia de activación implícita. En jsdom solo se simula apertura/cierre del diálogo y se restauran sus descriptores. |
| Caso de audio sin modelo y catálogo de voz sin permiso explícito | La fixture de éxito declara los modelos de análisis; se espera el resultado asíncrono del adjunto. El caso permitido del catálogo declara `outboundEnabled`. | No se modifican las guardas de inferencia, adjuntos o salida externa. |
| Inventario y pantallas de Canales anteriores a su operación local | Se comprueban 157 rutas, 134 stubs 501, 14 propuestas sustituidas, 122 esquemas definidos y 12 provisionales; fase 7 conserva 38. Se verifican las identidades concretas sustituidas y sus rutas operativas. | Abrir la configuración no activa servicios ni guarda credenciales. Los conteos no se actualizaron sin comprobar las rutas. |

La [revisión estática independiente](../../artifacts/qa/frontend-repair/review.json) examinó los 23 archivos y no encontró hallazgos accionables. Su alcance es ese parche, no una aprobación general de todos los cambios concurrentes.

## Comandos y evidencia

Ejecutados desde `E:\Nuevos_Proyectos\CRM_CBN\frontend`:

| Comando | Estado | Evidencia |
|---|---|---|
| `npm run typecheck` | **APROBADO** en la reparación | Resultado registrado en [implementación](../../artifacts/qa/frontend-repair/implementation.json); el build independiente vuelve a ejecutar `tsc --noEmit`. |
| `npm exec -- prettier --check <23 paths modificados>` | **APROBADO** focal | Paths exactos y resultado en [implementación](../../artifacts/qa/frontend-repair/implementation.json). |
| `npm exec -- eslint <23 paths modificados>` | **APROBADO** focal | [Log](../../.local/frontend-repair-20261021/scoped-lint.log). |
| `npm test -- --reporter=json --outputFile=../.local/frontend-repair-20261021/tests-final.json` | **APROBADO**, 228/228 | [JSON del escritor](../../.local/frontend-repair-20261021/tests-final.json), [log](../../.local/frontend-repair-20261021/tests-final.log). |
| `npm.cmd test -- --reporter=default --reporter=json --outputFile.json=../.local/frontend-repair-20261021/tests-independent-stable.json` | **APROBADO**, 231/231 | [JSON independiente](../../.local/frontend-repair-20261021/tests-independent-stable.json), [log](../../.local/frontend-repair-20261021/tests-independent-stable.log). |
| `npm.cmd run build` | **APROBADO** independiente | [Log final](../../.local/frontend-repair-20261021/build-independent-stable.log). |
| `git diff --check` sobre los archivos del parche, desde la raíz | **APROBADO** | Verificación de whitespace del parche; no reemplaza pruebas funcionales. |

La normalización se limitó a los archivos modificados antes de verificar. No se usaron `skip`, `todo`, `only`, exclusiones condicionales nuevas, relajación de tipos/guardas ni aumentos de timeout para ocultar fallos. No se cambiaron dependencias ni configuración de pruebas/compilación. Lint y formato **globales** no se volvieron a ejecutar: la aprobación focal no los convierte en verdes.

## Trabajo concurrente y estabilidad

Se preservaron las modificaciones concurrentes de Agentes y documentación. Durante un primer intento independiente, el índice de IA apuntaba a `AgentAssistantChat` antes de que su archivo estuviera disponible: se registró TS2307 y siete fallos de colección. Después aparecieron la página y sus tres pruebas. Ese intento **FALLIDO** permanece en [final-checks-concurrent-attempt.json](../../artifacts/qa/frontend-repair/final-checks-concurrent-attempt.json); no se borró ni se contó como prueba aprobada.

La nueva pasada comenzó sobre el árbol completo y estable, sin ediciones del verificador. Comparó SHA antes/después de **155 fuentes/configuraciones**, sin deriva, y confirmó intactos los 23 paths del escritor. El resultado que cierra este trabajo es la [pasada estable aprobada](../../artifacts/qa/frontend-repair/final-checks.json), que incluye el trabajo concurrente disponible en ese momento.

## Límites y siguiente comprobación

- Vite informa un chunk JavaScript de **605,37 kB**, superior a su aviso de 500 kB. El build termina correctamente; no se cambió la configuración para ocultar el aviso ni se emprendió una optimización no solicitada.
- **NO PROBADO por esta reparación:** navegador, base de datos, proveedores, canales externos, auth/RBAC y dispositivos físicos. Los resultados jsdom no acreditan diálogo nativo, zoom, teclado virtual o accesibilidad completa.
- Siguen vigentes los pendientes del [informe responsive](ui-responsive-crm.md): zoom real al 200 % **BLOQUEADO**, dispositivos/otros navegadores sin prueba, más validación funcional pendiente. Este cierre sustituye únicamente sus fallos históricos de suite y TypeScript/build; no declara aprobados lint/formato globales ni esos escenarios.
- No hubo commit, push, PR, despliegue, cambios de SQL, activación de proveedores o envíos. Cualquier edición posterior de fuentes/configuración requiere comprobar nuevamente la evidencia que dependa de esos bytes.
