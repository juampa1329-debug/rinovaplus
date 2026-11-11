# Roadmap UX/UI: dashboard moderno, gráficas animadas y claridad operativa

**Fecha:** 2026-10-14 · **Rama:** `codex/disenos-ui` · **Estado:** V0/V1 completadas en definición/auditoría; [informe del snapshot](reports/ui-v0-v1-baseline.md). V2–V5 aceptadas para el piloto; [V5 integrada](design-integration-v5.md) y [V6 implementada localmente](design-extension-v6.md) en Clientes, Asistente y Ajustes. Corte V6 comprobado: 80 pruebas y 24 combinaciones de navegador; extensiones restantes y V7/aceptación global pendientes. Chat de proveedores IA separado.

El propietario eligió como referencia dashboards claros, redondeados, con métricas legibles y gráficas protagonistas, y pidió animaciones de entrada y salida. Se propone llevar ese lenguaje a **Resumen e Inbox**, con variantes clara y oscura, sin dificultar encontrar una conversación, comprender su estado y ejecutar el siguiente paso. Las gráficas tendrán entrada, actualización y salida explícitas; sus cifras y controles estarán disponibles inmediatamente.

Este documento complementa el [roadmap funcional](roadmap.md), el [sistema de diseño](design-system.md) y [DESIGN.md](../DESIGN.md). No modifica fases de negocio, contratos ni autorizaciones. P-003/P-015 y la aceptación visual de P-032 siguen pendientes.

## 1. Base real y alcance

**Implementado en esta rama:** React/Vite, Tailwind CSS 4.3.3 sobre tokens compartidos, SVG comunes, Claro/Oscuro/Sistema con preferencia persistida, foco visible y tratamiento de movimiento reducido. [ADR-005](decisions/ADR-005-tailwind-appearance.md) acepta esa tecnología, no una nueva dirección visual definitiva.

Los 64 tests y el pase previo de navegador constan en [A-018/A-021](progress.md); son evidencia histórica, **no pruebas reejecutadas para este plan**. La inspección de código actual confirma estructura y estilos, sin certificar comportamiento, accesibilidad o rendimiento nuevos.

**Skills aplicadas:** Impeccable (planificación y producto operativo), Emil Design Engineering (interacciones y movimiento) y Cognitive Doc Design (documentación). Los nombres solicitados `frontend-design` y `ui-ux-pro-max` no se encontraron en el catálogo ni en las rutas instaladas inspeccionadas; no se afirma haberlos ejecutado ni instalado. Estas skills disponibles aportan la base de esta propuesta.

**Usuario de referencia por validar:** personal de admisiones/atención que alterna fichas y conversaciones durante la jornada; aspirante que completa el formulario público. El primer grupo necesita lectura rápida y continuidad de contexto; el segundo, pasos comprensibles y recuperación de errores.

### Inventario de superficies actuales

Las rutas se leen en [navigation.ts](../frontend/src/shared/navigation.ts) y [App.tsx](../frontend/src/App.tsx): doce módulos en el menú y una referencia adicional de Creadores.

| Ruta | Superficie actual en esta rama | Tratamiento previsto |
|---|---|---|
| `#/overview` | Resumen con contadores ficticios, atención pendiente y recorrido de revisión. | Piloto de jerarquía, filas y siguiente acción. |
| `#/inbox` | Mensajes/Comentarios, filtros, hilo, control humano, ficha, tareas y timeline locales. | Piloto de densidad, contexto y continuidad. |
| `#/clients` | Lista/ficha, etapas, etiquetas, campos configurables y mini CRM demostrativo. | Adoptar patrones aprobados de lista, formulario y estados. |
| `#/application` | Formulario público con validación local y confirmación ficticia. | Refinar presentación preservando campos y reglas; coordinar con fase 4. |
| `#/assistant`, `#/settings` | Configuración/preview local compartidos; Ajustes con siete secciones. | Jerarquía de edición, guardado y operaciones no disponibles. |
| `#/review`, `#/knowledge`, `#/memory`, `#/access` | Superficies de alcance pendiente mediante `PlannedModule`. | Coherencia visual y explicación honesta; no fabricar funciones. |
| `#/retention`, `#/corporate` | Expansiones condicionadas mediante `PlannedModule`. | Menor protagonismo en navegación habitual, sujeto a revisión. |
| `#/creators` | Referencia separada mediante `CreatorReference`. | Mantener identificación como referencia y dependencia P-028. |

