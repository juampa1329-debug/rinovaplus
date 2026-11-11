# Auditoría UI y responsive del CRM — 2026-10-21

Se corrigieron cuatro hallazgos comprobados: acceso al formulario al crear Clientes/Agentes, texto del avatar de Resumen, mensaje de error de conexión de Agentes y presentación/foco de los campos inválidos de Clientes. Ego verificó las cuatro correcciones y la persistencia del registro QA en el backend local después de recargar. Hay **63 mediciones de layout sin desbordamiento lateral del documento**; ese resultado no aprueba todos los flujos. En aquel corte, los checks globales del frontend fueron **FALLIDOS** y el zoom real al 200 % quedó **BLOQUEADO**.

**Actualización posterior — 2026-10-21:** los seis diagnósticos TypeScript y los fallos de suite de este snapshot histórico fueron sustituidos por la [reparación y verificación independiente de frontend](frontend-repair.md): **231/231 pruebas y build aprobados**. Esta actualización solo cierra suite y compilación; lint/formato globales, zoom y dispositivos conservan sus pendientes. Las tablas y logs siguientes documentan el corte de auditoría original.

## Entorno, alcance y criterio

- Proyecto: `E:\Nuevos_Proyectos\CRM_CBN`; entorno local abierto en `http://127.0.0.1:4173`, con `/health/live` comprobado. Frontend real React/TypeScript, Vite, CSS compartido y utilidades Tailwind; backend local FastAPI y persistencia configurada sobre copia SQL local. No se cambió el stack ni se consultó SQL directamente durante esta auditoría.
- Navegador: Ego/Chromium, Space de QA; viewports efectivos en píxeles CSS y emulación táctil cuando corresponde. No son dispositivos físicos. La meta viewport observada fue `width=device-width, initial-scale=1.0`.
- Identidad visual conservada: Glass/Azul noche, componentes y tokens existentes. Tema oscuro recorrido a 1440 y 390 px, con tema claro restaurado al terminar: [escritorio](../../artifacts/qa/ui-responsive-crm/theme-dark-1440.png), [móvil](../../artifacts/qa/ui-responsive-crm/theme-dark-390.png).
- No hay autenticación/RBAC institucional implementados en este acceso local. Las filas de las matrices usan el mismo acceso local sin rol autenticado; no acreditan otros roles ni inicio de sesión empresarial.
- Evidencia combinada: capturas observadas, snapshots y mediciones DOM, foco/teclado, interacción por controles y relectura tras recarga. No se usaron clics forzados ni cambios temporales del DOM como corrección.
- **APROBADO**: el caso y la capa descritos se comprobaron. **FALLIDO**: se observó incumplimiento. **BLOQUEADO**: una capacidad o dependencia impidió verificar. **NO PROBADO**: sin ejecución suficiente. **NO APLICA**: función ausente o caso ajeno, explicado individualmente.

El plan ejecutado fue: revisar navegación y módulos, capturar los tres tamaños base, reproducir los defectos, corregir sus causas, repetir los casos y ampliar tamaños/breakpoints, flujos y comprobaciones automatizadas. El trabajo local previo y las modificaciones concurrentes se conservaron; no se aprobaron perfiles de agentes ni cambios de negocio ajenos al registro QA.

## Hallazgos corregidos

