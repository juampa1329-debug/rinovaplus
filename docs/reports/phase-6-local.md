# Fase 6 — operación demostrativa LOCAL

**Estado A-023/P-036: completada al 100% exclusivamente LOCAL.** Código, check final de 129 tests y navegador escritorio/móvil emulado/claro/oscuro/teclado comprobados; aviso corregido revalidado y readback posterior 51/51 fuentes/config + 19/19 protegidos intactos. Alcance y checklist fijados en este informe antes de modificar source. Fecha: 2026-10-14, America/Bogota. No piloto ni aceptación de operación conectada.

## Autorización y límite

Instrucción del propietario: «con la fase6, fase1dejaremos después cuandohayamos construido todosendpoints». Se conserva el contexto LOCAL, funcional y sin DB/APIs. La fase 6 original exige operación conectada; esta unidad entrega exclusivamente su demostrador local, no un piloto real ni su aceptación original.

Secuencia explícita: **0 → 2 → 3 → 4 → 5 → 6 LOCAL → construcción de contratos/stubs de endpoints en unidad separada → 1**. Fase 1 sigue siendo obligatoria **antes de activar/exponer endpoints reales, acceso de personas reales, datos reales, conexión a proveedores, entorno compartido o despliegue**. Construir contratos/stubs no autoriza esas acciones. Piloto 6 conectado exige 1, aceptación conectada aplicable y autorización específica.

## Aceptación LOCAL fijada antes del source

- [x] Source/jsdom: Ajustes → Diagnóstico mantiene contadores existentes y agrega escenarios sintéticos estable/proveedor no disponible/cola detenida/envío incierto; ningún indicador representa servicio conectado.
- [x] Source/jsdom: estado por escenario estable/degradado/pausado/en revisión de recuperación. Selección no muta ni pierde otras incidencias.
- [x] Source/jsdom: pausa explícita y confirmada, vinculada al registro/revisión/motivo; no modifica Inbox, handoff, configuración IA, formulario ni revisión académica.
- [x] Source/jsdom: checklist reversible solo en pausa; revisión bloqueada sin todos los pasos, reanudación bloqueada sin revisión. Cada transición conserva historial temporal y fecha local real; no promete restauración/reconciliación.
- [x] Source/jsdom y navegador: acciones confirmadas revalidan registro/revisión y el motivo capturado; cancelar, cambiar escenario/motivo/checklist/sección/ruta invalidan la confirmación. Navegar conserva resultados en App, no borradores; reset/nuevo montaje elimina todo. Recarga real comprobada en navegador.
- [x] Source/jsdom: incidencias/contadores/historial proceden exclusivamente de fixtures y acciones manuales locales. No timer, scheduler, llamadas, storage de negocio, reenvío o procesamiento de colas.
- [x] Source/jsdom: runbook/checklist visible usa límites de seguridad existentes; roles, contactos, SLAs, budgets y RPO/RTO siguen sin configurar. Exportación/baja/rotación/revocación upstream/colas reales siguen bloqueadas.
- [x] Normalización acotada, tests/check final y freeze completo; backend, manifiestos, fase 4 y fuentes de revisión fase 5 protegidos. Check inicial 128 tests y check posterior a la corrección de copy 129 tests, según detalle abajo.
- [x] Navegador escritorio/móvil emulado/claro/oscuro/teclado, confirmaciones, historial, navegación/reset/recarga, aviso corregido y regresión acotada, por coordinador; readback posterior 51/51 fuentes/config + 19/19 protegidos intactos. Cierre 100% LOCAL, no teléfono físico/aprobación visual humana final.

## Fuentes y alcance proporcional

[Roadmap original 6](../roadmap.md), [operabilidad/recuperación](../security-and-operations.md) y [SET-04, DI-01/02/03](../design/settings-specification.md) justifican estado, pausa, incidencias y checklist. Se reutilizan App, componentes y tokens existentes; no navegación o módulo independiente. No se replica timeline/tareas de fase 3 ni revisión académica de fase 5. La simulación muta exclusivamente fixtures propios en memoria y se rotula como tal; no es la simulación conectada DI-03.

## Evidencia y siguiente bloqueo

Línea base comprobada por hashes: 47 archivos frontend/config; 19 protegidos (14 anteriores y cinco fuentes/tests de fases 4/5), intactos. Respaldo preexistente de las seis fuentes/documentos a modificar en `.local/phase-6/before/`; no se descarta el trabajo sucio anterior. Engram no permite lectura/escritura por host no registrado; no se inventan identidades ni se modifican memorias locales.

Línea base renovada: `npm run check`, **101 tests/10 archivos**, formato/lint/tipos/build aprobados. Se preserva el cierre anterior; no se usa solo su cifra histórica.

Pruebas primero: `operationsDomain.test.ts` RED por módulo inexistente; GREEN **17 tests**. `operations.test.tsx` RED **10 fallos esperados** por UI inexistente; GREEN enfocado **27 tests/2 archivos**. Tras normalización, check inicial **128 tests/12 archivos** (101 anteriores + 27 nuevos; sustituido por check final 129 después de la corrección detallada abajo), formato/lint/tipos/build aprobados. No fallos de producto pendientes en esta capa. Detector mecánico una vez: `[]`, exit 0. No revisión semántica externa ni conformidad accesible certificada; inspección de navegador por coordinador.