**Componentes existentes:** `Button`, `Badge`, `Notice`, `Field`, `SelectField`, `TextArea`, `PageHeading`, `EmptyState` en [ui.tsx](../frontend/src/shared/ui.tsx); iconos en [Icon.tsx](../frontend/src/shared/Icon.tsx). Navegación, selector de tema, filas, paneles y disclosures se componen en App/features. No existe un kit externo que deba reemplazarse.

**Coordinación:** esta rama conserva el formulario anterior al corte de fase 4. El trabajo avanzado de formulario vive en `feat/phase-4-local`; los contratos SQL/API, en su worktree separado. Revisar [A-021](progress.md) antes de integrar cambios compartidos. Este roadmap no fusiona ramas ni altera el trabajo de esos chats.

## 2. Dirección derivada de las tres referencias

Las tres imágenes estáticas aportadas fueron inspeccionadas. Esta selección confirma una preferencia estética; no aprueba automáticamente colores exactos, nuevas funciones o cifras del producto. El movimiento no puede observarse en capturas estáticas: su comportamiento parte de la petición del propietario y de la propuesta siguiente.

| Referencia | Qué se adopta como dirección | Adaptación a CRM CBN |
|---|---|---|
| R1 — Dashboard amplio con barras, indicador circular y acento violeta | Fondo neutro, paneles blancos redondeados, jerarquía de cifras y profundidad contenida. | Gráficas de admisiones y carga de atención; evitar paneles flotantes que oculten datos. |
| R2 — Dashboard pastel con accesos rápidos, dona y calendario | Acciones agrupadas, navegación compacta y diferenciación suave de categorías. | Accesos a Clientes/Inbox/Formulario existentes; el calendario y carga de archivos no se incorporan por aparecer en la imagen. |
| R3 — CRM compacto con indicadores, minigráficas, tabla e inbox | Relación clara entre resumen, datos y siguiente acción; aprovechamiento del espacio y acento lila. | Cola de atención e indicadores locales con vínculo al flujo; series temporales solo cuando su fuente esté definida. |

**Composición propuesta:** encabezado breve, fila de indicadores útiles, bloque analítico principal y cola de atención visible; navegación lateral más compacta. En Inbox predominan hilo, búsqueda y contexto; no convertirlo en otro dashboard. Paneles suaves, bordes discretos e iconografía coherente reemplazan la acumulación de elementos destacados.

**Color propuesto:** explorar un acento lila/violeta moderado y colores de series diferenciables, inspirados en las referencias. Mantener el verde institucional como identidad existente hasta acordar el papel de cada color. El violeta no queda declarado color oficial ni sustituye unilateralmente la marca. Oscuro tendrá superficies por niveles, ejes/textos legibles y contraste controlado; no requiere neón, transparencias o efecto vidrio.

No copiar nombres, fotos, correos, marcas, importes, promociones, mapas, planes comerciales o capacidades de las capturas. Las imágenes son referencia de composición, no fuente de datos, licencia de activos ni contrato funcional.

## 3. Oportunidades verificables

Son oportunidades de diseño, no defectos de negocio demostrados. La observación visual del coordinador se limita a Resumen oscuro en el navegador local, aproximadamente 1037 × 917; no equivale a una auditoría de todas las rutas.

| Antes: evidencia actual | Después: propuesta | Por qué / prueba de salida |
|---|---|---|
| App muestra trece entradas agrupadas; en la vista observada hay scroll lateral independiente y etiquetas largas partidas. | Dar prioridad visual a Operación; compactar o agrupar expansiones/referencias conservando acceso y nombres reconocibles. | Encontrar Resumen, Clientes e Inbox sin explorar opciones futuras; verificar teclado y etiquetas completas. |
| `Overview` mezcla cola de atención, contadores ficticios y recorrido; las filas altas desplazan el recorrido en la vista observada. | Cola más escaneable: identidad, último contexto breve y una acción clara; recorrido secundario y contadores discretos. | Abrir el hilo correcto desde Resumen y volver con contexto comprensible; comparar antes/después con los mismos fixtures. |
| App repite límites de demo en encabezado, badges, métricas y pie; varias features agregan avisos propios. | Aviso persistente breve más detalle contextual donde una acción pueda confundirse con operación real. | Reducir competencia visual conservando siempre la distinción local/no enviado/no conectado. |
| Inbox apila búsqueda, vista rápida, canal y estado antes de la lista; ficha y controles comparten ancho disponible. | Búsqueda y vista frecuente visibles; filtros secundarios agrupados con resumen activo; contexto progresivo sin ocultar control humano. | Cero coincidencias tiene salida clara; filtros y selección se conservan al abrir/cerrar contexto. |
| `tokens.css` centraliza color/espacios/radios y 160 ms; `styles.css` repite tamaños tipográficos y `ui.tsx` usa 150 ms. | Completar roles tipográficos y de movimiento; mapear valores existentes sin introducir una escala por pantalla. | Piloto y componentes comparten tokens; cualquier excepción queda justificada. |
| `Badge` tiene una presentación única; `Notice` distingue aviso/error; `TextArea` no ofrece las mismas props de error/ayuda que `Field`. | Catálogo explícito de variantes semánticas y contrato consistente de ayuda/error cuando cada control lo necesite. | Estado identificable por texto además de color; asociación accesible verificada en el flujo que lo use. |
| La navegación no tiene entradas animadas; tareas y timeline usan `details`; la ficha CRM se muestra/oculta desde un botón. | Preservar rutas instantáneas y disclosures nativos; añadir entrada/salida de gráficas y apertura contextual con reglas separadas. | No demorar acciones frecuentes ni perder foco/datos por la transición. |