| ID / gravedad | Ruta, estado y reproducción | Antes / esperado | Causa y solución | Resultado final y evidencia |
|---|---|---|---|---|
| UI-01 / media | `#/clients` → Nuevo; `#/agents` → Crear agente. Móvil 320×568, formulario nuevo. | **FALLIDO**: foco retenido en botón superior; el editor quedaba lejos del viewport. Se esperaba acceder inmediatamente al nombre. | La acción actualizaba el estado sin foco. Ref del formulario y contador exclusivo de creación disparan el foco después del render. No depende de cada edición del borrador. | **APROBADO**: nombre visible a ~262 px de altura, campo de 44 px y Tab al siguiente control. Repetir Nuevo conserva el borrador; repetir Crear agente genera uno nuevo, como antes. [DOM final](../../artifacts/qa/ui-responsive-crm/focus-after.json). |
| UI-02 / media | `#/overview`, atención pendiente, nombre largo; base 1440×900 y repetición 390×844. | **FALLIDO**: avatar de 40 px con contenido de 48 px; se mostraba el apellido completo. Se esperaba una inicial legible sin invadir el nombre. | `name.split(" ").at(-1)` devolvía una palabra. Se usa la primera inicial, recortando espacios y convirtiendo a mayúscula; el nombre completo adyacente permanece. | **APROBADO**: tres avatares medidos, incluido QA, con ancho/contenido 40/40 px y un glifo. [DOM final](../../artifacts/qa/ui-responsive-crm/avatar-after.json), [baseline](../../artifacts/qa/ui-responsive-crm/baseline-layout.json). |
| UI-03 / baja | `#/agents`, 390×844; poner solo la pestaña de prueba offline y pulsar Actualizar; restaurar conectividad y repetir. | **FALLIDO**: alert literal `Failed to fetch`. Se esperaba un mensaje español que explicara el fallo y cómo recuperarse. | El rechazo `TypeError` de fetch escapaba antes del procesamiento HTTP. El cliente API lo convierte mediante el catálogo de mensajes a «No se pudo conectar con el servidor. Revise la conexión y vuelva a intentarlo.». Ramas HTTP y validación conservadas. | **APROBADO**: aviso español, sin overflow; Actualizar recupera catálogo/proveedores HTTP 200. [Red final](../../artifacts/qa/ui-responsive-crm/network-final.json), [recuperación](../../artifacts/qa/ui-responsive-crm/network-recovery.json). |
| UI-04 / media | `#/clients`, 390×844, Nuevo; nombre/teléfono/etapa vacíos → Crear ficha. Después completar el nombre y repetir con etapa vacía. | **FALLIDO**: error de nombre fuera de vista con foco en botón inferior. El caso de etapa mostraba aviso general, pero el selector no recibía el error ni `aria-invalid`. Se esperaba acceder al primer control inválido y conocer su error asociado. | Se reutiliza la solicitud explícita de foco después de renderizar errores. Además `ClientFields` pasa `fieldErrors.stage` al `SelectField` existente; no cambia el validador. Escribir no vuelve a disparar foco. | **APROBADO** en Ego y regresión: nombre y etapa enfocados/visibles, campos de 44 px a ~400 px, error de etapa asociado. `onSave` no llamado; no se guardó el borrador inválido. [Antes DOM](../../artifacts/qa/ui-responsive-crm/validation.json), [después DOM](../../artifacts/qa/ui-responsive-crm/validation-after.json), [regresión](../../artifacts/qa/ui-responsive-crm/validation-check.json). |

### Capturas antes/después y evidencia complementaria

| Caso | Antes | Después |
|---|---|---|
| Agentes, crear a 320×568 | [Página completa con borrador fuera de vista](../../artifacts/qa/ui-responsive-crm/before-agent-draft-320.png) | [Viewport con nombre enfocado y visible](../../artifacts/qa/ui-responsive-crm/after-create-agents-320.png) |
| Clientes, acceso al editor móvil | [Ficha QA a 390×844](../../artifacts/qa/ui-responsive-crm/before-clients-qa-390.png) | [Creación a 320×568](../../artifacts/qa/ui-responsive-crm/after-create-clients-320.png) |
| Resumen, avatar a 390×844 | [Apellido desbordado](../../artifacts/qa/ui-responsive-crm/before-avatar-390.png) | [Inicial dentro del avatar](../../artifacts/qa/ui-responsive-crm/after-avatar-390.png) |
| Agentes, error a 390×844 | [Error de transporte crudo](../../artifacts/qa/ui-responsive-crm/agents-network-error-390.png) | [Mensaje traducido](../../artifacts/qa/ui-responsive-crm/after-network-error-390.png) |
| Clientes, submit inválido a 390×844 | [Error de nombre fuera de vista](../../artifacts/qa/ui-responsive-crm/validation-required-390.png) | [Nombre enfocado](../../artifacts/qa/ui-responsive-crm/after-validation-name-390.png), [etapa y error asociado](../../artifacts/qa/ui-responsive-crm/after-validation-stage-390.png) |

