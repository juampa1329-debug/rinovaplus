# V0/V1 — Brief visual, auditoría y contrato de datos

**Fecha:** 2026-10-14 · **Rama:** `codex/disenos-ui` · **Alcance autorizado:** completar las fases visuales V0 y V1 del [roadmap UX/UI](../ux-ui-roadmap.md), preservando todas las funciones actuales. No son las fases funcionales 0/1 del proyecto.

**Estado:** V0/V1 completadas al **100 % de sus alcances de definición y auditoría**. Integridad frontend comprobada en el snapshot de cierre; cambios backend concurrentes atribuidos a otro chat y preservados. No se certifica ausencia global de regresiones de ese trabajo independiente. No significa diseño final ni gráficas implementadas. V2 no se inició.

## 1. V0: brief resuelto

| Aspecto | Base confirmada / decisión de esta unidad |
|---|---|
| Solicitud | Estética moderna inspirada en las tres referencias recibidas, gráficas animadas en entrada/salida y modos claro/oscuro. El propietario pidió empezar por V0/V1 y preservar lo que ya funciona. |
| Público y tarea | CRM de admisiones/relacionamiento según README y documentación existente: operador que consulta fichas, atiende hilos y comprende el siguiente paso; formulario público del aspirante. No hubo entrevista de usuarios finales; frecuencia/volumen real aún no medidos. |
| Modo de experiencia | Operate: datos y acciones reconocibles, lectura rápida y continuidad de contexto. Las gráficas acompañan el trabajo; no retrasan su disponibilidad. |
| Piloto previsto | Resumen e Inbox, claro/oscuro y adaptación móvil. Posterior extensión a componentes/rutas actuales, sin inventar módulos operativos. |
| R1 | Dashboard amplio: superficies neutras, paneles redondeados, jerarquía de cifras, barras y circular. Adaptar a indicadores de admisiones; no copiar ingresos o paneles que tapen datos. |
| R2 | Dashboard pastel: navegación compacta, accesos agrupados y dona. Adoptar orden/agrupación; no incorporar calendario, subida de archivos o servicios ajenos. |
| R3 | CRM compacto: indicadores, gráfica principal, tabla e inbox. Adoptar relación dato → acción y densidad legible; no copiar contactos, fotos, conversiones o mapas. |
| Movimiento | Entrada, actualización y salida propuestas en la matriz del roadmap; imágenes estáticas no acreditan animaciones observadas. Valores finales inmediatos, última interacción gana, movimiento reducido instantáneo. |
| Identidad | Verde institucional existente; explorar lila/violeta como acento de las referencias en V2. Marca oficial, tokens exactos, composición final e idioma definitivo siguen sus pendientes; no bloquean cerrar este brief. |
| Límites | Sin nuevos datos reales, API/DB, identidad, envío, persistencia de negocio, dependencias, publicación o modificación de otros worktrees. Capturas personales no copiadas al repositorio. |

**Resultado de V0:** requisitos, referencias y límites trazados. No se solicita repetir ejemplos ni aprobar valores CSS en esta fase. Las decisiones de tokens pertenecen a V2, composición a V3 y su ejecución a los cortes autorizados posteriores.

## 2. Inventario V1 y mapa de estado

Se inspeccionaron [App.tsx](../../frontend/src/App.tsx), [navigation.ts](../../frontend/src/shared/navigation.ts), [Clients.tsx](../../frontend/src/modules/clients/pages/Clients.tsx), [Inbox.tsx](../../frontend/src/modules/inbox/pages/Inbox.tsx), [demo.ts](../../frontend/src/shared/demo.ts), [crm.ts](../../frontend/src/shared/crm.ts) y [workflow.ts](../../frontend/src/shared/workflow.ts). Se conserva el inventario de trece rutas del roadmap: doce módulos y la referencia Creadores.

| Grupo actual | Rutas | Tratamiento de UX |
|---|---|---|
| Operación | Resumen, Clientes, Inbox, Formulario, Revisión académica | Priorizar las tareas existentes; Revisión sigue rotulada como futura. |
| Gestión | Asistente, Conocimiento, Memoria, Ajustes, Acceso | Preservar configuración y límites de capacidades no conectadas. |
| Expansión | Retención, Corporativo, Creadores | Menor protagonismo para el trabajo habitual; conservar acceso y señalización de futuro/referencia. |