## 4. Fundamentos propuestos para el piloto

La base **institucional serena** evoluciona hacia el dashboard de las referencias: superficies neutras, paneles redondeados, lectura clara y mayor presencia de datos. Verde bosque/menta y tipografía del sistema son la base vigente; el acento violeta y los nuevos roles de gráficos se revisarán en el piloto. No se inventa un logo ni se instala una fuente remota.

| Fundamento | Regla propuesta | Entregable concreto |
|---|---|---|
| Color y temas | Roles de superficie, texto, borde, selección, foco, estado y series. Separar identidad, acento interactivo y categorías de datos. Oscuro se ajusta por rol. | Matriz claro/oscuro de componentes/gráficas y combinaciones de contraste medidas. |
| Tipografía | Una familia; roles estables en `rem` para título, sección, cuerpo, control, dato y ayuda. Reservar tamaños pequeños para información secundaria legible. | Tabla de roles aplicada a cola, conversación y formulario; zoom sin pérdida de información. |
| Espaciado y densidad | Reutilizar `--space-*`; compactar metadatos y separar grupos de acción. Comenzar con una densidad coherente, sin crear un selector adicional. | Lista/hilo antes-después con nombres largos, múltiples etiquetas y mensajes extensos. |
| Jerarquía | Una acción principal por contexto; indicadores con definición y unidad; estado/asignación/control humano reconocibles. | Composición de Resumen e Inbox y recorrido de tres tareas reales de demo. |
| Componentes | Extender el origen compartido solo por necesidades del piloto; estados normal, hover, foco, pulsado, seleccionado, deshabilitado y error. | Catálogo acotado de controles/filas/avisos con ejemplos en ambos temas. |
| Estados de datos | Vacío inicial, sin coincidencias, error y confirmación distintos. Diseñar carga para futuro trabajo asíncrono, sin simular esperas en fixtures síncronos. | Matriz estado → mensaje → acción → foco; sin spinners o skeletons ficticios. |
| Responsive | Escritorio: lista/hilo/contexto según espacio; tablet: priorizar hilo y abrir contexto a demanda; móvil: secuencia lista → hilo → ficha con retorno claro. | Propuesta de layout y conservación de selección/borrador al cambiar de vista. No se da por implementada. |
| Lenguaje | Español neutral del preview conservado; verbos concretos y límites locales próximos a acciones sensibles. Idioma definitivo permanece P-003/P-015. | Revisión de etiquetas, instrucciones, errores y confirmaciones sin cambiar reglas de negocio. |

La única fuente de estilos seguirá siendo [tokens.css](../frontend/src/shared/tokens.css), el puente [tailwind.css](../frontend/src/shared/tailwind.css) y los controles compartidos. Añadir roles de tipografía, densidad, gráficos y movimiento allí, sin paletas por pantalla. Radios y sombras nuevos se decidirán sobre el piloto, evitando que cada dato necesite una tarjeta.

## 5. Contrato de datos para indicadores y gráficas

Fuente inspeccionada: [demo.ts](../frontend/src/shared/demo.ts), [crm.ts](../frontend/src/shared/crm.ts) y [workflow.ts](../frontend/src/shared/workflow.ts). `Client` tiene una etapa actual; `Thread` contiene canal, modo y lectura; `workflowOf` provee estado/tareas. Los mensajes no tienen timestamp y los eventos de workflow son temporales; no constituyen una serie histórica de admisiones.