```powershell
# cwd frontend; dependencias existentes, sin instalación
npm test -- src/test/operationsDomain.test.ts
npm test -- src/test/operations.test.tsx src/test/operationsDomain.test.ts
npm exec -- prettier --write src/App.tsx src/features/Settings.tsx src/features/OperationDiagnostics.tsx src/shared/operations.ts src/test/operations.test.tsx src/test/operationsDomain.test.ts
npm run check
```

Logs ignorados: `.local/phase-6/baseline-check.txt`, `red-domain.txt`, `green-domain.txt`, `red-ui.txt`, `focused-check.txt`, `normalization.txt`, `frontend-check.txt`, `detector.txt`. Freeze después del check: `.local/phase-6/final-source-hashes.json`, **51 archivos**, rutas relativas/SHA-256, source completo más siete archivos raíz de configuración. Delta frente a baseline: **dos fuentes existentes** `App.tsx`/`features/Settings.tsx` y **cuatro nuevas** `features/OperationDiagnostics.tsx`, `shared/operations.ts`, `test/operations.test.tsx`, `test/operationsDomain.test.ts`; `.local/phase-6/source-delta.json`. **19/19 protegidos intactos**, `.local/phase-6/protected-hashes.json` y `builder-readback.json`; backend/manifiestos/formulario/revisión existentes sin cambios y backend no reejecutado. CSS, tokens, Tailwind, navegación y resto de fuentes preservados. `git diff --check` exit 0 con avisos heredados de normalización LF/CRLF, sin mutación Git.

Navegador y readback comprobados por coordinador; cierre exclusivamente documental después de la prueba final, sin normalización/check adicional innecesario ni cambio de source. P-012/019/025/026 y todas las puertas conectadas siguen abiertos. Sin Git/commit/push/PR/despliegue/instalación/backend/SQL ni otras carpetas. El escritor no inicia, detiene ni modifica runtime. El coordinador verificó disponibilidad del frontend de esta carpeta mediante recarga real en loopback 5174; esto no reconfirma el PID histórico 20848 ni otro detalle del proceso host. La consulta sandbox sin PID no prueba ausencia de runtime.

## Recorrido de navegador — comprobado por coordinador

1. `#/settings` → **Diagnóstico** → **Ensayo de operación local**; seleccionar **Proveedor no disponible · Fixture**, **Cola detenida · Fixture** o **Envío incierto · Fixture**. Estado inicial Degradado · Demo; stable es otro fixture, no conexión comprobada.
2. **Motivo ficticio de operación** vacío → **Pausar escenario local**: error asociado. Motivo sintético → preparar/cancelar/confirmar; solo cambia el escenario seleccionado. Cambio de motivo/escenario/sección invalida confirmación y no filtra checklist entre registros.
3. Pausado: **Revisar recuperación local** deshabilitado hasta tres pasos. Marcar/desmarcar registra eventos; desmarcar invalida preparación. Confirmar revisión → En revisión de recuperación · Demo; **Reanudar escenario local** requiere motivo/confirmación nuevos.
4. Reanudar → Estable · Demo, incidencia cerrada en demo, contador abierto baja y **Historial operativo local (6)** conserva pausa/3 pasos/revisión/reanudación. No botón de reenvío ni entrega externa confirmada.
5. Sección **Runbook local y puertas de operación**: políticas sin configurar y tres acciones reales bloqueadas. Navegación conserva resultados, no motivos pendientes; reset confirmado/recarga borra todo. Pausa de demo no interfiere con **Tomar control · Demo** / **Devolver a IA · Demo** de Inbox.
6. Escritorio/móvil emulado, claro/oscuro, teclado/foco/geometría/consola; smoke de formulario, revisión, Clientes/mini CRM, Inbox, Comentarios y Asistente sin repetir su entrega ni afirmar conformidad accesible certificada.

## Pase inicial de navegador y corrección acotada

El coordinador comprobó escritorio 1440 y móvil emulado 390, claro/oscuro y teclado: error de motivo vacío visible, cancelar no registra, cambio de motivo/escenario/sección/ruta invalida preparación y no reutiliza el motivo. Pausa del proveedor persiste al navegar; Inbox permite tomar control y usar compositor humano sin modificar el escenario pausado. Checklist de 2/3 bloquea revisión; tercero la permite; desmarcar invalida preparación y volver a marcar preserva historial (8 eventos en ciclo proveedor con desmarcado). Envío incierto completa ciclo limpio de 6 eventos, cierre solo demo y sin confirmar entrega externa; cola conserva estado inicial degradado/historial 0/checklist independiente.