En Agentes el viewport emulado es 320×568 en ambos casos, pero el antes captura la página completa y el después solo el viewport; son evidencia complementaria del acceso al formulario, no una comparación píxel a píxel. En Clientes, para acceso al editor, el antes es 390×844 y el después 320×568, con distinto estado; no existe captura baseline del foco de Clientes a 320 px. Su repetición final a 320×568 está medida en `focus-after.json`. La pareja de avatar usa el mismo viewport de 390×844 y datos enmascarados. La pareja de error usa 390×844 y el mismo escenario de desconexión de la pestaña. La validación usa 390×844; el antes y el después de nombre repiten ese error, mientras la captura de etapa es el segundo submit con nombre completado. Ninguna pareja con distinto encuadre o estado se presenta como igualdad visual exacta.

### Archivos de esta corrección

| Archivo | Cambio |
|---|---|
| [AgentsPanel.tsx](../../frontend/src/modules/agents/AgentsPanel.tsx) | Foco al crear agente. |
| [Clients.tsx](../../frontend/src/modules/clients/pages/Clients.tsx) | Foco al crear/retomar borrador nuevo y al primer control inválido después del submit rechazado. |
| [ClientFields.tsx](../../frontend/src/modules/clients/components/ClientFields.tsx) | Asocia el error de etapa al selector compartido por Clientes e Inbox, sin cambiar reglas ni foco de Inbox. |
| [Overview.tsx](../../frontend/src/features/Overview.tsx) | Inicial del avatar; ajustes locales de formato sin cambio de texto. |
| [agents/api.ts](../../frontend/src/modules/agents/api.ts) | Mensaje de fallo de transporte. |
| [responsiveActions.test.tsx](../../frontend/src/test/responsiveActions.test.tsx) | Cuatro regresiones de foco, validación, borrador e inicial. |
| [agentsTransport.test.ts](../../frontend/src/test/agentsTransport.test.ts) | Regresión de fetch y conservación de mensajes HTTP 409/422. |

Baseline de los cinco archivos fuente copiado **antes** de editarlos, con SHA-256 en [manifiesto local](../../.local/ui-responsive-crm-20261021/before-fix/manifest.json); el corte previo al ajuste de validación se conserva además en `.local/ui-responsive-crm-20261021/before-validation/`. [Manifiesto final](../../artifacts/qa/ui-responsive-crm/final-source-manifest.json) de las cinco fuentes y dos pruebas. No se modificaron CSS/tokens para ocultar overflow, ni contratos de API, permisos, backend o reglas de negocio. El consumidor Inbox ya pasaba `fieldErrors` al componente compartido: la asociación de etapa se conserva allí sin introducir foco automático nuevo.

## Inventario y matriz de pantallas

Se abrieron las diez rutas reales del [registro de navegación](../../frontend/src/shared/navigation.ts). En la tabla, **APROBADO significa únicamente layout revisado sin desbordamiento lateral involuntario del documento**. Las funciones no ejercitadas siguen pendientes aunque su pantalla se abra correctamente. Los flujos concretos tienen su propia matriz más abajo.

| Pantalla/ruta | 1440×900 | 768×1024 | 390×844 | Alcance visible |
|---|---|---|---|---|
| Resumen `#/overview` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-overview-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-overview-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-overview-390.png) | Métricas, gráficos y atención pendiente. |
| Clientes `#/clients` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-clients-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-clients-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-clients-390.png) | Lista, filtros y ficha compartida. |
| Admisiones `#/admissions` | [APROBADO](../../artifacts/qa/ui-responsive-crm/admissions-search-qa-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/admissions-search-qa-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/admissions-search-qa-390.png) | Período/catálogos y búsqueda QA sin resultados. |
| Inbox `#/inbox` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-inbox-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-inbox-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-inbox-390.png) | Navegación de conversaciones y ficha CRM. |
| Agentes `#/agents` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-agents-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-agents-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-agents-390.png) | Constructor, jerarquía y navegación de secciones. |
| Asistente `#/assistant` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-assistant-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-assistant-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-assistant-390.png) | Distribución y controles; sin enviar consultas. |
| Campañas `#/campaigns` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-campaigns-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-campaigns-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-campaigns-390.png) | Consulta de pantalla; sin activar campañas. |
| Conocimiento `#/knowledge` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-knowledge-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-knowledge-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-knowledge-390.png) | Controles y estado disponible; sin publicar fuentes. |
| Memoria `#/memory` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-memory-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-memory-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-memory-390.png) | Registro QA seleccionado; sin reinicio de memoria. |
| Ajustes `#/settings` | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-settings-1440.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-settings-768.png) | [APROBADO](../../artifacts/qa/ui-responsive-crm/after-settings-390.png) | Navegación y controles; sin guardar credenciales. |