| Métrica / tipo propuesto | Definición y fuente disponible | Regla y fallback |
|---|---|---|
| Fichas locales / indicador | `clients.length` del estado temporal. | Etiqueta Demo; 0 es conjunto vacío válido, no fallo. Sin porcentaje de crecimiento. |
| Fichas por etapa / barras | Conteo de `Client.stage` agrupado por etapas configuradas. | Resolver correspondencia etiqueta/clave; categoría explícita para valor sin correspondencia; suma igual al total. No llamar conversión a distribución. |
| Conversaciones por estado / dona | Conteo de Abierta/En espera/Cerrada mediante `workflowOf(thread).state`. | Categorías excluyentes y mismo universo; total igual a hilos actuales. Sin registros: estado vacío, no dona completa ficticia. |
| Hilos sin leer / indicador | Conteo de `Thread.unread === true`. | Independiente de modo/prioridad; no sumar categorías solapadas en una dona. |
| Distribución por canal / barras secundarias | Cada hilo tiene un canal en el modelo local. | Presentar hilos, no personas únicas omnicanal; no implica canal conectado. |
| Tareas pendientes / indicador opcional | Suma de tareas con `status === 'Pendiente'` en workflows. | No representa recordatorios programados ni incumplimientos de SLA. |
| Evolución diaria/semanal / línea o área | No hay historial suficiente en el modelo actual. | Para un futuro prototipo autorizado, dataset sintético separado con rótulo «Serie ilustrativa · Datos sintéticos»; en vista operativa sin fuente, «Histórico no disponible». |
| Conversión, ingresos, crecimiento y tiempo medio / fuera del piloto operativo | No hay cohorte/denominador, transacciones o eventos temporales completos que acrediten estas métricas. | No calcular desde probabilidades configuradas ni espera de demo. Diseñar solo estado no disponible hasta contrato y fuente aprobados. |

Cada modelo de gráfica definirá ID estable de serie/categoría, unidad, universo, filtros, rango temporal si existe, procedencia y estado de disponibilidad. Filtros compartidos tendrán alcance explícito; una cifra de otra selección no aparecerá bajo el mismo título.

**Estados obligatorios:** cero conocido, conjunto vacío, dato no disponible, error y carga real asíncrona se distinguen. Las series ilustrativas nunca se suman ni comparan como operación real con los conteos de fixtures actuales. Los valores finales y una tabla/lista textual equivalente estarán disponibles desde el inicio, antes de terminar la animación.

## 6. Movimiento de gráficas e interfaz

**Valores de partida propuestos para evaluar, no estándares universales ni implementación actual.** `feedback` reutiliza `cubic-bezier(0.23, 1, 0.32, 1)`; `suave` propone `ease-in-out`. La petición de gráficas animadas permite duraciones mayores que un control frecuente: la animación acompaña el dato, nunca demora su disponibilidad o la navegación.

### Gráficas: entrada, actualización y salida

| Elemento / disparador | Propiedad y comportamiento propuestos | Duración / curva | Interrupción y salida accesible |
|---|---|---|---|
| Contenedor al entrar al piloto | `opacity` y desplazamiento máximo 6 px; reservar dimensiones desde el primer render. | 160–220 ms / feedback. | No esperar su fin para dibujar datos o habilitar controles; sin escalado del texto. |
| Barras al montar la gráfica | Revelar marcas desde su línea base dentro del área de trazado; ejes, categorías y valores finales inmediatos. | 300–450 ms / feedback. | Última entrada gana; no hacer que etiquetas simulen conteos intermedios. |
| Línea/área al montar | Revelado progresivo del trazado de izquierda a derecha; ejes y leyenda estables. | 400–600 ms / suave. | El revelado no significa llegada temporal de datos; usar dataset ilustrativo claramente rotulado si falta historial. |
| Dona al montar | Revelado del arco; total/leyenda finales visibles desde el inicio. | 300–500 ms / feedback. | Categorías excluyentes y orden estable; sin porcentajes transitorios anunciados. |
| Filtrar o actualizar series | Interpolar marcas desde geometría actual a nuevo valor con claves estables; mostrar texto final inmediatamente. | 250–350 ms / suave; actualización de teclado inmediata por defecto. | Cancelar transición anterior; última selección gana. Mantener ejes salvo cambio necesario de dominio; no reiniciar desde cero. |
| Quitar serie/panel o salir de vista | Desvanecer marcas o contenedor; no invertir barras/dona hasta cero. | 120–180 ms / feedback. | Capa saliente sin interacción ni foco, excluida de lectura duplicada; destino navegable inmediatamente. Si se desmonta de inmediato, omitir salida antes que bloquear navegación. |
| Cambiar tema, hover o desplazarse | Actualizar tema/tooltip sin repetir entrada de la gráfica. | 0 ms para datos; tooltip breve o instantáneo. | No reanimar cada scroll/hover/cambio de tema; foco y selección permanecen. |

