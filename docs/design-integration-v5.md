# V5 — Resumen e Inbox integrados en la aplicación local

**2026-10-14 · Alcance autorizado:** el propietario aceptó V4 y solicitó integrar composición, temas y movimiento en la aplicación existente, conservando funciones y borradores. Se implementa en `codex/disenos-ui`; [V3](design-pilot-v3.md) y [V4](design-motion-v4.md) permanecen como referencias independientes. No se modifica backend, ajustes IA, proveedores, conexiones, otros worktrees o publicaciones Git.

## Resultado y recorrido

Abrir `http://127.0.0.1:5173/#/overview`. Resumen muestra los contactos, hilos sin leer, tareas pendientes y conversaciones abiertas de la pestaña. Las barras usan las etapas configuradas en Clientes; la dona usa los estados operativos de los hilos. **Abrir hilo** conserva la selección compartida con Clientes e Inbox.

En Inbox, búsqueda y vista rápida permanecen accesibles; **Más filtros** contiene canal y estado. Se conservan mensajes, comentarios, control humano, lectura, estado/responsable/prioridad, mini CRM, campos configurados, tareas, timeline y plantilla con revisión humana. **Mostrar ficha CRM / Cerrar ficha** abre y cierra contexto, con retorno de foco. En móvil, **Volver a la bandeja** permite elegir otro hilo; el contexto ocupa su propia vista.

Los trece destinos siguen en navegación: Resumen e Inbox directos y el resto mediante **Otros módulos**. Las siete secciones de Ajustes mantienen sus controles y comportamiento. No se copian los escenarios, filtros gráficos, reproducción lenta, diagnóstico ni botón de repetir del prototipo como funciones de negocio.

## Propiedad de estado y conservación de borradores

El nuevo `InboxSessionProvider` se monta en App por encima de las rutas. Conserva únicamente estado efímero de Inbox: borradores manuales por hilo, comentarios por ID, títulos/fechas de tareas por hilo y selección/modo/filtros de la bandeja. No mantiene páginas completas ocultas ni añade almacenamiento de datos personales.

| Antes | Después | Motivo |
|---|---|---|
| Cambiar de ruta desmontaba los borradores de Inbox. | Navegar a Resumen, Clientes u otra ruta conserva los borradores en la pestaña. | Mejora funcional autorizada expresamente para V5. |
| Cerrar contexto o cambiar de hilo desmontaba el formulario de tarea sin guardar. | Título y fecha se conservan por hilo; guardar tarea limpia únicamente su borrador. | El contexto progresivo no debe descartar trabajo. |
| Mensajes y comentarios guardaban su estado en componentes de ruta. | El propietario del estado está sobre las rutas; los componentes siguen desmontándose. | Retención acotada sin duplicar pantallas, IDs o listeners. |
| Plantillas derivadas dependen de un binding de contexto/configuración. | Se conserva el mismo binding y su invalidación; un borrador derivado obsoleto no se reutiliza como manual. | Mantener revisión humana y evitar respuestas fuera de contexto. |
| Recargar o confirmar Restablecer demo descarta datos temporales. | Igual: el restablecimiento remonta el propietario; cancelar conserva todo. | No inventar persistencia ni modificar ajustes IA guardados. |

La UI explica este límite junto al compositor. Solo la preferencia Claro/Oscuro/Sistema conserva su persistencia previa. La mejora no cambia la edición sin guardar de Clientes ni otros formularios fuera de Inbox; ampliar su ciclo de vida requiere un alcance propio.

## Datos y gráficas

`shared/overview.ts` deriva las cifras del estado real de la demo, sin nuevos fixtures ni endpoints. Se muestran las etapas configuradas aunque tengan cero; los valores no reconocidos se agrupan en **Sin correspondencia**, conservando la suma de clientes. La categoría desconocida no modifica fichas ni configuración. Las tareas cuentan solo estado Pendiente; la dona usa Abierta/En espera/Cerrada mediante `workflowOf`, respetando el fallback anterior de hilos sin workflow.

Cada barra indica cantidad sobre el total de fichas; los estados suman todos los hilos, independientemente de filtros de Inbox. Las etiquetas y listas de definición ofrecen los valores finales accesibles desde el primer render; colores y hover no son la única fuente. El vacío muestra cero y explica ausencia de proporciones. No se muestran ingresos, tasas de conversión, variaciones históricas o tiempos sin contrato/fuente.

## Movimiento y apariencia

Se reutiliza Web Animations API sin dependencias nuevas: entrada **250 ms**, actualización **200 ms**, salida **150 ms**, con curvas V4 `--ease-out` y `--ease-in-out`. Las marcas usan máscara/opacidad; no se animan dimensiones de layout ni números. Una actualización interrumpida captura la máscara computada antes de cancelar. Los valores del texto son inmediatos.

El contenedor React de gráficas conserva una salida visual breve al navegar: posición fija, `inert`, `aria-hidden` y sin interacción de puntero. No hay clon del DOM, IDs duplicados o espera de navegación. Reentrada cancela la salida; finalización/cancelación, desmontaje, pestaña oculta, teclado y preferencia reducida limpian los efectos. StrictMode tiene limpieza explícita. El sistema reducido y acciones de teclado usan estado final instantáneo. Cambiar tema no reinicia marcas.