[Matriz DOM base: 30 filas](../../artifacts/qa/ui-responsive-crm/final-base-matrix.json). Algunas capturas iniciales de Admisiones registran carga: las enlazadas arriba corresponden al estado estable, respaldado por [admissions-read.json](../../artifacts/qa/ui-responsive-crm/admissions-read.json). Período observado 128, 72 opciones de programa y cuatro de jornada, sin alerts. Esto no prueba la ficha de un aspirante institucional: la búsqueda sintética no obtuvo resultados. Memoria tiene lectura independiente con QA seleccionado en [memory-layout.json](../../artifacts/qa/ui-responsive-crm/memory-layout.json).

### Ampliación por tamaños y breakpoints

Todas las siguientes mediciones dieron **APROBADO solo para ausencia de overflow del documento**. Son 15 casos ampliados y 18 de breakpoint, además de los 30 base: **63 en total**. [Matriz DOM ampliada completa](../../artifacts/qa/ui-responsive-crm/extended-matrix.json).

| Ruta | 1366×768 | 1920×1080 | 1024×768 | 360×800 | 320×568 |
|---|---|---|---|---|---|
| Resumen | [Captura](../../artifacts/qa/ui-responsive-crm/extended-overview-1366.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-overview-1920.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-overview-1024.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-overview-360.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-overview-320.png) |
| Inbox | [Captura](../../artifacts/qa/ui-responsive-crm/extended-inbox-1366.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-inbox-1920.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-inbox-1024.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-inbox-360.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-inbox-320.png) |
| Agentes | [Captura](../../artifacts/qa/ui-responsive-crm/extended-agents-1366.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-agents-1920.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-agents-1024.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-agents-360.png) | [Captura](../../artifacts/qa/ui-responsive-crm/extended-agents-320.png) |

| Ruta | Anchos justo antes/en/después del límite, altura 800 px | Casos |
|---|---|---|
| Resumen | 759/760/761 y 1149/1150/1151 | 6 |
| Inbox | 1099/1100/1101 | 3 |
| Agentes | 559/560/561 y 899/900/901 | 6 |
| Ajustes | 639/640/641 | 3 |

Los primeros `coveredControls` eran señales geométricas, no defectos aceptados: incluían descendientes de `<details>` cerrados. La ampliación registró `visible:false` y `closedDetails:true` en `hitCandidates`; no se contabilizaron como acciones visibles tapadas. Las capas intencionales no se clasificaron como errores por mera intersección.

## Matriz de flujos e interacción

Acceso en todas las filas: sesión local sin rol autenticado. Los resultados se limitan a los datos/estados ejecutados.