**Movimiento reducido:** todas las marcas adoptan inmediatamente su estado final; sin trazado progresivo, desplazamiento, giro ni interpolación. Consultar la preferencia al montar y durante cambios. Sin bucles continuos, rebotes decorativos, contadores que aparenten valores reales intermedios o secuencias de tarjetas que retrasen la lectura.

**Interacción:** tooltip accesible por foco/teclado y toque además de hover; tabla/lista de valores equivalente, etiquetas/unidades y leyenda comprensibles sin color. Escape cierra overlays cuando corresponda; no robar foco al actualizar. No convertir cientos de puntos en cientos de paradas Tab: definir navegación del gráfico o alternativa textual en V4.

### Controles y contexto

| Superficie / disparador | Propiedad e intención | Duración / curva propuestas | Interrupción y foco | Movimiento reducido |
|---|---|---|---|---|
| Botón, pulsación con puntero fino | `transform: translateY(1px)` para feedback; color/borde para estado. | 100–150 ms / feedback. | Transición retoma estado actual al soltar; teclado sin desplazamiento. | Sin transformación; feedback estático. |
| Navegación y fila seleccionada | Fondo/borde cambian; contenido y selección instantáneos. | 100–150 ms / feedback; 0 ms con teclado. | Última selección gana; sin reiniciar entradas ni alterar scroll. | Cambio instantáneo. |
| Selector Claro/Oscuro/Sistema | Cambio de tokens; sin barrido, flash o transformación de toda la página. | 0 ms inicialmente. | Selección inmediata; preservar foco y preferencia existente. | Igual. |
| Mostrar/ocultar ficha CRM | Si el piloto justifica transición: `opacity` y desplazamiento máximo 8 px, dentro del layout elegido. | Entrada 180 ms; salida 120 ms / feedback. | Reversible desde posición actual; al ocultar, recuperar foco si estaba dentro; no animar ancho. | Aparición/ocultación inmediata. |
| Menú móvil | Conservar expansión nativa inicial; si se aprueba panel superpuesto, `transform` + `opacity`. | Entrada 200 ms; salida 140 ms / feedback. | Aperturas rápidas cancelan anterior; Escape/retorno de foco solo según patrón elegido; sin focos ocultos. | Sin desplazamiento ni espera. |
| Tareas, timeline, plantilla (`details`) | Apertura nativa; opcional giro del indicador, sin animar altura del texto. | 120 ms / feedback para indicador; teclado 0 ms. | Respetar semántica nativa y control abierto/cerrado. | Indicador cambia sin transición. |
| Aviso de guardado/confirmación local | Texto persistente junto a acción; `opacity` opcional. | 120–160 ms / suave. | Repetición actualiza aviso, no apila eventos; `status` anuncia sin mover foco. | Cambio inmediato. |
| Error de validación | Mensaje, resumen y foco según flujo; sin sacudir campos. | 0 ms. | Mantener valores; no esconder error por tiempo; corregir sin reiniciar formulario. | Igual. |
| Cambio de hilo, búsqueda, rutas y nuevos mensajes | Contenido inmediato; no cascadas, typing ficticio, conteo animado ni entrada por mensaje. | 0 ms. | No robar foco ni forzar scroll si el usuario lee historial. | Igual. |

**Implementación prevista:** CSS/Tailwind para estilos y transiciones simples, con propiedades explícitas. SVG o una biblioteca candidata pueden resolver marcas/ejes; la tecnología se decide con una prueba acotada en V4. No presumir aceleración GPU, ausencia de repintado ni 60 fps: medir el recorrido real en navegador. Reservar espacio evita que una gráfica desplace el trabajo al entrar/salir.

No instalar bibliotecas en esta unidad. Una eventual elección debe probar compatibilidad con React/Vite actuales, temas/tokens, texto alternativo, tooltip por teclado/toque, entrada/actualización/salida interrumpibles, desmontaje/presencia, tamaño de bundle y mantenimiento/licencia. Comparar una solución SVG pequeña con como máximo dos candidatas; elegir la menor complejidad que cubra el piloto. Nueva dependencia o cambio de stack requiere autorización del propietario y ADR, no una instalación exploratoria implícita. Sin scrolljacking, parallax de trabajo ni blur global animado.

## 7. Roadmap detallado por fases visuales