**Propiedad de estado comprobada en código:** App conserva clientes, hilos, configuración, selección de hilo y borradores de Ajustes. El contenedor `key={route-revision}` (App, línea 256) remonta cada feature al cambiar de ruta. Inbox guarda filtros, ficha abierta y borradores por cliente en estado propio (líneas 56–77); Clientes guarda selección/filtros/borrador de edición en su feature (líneas 45–58). La preferencia visual tiene persistencia separada; esto no hace persistentes los datos de negocio.

Por tanto, **no se promete conservar borradores de Inbox entre rutas**: hoy se pierden al desmontar la feature. Dentro de Inbox, cambiar de hilo conserva los borradores manuales por `clientId`; los derivados de plantilla pueden invalidarse si cambia su binding. Cambiar de cliente en Clientes descarta la edición sin guardar (`setDraft(null)`, líneas 149–153). Estos comportamientos previos se registran como base, no como regresiones introducidas aquí.

## 3. Tres recorridos de referencia

Los pasos siguientes definen el flujo y los puntos de aceptación; el resultado observado se registra en la sección 8. No ejecutar envío real, restablecer la pestaña del propietario o editar datos personales para comprobarlos.

| Flujo | Pasos concretos | Selección, foco y resultado que se comprueban |
|---|---|---|
| F1 — Resumen → hilo → ficha | En Resumen abrir el primer hilo; identificar contacto/canal; ocultar y mostrar ficha CRM; abrir su ficha de Clientes. | App fija `selectedThread` antes de navegar (líneas 262–263); cambio de título enfoca encabezado (líneas 43–46). Ocultar/mostrar contexto no cambia cliente. Clientes recibe `initialSelected` desde la selección de App (línea 274). |
| F2 — Filtro → sin coincidencias → recuperación | En Inbox usar una búsqueda ficticia que no coincida; observar mensaje vacío y control de recuperación; restablecer filtros y volver a los cuatro hilos. | `visible` combina búsqueda, canal, vista rápida y estado (Inbox, líneas 78–89). Filtrar no cambia `selectedId`: el hilo puede seguir visible sin estar en la lista filtrada. Restablecer pone cuatro filtros en su base; el usuario mantiene el control de foco. |
| F3 — Clientes → edición local → hilo compartido | Desde la ficha de A abrir Clientes; seleccionar Persona Demo B, cambiar una nota ficticia y guardar localmente; abrir su Inbox y comprobar contacto/nota. Volver a A para comprobar límite de borrador entre rutas. | `onInbox(client.id)` comparte selección (Clients, línea 340; App, líneas 276–279). B inicia en modo humano. Guardar actualiza la ficha en App; navegación enfoca encabezado. Borradores manuales por hilo se comprueban dentro de F1; salir de la ruta los desmonta: límite conocido. |

**Criterio de éxito del recorrido:** llegar al objeto correcto, conservar el estado que el código ya conserva y tener recuperación comprensible; no convertir persistencia nueva, autoscroll, animación o guardado automático en requisito ya implementado.

## 4. Contrato preciso de métricas

**Comprobación actual:** módulos TypeScript existentes cargados mediante transpilación en memoria con el compilador ya instalado; sin build, instalación ni cambio de fuente. Se ejecutaron assertions de sumas sobre `seedClients()`, `seedThreads()`, `seedCrmConfig()` y `workflowOf()`. Resultado saneado en `.local/ui-v0-v1-evidence/data-contract-check.json`.