| Flujo y viewport | Estado | Comprobación y evidencia |
|---|---|---|
| Navegar por las diez rutas; tres tamaños base | **APROBADO** | Capturas y matriz base anteriores. No acredita ejecución de las acciones de cada módulo. |
| Crear interesado/contacto QA, encontrar y abrir ficha; móvil 390×844 | **APROBADO** | Registro identificable creado mediante UI y recuperado desde backend tras recarga, sin teléfono. [Persistencia](../../artifacts/qa/ui-responsive-crm/qa-persistence.json), [ficha](../../artifacts/qa/ui-responsive-crm/after-clients-390.png). |
| Editar ciudad, jornada, tipo y notas; recargar | **APROBADO** | Relectura confirmó `QA Ciudad`, `QA Jornada de revisión`, tipo `QA`, notas de auditoría y teléfono vacío. Prueba de backend local después de recarga; no es solo toast, estado optimista o localStorage. No se reinició el proceso ni se consultó SQL directamente. |
| Buscar + combinar etapa/ciudad/tipo, sin resultados y restablecer; escritorio | **APROBADO** | Un resultado combinado, cero con búsqueda sin coincidencias y tres tras limpiar. [flows-additional.json](../../artifacts/qa/ui-responsive-crm/flows-additional.json). |
| Cancelar edición de la ficha QA; escritorio | **APROBADO** | La ciudad temporal se descartó y volvió `QA Ciudad`. [flows-additional.json](../../artifacts/qa/ui-responsive-crm/flows-additional.json). |
| Seleccionar programa en ficha compartida de Inbox, recargar y reseleccionar; móvil | **APROBADO** | Programa 100 conservado, sin teléfono ni alerts. [qa-inbox-persistence.json](../../artifacts/qa/ui-responsive-crm/qa-inbox-persistence.json). No se eligió un asesor distinto. |
| Cambiar estado de conversación y reconsultar; móvil | **APROBADO** tras relectura | Primer intento rechazado por conflicto de revisión, con alert visible. Después de releer y repetir, `En espera` persistió al recargar/reseleccionar. [Evidencia de esa persistencia](../../artifacts/qa/ui-responsive-crm/qa-inbox-state.json). La causa concreta del conflicto inicial no se determinó. Una comprobación posterior dejó el estado en Abierta, como se detalla abajo. |
| Crear borradores y Tab, 320×568 | **APROBADO** | Nombre visible, siguiente campo accesible y repetición explícita con comportamiento conservado. [focus-after.json](../../artifacts/qa/ui-responsive-crm/focus-after.json). |
| Abrir siete secciones de Agentes, 390×844 | **APROBADO** para navegación | Constructor, Etapas, Fuentes, Revisión, Simulador, Actividad y Supervisión sin alerts ni overflow. [agents-tabs-mobile.json](../../artifacts/qa/ui-responsive-crm/agents-tabs-mobile.json). No se ejecutó simulador, inferencia o aprobación. |
| Modal de credencial: abrir, recorrer, Escape y retorno, 320×568 | **APROBADO** para apertura/cancelación | Diálogo nativo 282×385 px dentro del viewport; foco Cerrar → entrada → Cancelar, con BODY transitorio entre vueltas del navegador, sin foco en controles del fondo. Escape cerró y devolvió foco a Agregar. Guardar cifrado deshabilitado con entrada vacía; no se guardó ninguna credencial. [DOM/foco](../../artifacts/qa/ui-responsive-crm/modal-keyboard.json), [captura](../../artifacts/qa/ui-responsive-crm/modal-api-320.png). No equivale a auditoría completa del foco con tecnologías asistivas. |
| Error de red y recuperación en Agentes, 390×844 | **APROBADO** | Offline solo de la pestaña de prueba, aviso traducido y recuperación con Actualizar tras restaurar. [network-final.json](../../artifacts/qa/ui-responsive-crm/network-final.json). |
| Selección de catálogos/búsqueda en Admisiones; tres tamaños base | **APROBADO** para lectura | Estado estable sin resultados QA, opciones reales y sin alerts. [admissions-read.json](../../artifacts/qa/ui-responsive-crm/admissions-read.json). |
| Ficha institucional, alta de aspirante o seguimiento institucional | **NO PROBADO** | No se creó/alteró un aspirante SIIE ni se ejercitó una ficha institucional real. La ficha CRM QA y su conversación son independientes. |
| Cambiar etapa CRM a una alternativa, asignar otro asesor | **NO PROBADO** | Solo estaba configurada la etapa Nuevo; no se cambió el catálogo para fabricar el caso. No se ejercitó otro responsable. |
| Página 2, ordenar y kanban/pipeline | **NO PROBADO** | Siguiente estaba deshabilitado con tres fichas; no se sembraron 31 registros. No hay evidencia de ordenación o interacción kanban en esta ejecución. |
| Submit inválido de nombre y luego etapa; Clientes 390×844 | **APROBADO** tras corregir | Nombre/teléfono vacíos: nombre recibe foco. Con nombre completado y etapa vacía: selector recibe foco, `aria-invalid=true`, `aria-describedby=client-stage-error` y mensaje visible. Nuevo después del error devuelve foco al nombre conservando el borrador; se canceló. Relectura confirmó un QA/tres contactos y que no se guardó el inválido. [Antes](../../artifacts/qa/ui-responsive-crm/validation.json), [después](../../artifacts/qa/ui-responsive-crm/validation-after.json), [regresión](../../artifacts/qa/ui-responsive-crm/validation-check.json). No se presentan como todos los errores/formatos posibles. |
| Validaciones de todos los campos, formatos y doble envío | **NO PROBADO** como cobertura completa | El caso obligatorio anterior y las regresiones de transporte 409/422 no sustituyen todos los casos de validación/duplicados por UI. |
| Inicio de sesión empresarial y roles | **NO APLICA** al entorno actual | Auth/RBAC institucional aún no implementados; no hay rol de prueba adicional aprobado. |
| Envíos, automatizaciones, inferencia y simulador de agentes | **NO PROBADO** | La QA no envió mensajes ni hizo llamadas a proveedores; no se activaron configuraciones para fabricar evidencia. |