V0–V7 ordenan el trabajo visual y **no renumeran las fases funcionales**. V0/V1 están cerradas en definición/auditoría; V2–V5 aceptadas para el piloto, V6 implementada en el alcance autorizado y V7 pendiente. Técnico prepara/implementa/verifica; propietario decide dirección del piloto y aceptación final. No se requieren confirmaciones nuevas para cada tarea dentro de un alcance ya autorizado. Las puertas humanas son aprobación de la propuesta del piloto, autorización de su implementación y aceptación del resultado; dependencias nuevas conservan su ADR.

### V0 · P0 — Referencias y brief

**Objetivo:** convertir las tres referencias en una dirección propia y acotada. **Estado:** completada al 100 % de este brief; referencias/preferencia, alcance y límites resueltos en el [informe V0/V1](reports/ui-v0-v1-baseline.md). Tokens/composición pertenecen a fases posteriores.

1. Relacionar R1/R2/R3 con composición, densidad, color y gráficos, separando lo visual de las funciones ajenas.
2. Fijar Resumen e Inbox como piloto y preservar atención humana, datos demo y rutas existentes.
3. Registrar gráficas con entrada/actualización/salida como requisito y movimiento reducido como variante equivalente.

**Entregable:** brief de las secciones 2–6. **Prerequisito:** solicitud e imágenes recibidas. **Salida:** tres referencias trazadas, alcance/antiobjetivos explícitos y ninguna métrica copiada; sigue V1 sin volver a pedir ejemplos.

### V1 · P0 — Auditoría de UX y contrato de datos

**Objetivo:** decidir qué se necesita ver y qué datos permiten mostrarlo con honestidad. **Estado:** completada al 100 % de la auditoría acotada; tres recorridos, métricas/IDs/filtros/fallbacks, sumas de fixtures y backlog comprobados en el [informe](reports/ui-v0-v1-baseline.md). Frontend 41/41 intacto en snapshot; cambio concurrente backend atribuido/conservado. No se implementó UI ni se certifica regresión global de trabajo ajeno.

1. Recorrer Resumen → hilo → ficha y filtros → sin coincidencias → recuperación; registrar pasos, foco y selección en la línea base.
2. Revisar navegación habitual frente a módulos futuros y jerarquía de avisos, manteniendo información local/no enviada.
3. Completar cada fila del contrato de gráficas con universo, fuente, filtros, IDs y tratamiento de vacíos; comprobar sumas de categorías con fixtures.
4. Definir estados de ejemplo: vacío, cero, nombre largo, múltiples etiquetas, valores desiguales y series sintéticas claramente separadas.

**Entregable:** mapa de recorridos, backlog priorizado y contrato de datos. **Prerequisito:** V0. **Salida:** cada indicador tiene definición/fuente/fallback; cero tasas o históricos sin sustento; tres recorridos y sus criterios de éxito documentados. Sigue V2.

### V2 · P0 — Fundamentos visuales y temas

**Objetivo:** producir un lenguaje único que acerque el CRM a las referencias. **Estado:** [fundamentos y catálogo](design-foundations-v2.md) preparados: roles claros/oscuros, escala tipográfica/geométrica, controles/estados, densidad y reglas responsive. Contraste y estructura comprobados; pase de navegador y aceptación humana se registran en el entregable. Sin cambios de código/configuración de la app.

1. Especificar roles tipográficos, espaciado, densidad, radios, bordes y elevación a partir de la base compartida.
2. Proponer relación verde institucional/acento violeta y paleta de series; definir equivalentes claros/oscuros por rol.
3. Documentar variantes/estados de botones, campos, badges, avisos, filas, indicadores y contenedores de gráficos.
4. Diseñar navegación compacta y reglas de composición para escritorio, tablet y móvil, sin esconder acciones esenciales.

**Entregable:** tabla de tokens propuesta y catálogo visual mínimo. **Prerequisito:** V1; ADR-005 como base. **Salida:** ambos temas cubren componentes/estados del piloto y colores no son el único portador de significado; no hay valores independientes por pantalla. Sigue V3.

### V3 · P0 — Composición visual del piloto

**Objetivo:** revisar una propuesta concreta antes de extenderla a toda la app.

1. Componer Resumen: encabezado breve, indicadores definidos, barras por etapa, dona por estado y cola accionable; usar solo gráficos útiles.
2. Componer Inbox: búsqueda/vista rápida, filtros secundarios, hilo con control humano y contexto progresivo; preservar Mensajes/Comentarios.
3. Preparar claro/oscuro en escritorio y móvil con los mismos datos, incluyendo vacío y texto largo; ubicar detalles de demo sin duplicación excesiva.
4. Anotar qué mostrará entrada/salida de gráficos y cómo volver de hilo/contexto sin perder selección o borrador.