| ID estable propuesto / presentación | Definición, universo e identidad | Resultado inicial comprobado | Ausencia, filtro y recálculo previstos |
|---|---|---|---|
| `clients.total` / indicador | Longitud de clientes locales; identidad `Client.id`, no número de matrícula. | **4**. | Vacío válido → 0. Colección ausente/error → no disponible, no 0. Recalcular tras guardar/crear o reset local. |
| `clients.by-stage` / barras | Una categoría por `CrmConfig.stages.key`; asociación actual por igualdad de `Client.stage` con etiqueta configurada, ya que el campo almacena texto. | `nuevo:1`, `contactado:1`, `interes:1`, `solicitud:1`; desconocidos 0; suma **4**. | Orden configurado estable; incluir categorías 0. Etiqueta sin correspondencia/vacía → `unmapped`, sin descartar ficha. No normalizar silenciosamente dos categorías distintas; resolver contratos antes de cambiar datos. |
| `threads.by-state` / dona | Un estado operativo exclusivo por `clientId`, obtenido mediante `workflowOf(thread)`. | Abierta **4**, En espera **0**, Cerrada **0**; suma **4**. | Sin workflow aplica default vigente, no null: Abierta/Normal/Sin asignar, tareas/eventos vacíos. Estado inválido futuro → dato no válido explícito; no forzarlo a Abierta. |
| `threads.unread` / indicador | Hilos con `unread === true`, no cantidad de mensajes sin leer. | **2**: demo-1 y demo-3. | No confundir false con propiedad ausente. Recalcular al marcar leído, sustituir hilos o reset; ningún porcentaje si falta universo. |
| `threads.by-channel` / barras | Un canal por hilo local; clave literal de los cuatro canales del modelo. | WhatsApp **1**, Facebook **1**, Instagram **1**, TikTok **1**; suma **4**. | Desconocido → categoría explícita/no disponible según contrato futuro. No equivale a personas únicas omnicanal ni canales conectados. |
| `tasks.pending` / indicador opcional | Suma de tareas de cada workflow con estado Pendiente; identidad compuesta `clientId/task.id`. | **0**. | Colección válida vacía → 0. Recalcular al crear/completar/cancelar; no es alerta programada, vencimiento o SLA. |
| `admissions.timeline` / línea ilustrativa futura | No existen timestamps de alta en Client ni de mensaje en Message; eventos de workflow contienen hora pero no son altas de admisiones. | **No disponible**; eventos seed **0**. | Sin línea operativa ni tendencia inventada. Dataset sintético aislado solo para prototipo autorizado y claramente rotulado; rango/zona/unidad definidos antes de generar puntos. |
| `conversion`, `revenue`, `growth`, `response-time` / diferidos | Faltan cohorte/denominador, transacciones o pares de eventos válidos. `probability` de etapa es configuración; `wait.minutes` es demo. | **No disponible**. | No convertir configuración/espera sintética en probabilidad calibrada, ingresos o rendimiento; sin porcentajes/flechas de crecimiento. |

**Pruebas aritméticas ejecutadas:** etapas conocidas + desconocidas = clientes; estados = hilos; canales = hilos. Las tres igualdades pasan con los valores iniciales. El cálculo no prueba un gráfico implementado, integración, datos reales o deduplicación omnicanal.

**Universo/filtros del piloto propuesto:** Resumen usará el conjunto local completo, explicitado como demo; no heredará silenciosamente filtros transitorios de otra ruta. Una eventual gráfica dentro de Inbox compartirá exactamente `visible` y su título indicará filtros activos. Los indicadores del conjunto total no se mezclarán visualmente con subtotales filtrados sin etiqueta.

**Búsqueda y estado actuales:** Inbox busca nombre/teléfono/último mensaje con trim y minúsculas locales; luego combina canal, vista rápida y estado mediante AND. Vistas rápidas usan `matchesQuickView` (workflow, línea 142): Sin leer, Humano, IA, Míos asignado a Operador Demo y Sin asignar. Clientes combina su búsqueda/etapa con filtro de etiqueta. No se añade un filtro temporal donde no existe fuente temporal.

**Integridad futura:** IDs de fichas/hilos duplicados, valores no finitos y categorías ilegales se tratarán como datos inválidos; no deduplicar, rellenar o descartar silenciosamente. No se cambia ahora la validación vigente. Textos finales, tabla equivalente y suma de categorías deberán coincidir antes/durante/después de la animación.

## 5. Casos de diseño preparados, no implementados

| Caso sintético | Resultado que deberá diseñarse/comprobarse en el corte correspondiente |
|---|---|
| Búsqueda sin coincidencias | Lista vacía con restablecer; distinguirla del hilo seleccionado que puede seguir visible. Este estado sí existe en la demo actual. |
| Colección sin registros | Contador 0 y mensaje útil; sin dona al 100 %. No se afirma soporte global actual: Clientes inicializa con `clients[0].id` (línea 49), por lo que vaciar toda la fuente necesita revisión antes de habilitar ese caso. |
| Categoría con 0 registros | Etiqueta conservada y barra nula; la tabla contiene 0, sin confundirlo con error o ausencia. |
| Etapa no reconocida | Categoría sin correspondencia que preserva conteo total; no reasignar etapas de negocio por estética. |
| Nombre largo / varias etiquetas | Ajuste de línea o truncado con acceso al valor completo; acción e identidad siguen reconocibles; no cambiar fixture actual. |
| Distribución desigual | Una categoría dominante y varias pequeñas: leyenda/tabla siguen legibles; no inflar segmentos mínimos para aparentar valores. |
| Cien categorías o mensajes extensos | Desbordamiento y densidad revisados antes de elegir el gráfico; no convertir todos los puntos en paradas Tab. Volumen no probado en esta unidad. |
| Serie temporal ilustrativa | Fuente separada con rótulo permanente, periodos/unidad coherentes y sin mezclarla con conteos actuales. No se genera dataset en V1. |
| Actualización repetida / salida durante entrada | Última interacción gana; cifras finales inmediatas, capa saliente no interactiva y estado reducido instantáneo. Es criterio de V4, no capacidad actual. |