La ficha permanece identificada como **`QA RESPONSIVE 20261021 Prueba de formulario y seguimiento de admisiones`**, sin teléfono. La creación corresponde a Contact + conversación vacía + operación CRM; el worker técnico existente puede preparar referencias. No se afirma ausencia absoluta de actividad automática. No hay eliminación UI/API disponible para esta ficha: no se usó SQL ni una ruta destructiva para limpiarla.

**Observación adicional, causa no confirmada:** una [lectura final local](../../artifacts/qa/ui-responsive-crm/qa-final-read.json) detectó la conversación QA en `mode: ai` y cero mensajes, sin que esta QA hubiera pulsado Reservar IA. No se reprodujo la transición ni se atribuye una causa ante la actividad concurrente; no se contabiliza como defecto corregido. Mediante Tomar control se restauró `human`, y otra lectura confirmó cero mensajes. Después se dejó el estado en **Abierta**, programa **100**, manteniendo control humano. [Investigación y estado final](../../artifacts/qa/ui-responsive-crm/qa-mode-investigation.json). La prueba anterior de persistencia de En espera sigue siendo válida para aquel momento; no describe el estado final del registro.

## Red y consola

La captura final registra **cero errores de consola y cero excepciones** en ese recorrido. Contiene cuatro `ERR_INTERNET_DISCONNECTED` esperados por la prueba offline y dos solicitudes canceladas al recargar. Tras restaurar conexión, `/api/v1/agents` y `/api/v1/agents/providers` respondieron 200. Este resultado no borra los fallos automatizados ni garantiza toda la sesión o todos los servicios. [Registro final](../../artifacts/qa/ui-responsive-crm/network-final.json).

## Comprobaciones automatizadas

La normalización de los archivos modificados se hizo antes de las comprobaciones que dependen de sus bytes. Las tres regresiones iniciales fallaron con el código anterior y pasaron después; las regresiones de red y validación también fallaron antes de cada corrección. Los checks amplios se ejecutaron una vez sobre un corte previo a los últimos parches de transporte y validación; el corte final tiene cinco pruebas focales y las verificaciones estáticas indicadas abajo. No se atribuye la evidencia global anterior a los bytes nuevos.