**Entregable:** composiciones comparables y anotaciones de interacción. **Prerequisito:** V2. **Salida:** propietario revisa composición/densidad/color del piloto; los controles son reconocibles y los datos trazables. Esta aprobación no cierra P-003/P-015 para todo el producto; sigue V4 dentro del alcance autorizado.

### V4 · P0 — Prototipo de gráficas y movimiento

**Objetivo:** demostrar entrada, actualización y salida sin comprometer legibilidad o interacción.

**Corte autorizado 2026-10-14:** [muestra V4 e informe](design-motion-v4.md). Evalúa 250 ms entrada / 200 ms actualización / 150 ms salida, más breves que los rangos exploratorios anteriores; teclado y movimiento reducido inmediatos. Sin librerías ni cambios en la aplicación. Etiquetas directas y tabla accesible resuelven la información de gráficos sin depender de hover.

1. Preparar, tras autorización para prototipar, barras y dona con datos de demo; línea/área solo con serie ilustrativa identificada.
2. Implementar la matriz de movimiento en una muestra acotada, diferenciando contenedor y marcas; mantener textos finales/ejes disponibles.
3. Probar actualizaciones rápidas, salida durante entrada, desmontaje, cambio de tema y movimiento reducido; última interacción gana.
4. Resolver tooltip de teclado/toque y alternativa textual; comparar SVG sencillo con candidatas solo si el caso lo exige, antes de instalar una dependencia nueva.

**Entregable:** muestra interactiva local, registro de medición y decisión técnica acotada; ADR si se requiere dependencia. **Prerequisito:** V3 aceptado y autorización de prototipo; contrato de datos V1. **Salida:** entrada/actualización/salida observables en los gráficos elegidos, valores finales inmediatos, sin espera de navegación/foco oculto ni reanimación por hover/tema; versión reducida instantánea. Sigue V5.

### V5 · P0 — Implementación del piloto

**Corte autorizado 2026-10-14:** [integración V5 y evidencia](design-integration-v5.md). Aprobación V4 e implementación real local expresas, incluida conservación de borradores de Inbox entre rutas. Sin dependencias nuevas ni cambios conectados.

**Objetivo:** aplicar composición y movimiento validados al flujo real de la demo.

1. Integrar tokens/componentes del piloto en el shell, Resumen e Inbox conservando estado y contratos locales existentes.
2. Conectar gráficos a selectores de datos tipados de la demo; mantener la serie ilustrativa aislada, si fue aceptada para el piloto.
3. Implementar navegación/contexto responsive, filtros y avisos con conservación de foco, selección y borrador.
4. Normalizar y comprobar comportamiento afectado; registrar capturas claras/oscuras, pruebas relevantes y diferencias respecto al piloto aprobado.

**Entregable:** Resumen e Inbox funcionales localmente con gráficas animadas. **Prerequisito:** V4 y autorización de implementación; cualquier ADR técnico resuelto. **Salida:** tres recorridos de V1 completos, conteos coherentes, filtros reversibles, ambos temas operables y ningún envío/registro real añadido. Corregir hallazgos acotados antes de extender; sigue V6.

### V6 · P1 — Extensión a módulos existentes

**Corte autorizado 2026-10-14:** el propietario aceptó V5 y autorizó Clientes, Asistente y Ajustes en ambos temas, conservando borradores y funciones, con movimiento más lento y natural. [Implementación, propiedad del estado y evidencia V6](design-extension-v6.md).

1. Adoptar composición y tokens compartidos en Clientes, con borradores separados por contacto y ficha nueva; no guardar implícitamente al cambiar de selección/ruta.
2. Aplicar el lenguaje a Asistente/Ajustes, conservando siete secciones, plantillas de demostración y operaciones IA existentes; guardar, descartar, revisar y probar siguen separados.
3. Conservar configuración y catálogo IA pendientes en RAM entre rutas, sin secretos ni almacenamiento nuevo; responder correctamente al finalizar solicitudes locales en vuelo.
4. Ajustar ritmo de gráficas a 450/350/250 ms y paneles/tema a 300 ms; curva de entrada suave, teclado/reducción instantáneos, sin ralentizar escritura o navegación.

**Entregable:** tres módulos refinados y evidencia de regresión. **Salida:** controles conservados, borradores por entidad, límites de guardado claros y gráficas equivalentes en ambos temas. El formulario, Creadores y pantallas futuras no se rediseñan en este corte ni se copian desde otros worktrees. La ampliación restante requiere otro alcance autorizado; sigue V7 para el corte actual.

### V7 · P1 — Verificación, aceptación y entrega