## 6. Backlog priorizado y clasificación

| ID / prioridad | Hallazgo y clase | Trabajo siguiente / aceptación |
|---|---|---|
| UX-01 / P0 | Trece entradas y navegación con scroll independiente; oportunidad de jerarquía, no defecto funcional probado. | V2/V3: priorizar operación, compactar expansiones y asegurar nombres/teclado accesibles. |
| UX-02 / P0 | Cola alta y recorrido compiten en Resumen; oportunidad de densidad. | V3: contexto breve y acción clara, indicadores útiles sin ocultar cola; comparar con fixtures idénticos. |
| UX-03 / P0 | No hay contrato temporal para tendencias/tasas; restricción de datos comprobada. | V3/V4: barras/dona honestas; historial no disponible o serie ilustrativa separada. |
| UX-04 / P0 | Borradores/filtros viven en Inbox y se desmontan al cambiar ruta; comportamiento existente. | V2/V3: expresar continuidad esperada; cualquier persistencia adicional es cambio funcional separado, no ajuste visual implícito. |
| UX-05 / P1 | Avisos de demo repetidos; oportunidad de simplificación sin perder transparencia. | V3: aviso estable breve y detalles junto a acciones que puedan confundirse con operación real. |
| UX-06 / P1 | Filtros apilados antes de la lista; oportunidad de espacio. | V3: agrupar secundarios y mostrar resumen de activos; conservar combinación/restablecimiento actual. |
| UX-07 / P1 | Tokens y estados compartidos incompletos para nuevas gráficas; deuda de diseño prevista. | V2: roles de tipografía, serie, movimiento y variaciones accesibles; mantener fuente única. |
| UX-08 / P1 | Clientes asume primera ficha al inicializar; riesgo de fuente para caso vacío completo, identificado en código y no provocado. | Antes de habilitar dataset vacío: definir aceptación y autorizar cambio acotado; no introducirlo incidentalmente en rediseño. |

No se encontró ni se corrige aquí una regresión causada por esta unidad: no cambia código. Las oportunidades anteriores no se presentan como fallos de producción.

## 7. Protección de lo que ya funciona

| Invariante a conservar | Prueba focalizada para una futura modificación |
|---|---|
| Identidad compartida Clientes/Inbox, guardado en memoria y cancelación explícita | F1/F3; editar/guardar/cancelar ficha y comprobar que otro contacto no recibe esos cambios. |
| Borradores por hilo y separación de Mensajes/Comentarios; binding de plantilla invalida contexto obsoleto | Alternar hilos/modos y revisar plantilla; comprobar límites actuales de desmontaje sin prometer persistencia nueva. |
| Hilo cerrado o sin control humano bloquea añadir mensaje | Pruebas funcionales existentes pertinentes más navegador del flujo afectado; ningún estilo habilita una operación bloqueada. |
| Estado/asignación/prioridad, tareas y timeline locales | Mantener acciones/validaciones y contar datos sin mutar el dominio desde una gráfica. |
| Configuración única Asistente/IA y siete secciones de Ajustes | Guardar/descartar/revisar; una variante visual no crea otro estado independiente o activa proveedor. |
| Claro/Oscuro/Sistema, foco y reducción de movimiento | Cambiar tema/recargar en entorno de prueba; preservación de preferencia y fallback; comprobar teclado sin flash/robo de foco. |
| Formulario y otros worktrees independientes | No copiar la versión antigua sobre fase 4; acordar integración de cambios compartidos antes de editar su flujo. |

**Método de reversibilidad:** trabajar por componente/pantalla en la rama asignada; conservar snapshot de archivos antes de cada futuro corte; no usar reset/clean/checkout para deshacer trabajo mixto. Revertir únicamente cambios de esa unidad contra su snapshot, respetando ediciones concurrentes. Gráficas derivan datos y no escriben en fichas/hilos; ningún cambio visual toca contratos SQL/API.