La actualización de proporciones de la dona cambia la geometría final inmediatamente: con valores presentes, máscara y opacidad permanecen completas y no se atribuye una interpolación visible a esa actualización. La dona conserva la entrada y salida comprobadas; no gira segmentos ni interpola una métrica ficticia. Las barras sí actualizan la máscara entre valores. Es una adaptación acotada del prototipo a cambios operativos reales.

Los roles V2 se adoptan desde `tokens.css` con alcance `.pilot-shell` para Resumen/Inbox y su shell. El resto de módulos mantiene su paleta/composición previa hasta V6. `pilot.css` resuelve composición responsive y utilidades Tailwind existentes resuelven la rejilla de indicadores. Las transiciones de tema especifican color/fondo/borde; no hay `transition: all`. No se sustituye la marca ni se cierra la aprobación global P-003/P-015.

## Evidencia

La línea base `npm run check` aprobó **69 pruebas en 8 archivos**, formato, lint, tipos y build. Copias previas y hashes se conservaron en `.local/ui-v5-evidence/before/` y `source-before.json`, incluyendo los cambios no confirmados que ya existían. No se usa `HEAD` como sustituto del estado de trabajo.

| Capa | Resultado final | Evidencia y límite |
|---|---|---|
| Código normalizado | **74/74 pruebas en 9 archivos**, formato, lint, TypeScript y build aprobados. | `.local/ui-v5-evidence/final-check.log`. Incluye las 69 pruebas previas y cinco de V5; no se retiraron aserciones funcionales. |
| Pruebas específicas | Borradores separados por hilo/comentario/tarea, rutas/tema/contexto, restablecimiento, intención explícita de abrir hilo, categorías configuradas/desconocidas y tareas/estados. | `frontend/src/test/visualPilot.test.tsx`. Movimiento con WAAPI simulada: salida inerte, reentrada/cancelación, teclado/reducción y limpieza StrictMode. |
| Preservación independiente | **53/53 archivos protegidos exactos**; nueve archivos previos cambiados intencionalmente y seis nuevos de V5. Índice Git vacío. | `independent-verification.md`, `independent-preservation.json`. Snapshot normalizado: 60 rutas únicas, 51 intactas; se suman lockfile contrastado con V4 y ajustes IA. Los 13 duplicados de separador no inflan el conteo. |
| Navegador | **12 combinaciones** Resumen/Inbox × claro/oscuro × 390/768/1440 px, sin overflow horizontal del documento. | `browser-verification.json`, captura `v5-final.png`. Anchos útiles 375/753/1425 px. No teléfono físico. |
| Recorridos | Mensajes A/B separados; comentario A y tarea B conservados entre rutas/tema; ficha móvil cierra con retorno de foco y borrador, y permite volver a bandeja. | Confirmado por el coordinador en la app real local. Añadir tarea B da indicador 1; cambiar B a En espera da estados 3/1/0 y abiertas 3. |
| Reinicio y apertura | Cancelar restablecimiento conserva; confirmar limpia; recargar limpia borradores y conserva tema. Abrir hilo B desde Comentarios abre Mensajes de B. | Sin envío, DB o persistencia de borradores añadidos. |
| Movimiento y consola | Entrada de puntero observada en máscara/opacidad hasta estado final; salida brevemente visible, inerte y después oculta. Enter produce entrada/salida inmediatas. Consola final sin errores. | Pase limpio después de recarga final; hubo errores HMR transitorios mientras se editaba. Preferencia reducida probada automáticamente, sin cambiar el SO. |
| Otras rutas y documentos | Smoke de Clientes, Formulario y Creadores; 165 enlaces locales resueltos en seis documentos y `git diff --check` aprobado. | El smoke no certifica regresión exhaustiva ni toda la app; `docs-check.json`. |

El build pasa de CSS 24,89 kB / JS 312,23 kB a CSS 35,87 kB / JS 320,97 kB; comprimidos, CSS 5,66→7,88 kB y JS 95,54→98,48 kB. No se añaden paquetes. Es tamaño de artefactos, no medición de FPS, CPU o tiempos de render. Las pruebas jsdom no acreditan interpolación visual, tamaño físico, lector de pantalla ni operaciones reales; el build no acredita producción. Zoom 200 %, lector de pantalla, dispositivo físico y rendimiento ampliado quedan para V7.

Los primeros checks detectaron aserciones ligadas a la navegación anterior, una consulta de texto ambigua al existir la gráfica oculta y un `@reference` CSS innecesario. Se corrigieron los selectores/aperturas de disclosure y se retiró la directiva sin uso; se mantuvieron las aserciones de comportamiento. La intención explícita de apertura de hilo y limpieza StrictMode recibieron pruebas antes del freeze. No hubo correcciones de producto posteriores al pase final de navegador.

## Continuación

V5 cubre exclusivamente Resumen/Inbox y el shell necesario. V6 requiere autorización para extender la composición a Clientes, Asistente/Ajustes y demás módulos, coordinando sus worktrees. V7 conserva evaluación de accesibilidad más amplia, dispositivo físico, rendimiento y aceptación final por pantalla. No se ejecutan implícitamente esas fases.