Pausa preventiva del fixture estable comprobada en móvil. Cancelar reset preserva resultados; confirmarlo o recargar restituye fixtures. Texto sintético de 295 caracteres sin separadores se mantiene acotado por campo 300 y sin overflow; contenido escritorio 1425 ≤ viewport 1440 y móvil 375 ≤ viewport 390. Tab desde motivo enfoca Pausar, con foco visible; consola errores/advertencias vacía y viewport restituido al final. Motivo vacío produce error visible con `aria-invalid=true` y `aria-describedby=operation-error`. Runbook conserva roles/contactos/SLA/budget/RPO/RTO sin configurar y acciones reales deshabilitadas. Un deadline de automatización al localizar reset se resolvió con DOM fresco/click directo; no defecto de producto demostrado.

**Defecto de copy detectado:** la confirmación global de reset enumeraba fichas/revisiones/mensajes/borradores pero omitía ensayos operativos, que también descarta. Causa: aviso heredado no extendido al incorporar OperationRecord. Única corrección de source: `App.tsx` ahora incluye **«ensayos operativos (incluidos su historial y checklist)»** antes de confirmar. Prueba enfocada nueva en `operations.test.tsx` primero falla por ausencia del aviso (RED); normalización de esos dos archivos antes del nuevo check. Ninguna transición/regla/componente/CSS o infraestructura cambia; sin nuevo detector por cambio exclusivamente de texto.

Snapshot inicial **128 tests/12 archivos** preservado en `.local/phase-6/pre-correction/`, incluido log/check y hashes, App y test previos. Check posterior a la corrección: **129 tests/12 archivos** (101 baseline + 27 iniciales + 1 regresión de aviso), formato/lint/tipos/build; freeze renovado en ruta habitual con 51 fuentes/config y 19 protegidos. Logs `correction-red.txt`, `correction-normalization.txt` y `frontend-check.txt`. El coordinador recargó realmente 5174 con el freeze renovado, comprobó el aviso corregido explícito sobre ensayos/historial/checklist; cancelar conserva dos eventos y confirmar restituye el escenario semilla/historial 0. Readback directo posterior a esta prueba: **51/51 fuentes/config + 19/19 protegidos intactos**. Cierre al 100% exclusivamente LOCAL.

Tres capturas sintéticas del pase inicial, formato JPEG y dimensiones de archivo comprobados (no inferidas del viewport):

| Archivo en `evidence/phase-6/` | Dimensiones reales | Bytes | Inspección |
|---|---|---|---|
| `desktop-resume-confirmation.jpg` | 1425 × 2426 | 205626 | Coordinador, CUA. |
| `mobile-dark-history.jpg` | 375 × 3422 | 167721 | Coordinador, CUA. |
| `mobile-light-paused.jpg` | 375 × 3222 | 149840 | Coordinador, view_image. |

El panel de operación representado no cambió por la corrección del aviso global; no atribuir prueba visual de ese aviso a estas capturas. La confirmación corregida se comprobó directamente tras recargar. El pase funcional inicial sigue válido para `OperationDiagnostics.tsx`/`operations.ts` intactos; no se repite toda la matriz por un cambio de texto global. Smoke posterior a la corrección: cuatro Clientes/mini CRM, Inbox toma humana/compositor, Comentarios de tres redes, inicio/motivo de revisión académica y validación vacía del formulario; Asistente compartido comprobado en el pase previo. Esto no reejecuta íntegramente los gates históricos de fases anteriores.

## Cierre y siguiente unidad

Todos los criterios acordados de fase 6 LOCAL y P-036 están comprobados; A-023 queda completado. Sin bloqueos locales restantes. No integración conectada, SLA/RPO/RTO/budget/roles/privacidad/seguridad/piloto aceptados, recuperación real, secretos, reenvíos o identidad autenticada; sin teléfono físico ni aprobación visual humana definitiva. El alcance original de operación 6 permanece separado y no se declara 100%.

Siguiente por instrucción vigente: **construcción de contratos/stubs de endpoints en una unidad separada; después fase 1 antes de activación/exposición/acceso/datos reales/proveedores/entorno compartido/despliegue**. Piloto 6 conectado requiere fase 1, aceptación conectada aplicable y autorización específica. Fase 7 y otras expansiones no quedan comprometidas por este cierre.

## Reversión acotada — preparada, no ejecutada

Restaurar exclusivamente `frontend/src/App.tsx`, `frontend/src/features/Settings.tsx` y los cuatro documentos README/roadmap/progress/pending desde `.local/phase-6/before/`; retirar exclusivamente las cuatro fuentes nuevas y este informe si se revierte toda la unidad. El respaldo contiene el trabajo previo del día, no HEAD. No `git reset`, limpieza global, rollback de Tailwind/fases 4/5 ni acceso a otros worktrees. Si documentos recibieron cierre posterior del coordinador, revertir solo adiciones A-023/P-036 sin eliminar evidencia ajena.

## Key Learnings:

1. Fase 6 LOCAL es un ensayo de estados/checklist; no sustituye el piloto conectado ni aprueba SLA, recovery o permisos.
2. El vínculo ID+revisión invalida confirmaciones tras un checklist reversible; App conserva resultados por navegación y los borradores viven solo en la sección.
3. La pausa de un escenario sintético no debe pausar la atención humana ni alterar consentimiento/configuración/reglas core.