**Freeze de esta unidad:** 51 archivos SHA-256 (41 frontend, 10 backend) antes de editar documentos; incluyen source, manifiestos y configuración, excluyendo dependencias, builds y caches. `source-before.json`, `git-before.json` y copias de los tres documentos anteriores están en `.local/ui-v0-v1-evidence/`. Rama inicial `codex/disenos-ui`, HEAD `14d818a123118914990dc8951738ae3b8bf38bd7`, índice vacío; cambios no confirmados previos preservados.

## 8. Evidencia, checklist y límites

El coordinador ejecutó el pase en **una pestaña nueva de prueba**, con fixtures de esta rama, escritorio en tema oscuro y viewport por defecto. No restableció la pestaña del propietario ni cambió su tema. Al terminar cerró la pestaña de prueba, descartando sus ediciones temporales; la original continuó en Resumen oscuro con 4 fichas y 2 hilos sin leer.

| Recorrido observado | Evidencia y resultado |
|---|---|
| F1 | Resumen → Abrir hilo A selecciona A; foco en contenedor de encabezado «Conversaciones». Tomar control local, escribir borrador ficticio, ocultar/mostrar ficha conserva texto y foco del botón. Cambiar A → B muestra borrador vacío; volver A conserva su texto. |
| F2 | Buscar `V1-sin-coincidencias-xyz` produce lista 0, conserva hilo A/borrador. Restablecer devuelve 4 hilos, búsqueda vacía y foco en Restablecer. Sin leer devuelve 2; combinado con TikTok devuelve 0; restablecer devuelve 4. |
| F3 | Ver Clientes selecciona A y enfoca encabezado; seleccionar B, editar solo nota ficticia y Guardar ficha local produce aviso de memoria temporal. Abrir Inbox selecciona B y muestra la nota compartida. Volver A después de cambiar de ruta deja borrador vacío: límite previo confirmado. |

Logs consultados: errores/advertencias `[]`. No se pulsó enviar/añadir mensaje, ni se realizaron operaciones DB/API. Evidencia ignorada de Git: `browser-observations.json`, `inbox-no-results.jpg`, `inbox-draft-preserved.jpg`, `clients-inbox-shared-context.jpg` y `original-preview-preserved.jpg`, bajo `.local/ui-v0-v1-evidence/`.

- [x] Tres referencias vinculadas a decisiones/antiobjetivos y brief V0 delimitado.
- [x] Trece rutas, propiedad de estado y tres recorridos V1 definidos desde código.
- [x] Métricas con fuente/ID/universo/fallback; sumas comprobadas en fixtures actuales.
- [x] Casos sintéticos preparados como aceptación futura, sin implementarlos.
- [x] Backlog clasificado y matriz de preservación/reversibilidad definidos.
- [x] Tres recorridos observados y evidencia de foco/selección incorporada.
- [x] Frontend 41/41 hashes intactos, rama/HEAD/índice iguales y enlaces documentales comprobados; detalle en `closure.json` local.
- [x] Cambio concurrente atribuido por el coordinador mediante lectura del chat correspondiente; no se restauraron ni modificaron sus archivos.

**Diferencia concurrente atribuida:** snapshot del 2026-10-14 a las **13:26:15 -05:00**: frontend 41/41 intacto; de los 10 archivos backend congelados, 9 conservaron hash y `app/main.py` cambió; aparecieron `ai_models.py`, `ai_providers.py`, `ai_routes.py` y `ai_service.py`. El coordinador comprobó mediante `list_threads`/`read_thread` que el nuevo chat **«Implementa proveedores de IA en los,»**, ID `01a13ba4-e7eb-7eb0-a4df-3bad5c448e8e`, trabaja en esta misma carpeta con autorización del propietario para proveedores IA. Los otros dos chats originales conservan sus worktrees. No se afirma 51/51 intactos ni se certifica esa integración desde el rediseño; sus cambios permanecen íntegros. La comparación parte de archivos reales anteriores, no de un árbol limpio supuesto.

**Condición antes de editar UI:** resolver el checkout compartido con ese nuevo chat y refrescar hashes/evidencia de rutas tocadas, pues informó que continuaría hacia frontend. Este cierre documenta un snapshot y no persigue ni sobrescribe cambios posteriores de otra tarea. No se migró ni se envió mensaje a ese chat desde esta unidad.

Los 64 tests del corte previo siguen siendo evidencia histórica en [A-018/A-021](../progress.md); no se reejecutó la suite ni un build aquí. La prueba de agregaciones y el pase acotado de navegador no equivalen a regresión exhaustiva, conformidad de accesibilidad, dispositivo físico, API/DB o producción. V2 y las fases de implementación no se inician con este informe.