| Comando, desde `frontend` salvo indicación | Estado | Resultado y alcance |
|---|---|---|
| `npm exec -- vitest run src/test/responsiveActions.test.tsx src/test/agentsTransport.test.ts` | **APROBADO** | Dos archivos, cinco pruebas finales. Mocks/sintéticos; no sustituyen Ego ni persistencia real. |
| `npm exec -- prettier --check src/modules/agents/api.ts src/test/agentsTransport.test.ts src/modules/agents/AgentsPanel.tsx src/modules/clients/pages/Clients.tsx src/features/Overview.tsx src/test/responsiveActions.test.tsx`; después, `npm exec -- prettier --check src/modules/clients/pages/Clients.tsx src/modules/clients/components/ClientFields.tsx src/test/responsiveActions.test.tsx` | **APROBADO** | Seis archivos del corte anterior; las tres fuentes/prueba de validación se comprobaron tras normalizar. |
| `npm exec -- eslint src/modules/agents/api.ts src/test/agentsTransport.test.ts`; pasada focal previa de los otros cuatro archivos; después `npm exec -- eslint src/modules/clients/pages/Clients.tsx src/modules/clients/components/ClientFields.tsx src/test/responsiveActions.test.tsx` | **APROBADO** | Archivos del parche sin errores; se comprobó el corte final de validación. |
| `impeccable detect --json frontend/src/modules/agents/AgentsPanel.tsx frontend/src/modules/clients/pages/Clients.tsx frontend/src/features/Overview.tsx`, desde raíz | **APROBADO** | Cero hallazgos en ese corte; no acredita accesibilidad completa. |
| `npm.cmd run build` | **FALLIDO** | Seis diagnósticos TypeScript; Vite no llegó a empaquetar. Valores sin uso en Settings/Inbox y mocks desactualizados de InboxDetail/MessagePage/SLA, fuera de las fuentes corregidas. Es el corte global anterior a los últimos parches, no un build final. |
| `npm.cmd run format:check` | **FALLIDO** | 17 archivos no conformes fuera del parche; origen completo no confirmado. |
| `npm.cmd run lint` | **FALLIDO** | 11 errores y tres avisos en siete archivos; no reportó las fuentes del parche. No hay baseline global previo suficiente para atribuirlos todos. |
| `npm.cmd test` | **FALLIDO** | 218 pruebas: 170 pasan, 48 fallan; 16 archivos pasan y 18 fallan; 14 errores no manejados. |
| `git diff --check` sobre archivos del parche, desde raíz | **APROBADO** | Comprobación de whitespace; no es revisión funcional. |

[Resumen global y límites de atribución](../../artifacts/qa/ui-responsive-crm/checks.json), [checks del helper de red](../../artifacts/qa/ui-responsive-crm/error-handling-check.json), [checks finales de validación](../../artifacts/qa/ui-responsive-crm/validation-check.json), [logs locales](../../.local/ui-responsive-crm-20261021/checks). Hay clases de fallo ya documentadas, pero **no se califican los 48 fallos como heredados**: no existe una ejecución global completa anterior a todos los cambios que permita esa conclusión. No se corrigieron fallos ajenos ni se alteraron pruebas para ocultarlos; el frontend no tiene gate global verde.

## Bloqueos y comprobaciones siguientes

| Pendiente | Estado | Siguiente comprobación concreta |
|---|---|---|
| Zoom de navegador real al 200 % | **BLOQUEADO** | `Control+Equal` cinco veces no cambió viewport, DPR ni escala en el runtime de Ego. Repetir con una capacidad que controle el zoom real; no sustituir por pinch, redimensionar imagen o escalado DOM. [zoom.json](../../artifacts/qa/ui-responsive-crm/zoom.json), [captura](../../artifacts/qa/ui-responsive-crm/zoom-keyboard.png). |
| Safari/iOS, Android y tablet físicos, otros navegadores | **NO PROBADO** | Ejecutar creación, ficha, selectores, modal y navegación en dispositivos/navegadores reales. |
| Teclado virtual, gestos físicos y lector de pantalla | **NO PROBADO** | Revisar campos/modal con teclado abierto, scroll/foco y lectura de errores. No se declara cumplimiento WCAG completo. |
| Suite, lint, formato y build globales | **FALLIDO** | Clasificar y corregir por separado los diagnósticos registrados; volver a comprobar el árbol final tras esas correcciones. |
| Paginación con más datos y etapa alternativa | **NO PROBADO** | Usar conjunto local de prueba autorizado y catálogo apropiado; comprobar página 2 y transición sin tocar configuración real para la QA. |
| Auth/RBAC y ficha institucional/seguimiento conectado | **NO PROBADO** | Preparar entorno, roles y datos de prueba específicos, con autorización de cualquier escritura institucional. |

Esta entrega queda en desarrollo y es revisable. No hubo commit, push, PR, despliegue, DDL, consulta SQL directa, credenciales guardadas ni mensajes a prospectos desde la QA. Las funciones de proveedor/canal requieren su propia aceptación; la apertura de sus pantallas no las acredita.