**Objetivo:** cerrar el corte con evidencia técnica y aceptación visual humana diferenciadas.

1. Ejecutar la matriz siguiente sobre source normalizado: recorridos, teclado, lector de pantalla, temas, responsive y movimiento reducido.
2. Comparar rendimiento antes/después y revisar interacción bajo actualizaciones repetidas; corregir fallos observados en un lote acotado y confirmar.
3. Entregar capturas y muestra de movimiento de entrada/salida, tabla de métricas y reporte de límites; build por sí solo no prueba animación.
4. Registrar aceptación por pantalla/tema y actualizar progreso/pendientes; abrir seguimiento para capacidades todavía condicionadas.

**Entregable:** reporte visual/técnico y catálogo final del corte. **Prerequisito:** V5/V6 congelados y checks pertinentes. **Salida:** aceptación explícita del propietario y evidencia completa del alcance; P-003/P-015 solo se cierran si todos sus requisitos aplicables se resolvieron. No implica publicación, integración o despliegue.

Las futuras capacidades de revisión académica y expansiones siguen el [roadmap funcional](roadmap.md) y P-028 para Creadores; no se añaden por imitar las referencias. Fechas y esfuerzo se estimarán tras fijar el alcance del piloto, sin porcentajes de progreso ficticios.

## 8. Matriz de verificación futura

- **Recorridos:** Resumen → hilo → contexto; filtro sin coincidencias → restablecer; Clientes → Inbox; errores/confirmación del formulario; guardar/descartar Ajustes. Usar datos sintéticos y distinguir demostración de envío/registro.
- **Accesibilidad:** Tab/Shift+Tab, Enter/Espacio, foco visible/no oculto y retorno al cerrar superficies; lectura de estados/errores con lector de pantalla; contraste medido en ambos temas. Objetivo WCAG 2.2 AA ya propuesto en el sistema de diseño; este documento no declara conformidad.
- **Objetivos táctiles:** proponer 44 × 44 px CSS como meta de comodidad para controles frecuentes. No confundirla con el mínimo AA de 24 × 24 px y sus excepciones de [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html). La [reducción de animación de interacciones](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html) se adopta como criterio del producto; WCAG 2.3.3 corresponde a AAA, no a una certificación AA automática.
- **Responsive:** revisar al menos 390 × 844, 768 × 1024 y 1440 × 1024, más zoom al 200 %, nombres largos y contenido extenso. No scroll horizontal del documento ni acciones perdidas; cualquier scroll interno tiene propósito y acceso por teclado. Dispositivo físico se reporta aparte.
- **Gráficas:** suma de barras/categorías igual al universo definido; filtros y leyendas coherentes; cero, vacío y no disponible diferenciados; fuente/unidad visibles, tabla textual equivalente, tooltip por teclado/toque y colores legibles en ambos temas.
- **Movimiento:** entrada, actualización y salida de marcas/contenedores; preferencia reducida antes de cargar y cambiada durante uso; aperturas repetidas y reversión a mitad de transición; etiquetas finales inmediatas, sin pérdida de foco/valor/selección ni interacción con capas salientes. Cambio de tema/hover/scroll no reinicia entrada.
- **Rendimiento:** comparar el mismo recorrido y datos antes/después en navegador; observar saltos de layout y trabajo de renderizado durante apertura/cierre. No animar dimensiones para desplazar listas; sin tareas largas atribuibles al movimiento ni regresión perceptible. Registrar entorno y medición, no prometer fps sin evidencia.
- **Código y alcance:** normalizar antes de checks; pruebas de comportamiento significativas para cambios reales, regresión de tema y flujos afectados. Browser confirma UX; build no prueba operación, seguridad conectada o aprobación humana. Actualizar avance/pendientes con cada corte.

## 9. Estado y siguiente unidad

**Confirmado:** referencias, fundamentos V2, composición V3, movimiento V4 e integración V5 aceptados. **Implementado:** [V5 Resumen/Inbox](design-integration-v5.md) y [V6 Clientes/Asistente/Ajustes](design-extension-v6.md), con borradores efímeros sobre rutas, componentes existentes y movimiento pausado. Los datos de demo siguen limitados a la pestaña; ajustes IA guardados mantienen su persistencia previa en backend.

El aislamiento con proveedores IA se resolvió en A-024. Backend, proveedores y otros worktrees quedan fuera de los cambios V6. **Siguiente unidad: V7**, aceptación y comprobaciones ampliadas del corte. P-003/P-015, marca oficial, idioma definitivo y contratos conectados mantienen pendientes. La evidencia técnica y de navegador se distingue de la aceptación humana final.
