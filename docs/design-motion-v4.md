# V4 — Entrada, actualización y salida de gráficas

**2026-10-14 · Prototipo independiente preparado para revisión.** El propietario aprobó la composición V3 y autorizó animar gráficas/transiciones en claro y oscuro preservando el funcionamiento existente. La [muestra V4](previews/v4-motion.html) añade movimiento a barras y dona, conserva textos inmediatos y cancela animaciones interrumpidas. [V3](previews/v3-pilot.html), frontend, backend y ajustes IA se preservan byte por byte. La integración en React/Tailwind pertenece a V5.

## Probar el resultado

1. Abrir Resumen y pulsar **Repetir entrada**. Los valores finales permanecen visibles mientras aparecen las marcas.
2. Alternar la muestra **Todos los hilos / Solo WhatsApp**: barras pasan de 1/1/1/1 a 0/0/1/0; total gráfico de 4 a 1. Los indicadores generales y la cola siguen mostrando el conjunto completo. Todos los hilos están abiertos: la dona conserva un arco completo y cambia su cifra inmediatamente, sin inventar otras categorías.
3. Abrir **Inbox** durante la entrada para observar la salida sin retrasar navegación. Volver rápidamente a Resumen: se cancela la salida anterior. **Sin datos** elimina marcas con opacidad y muestra cero inmediato, sin animar una falsa disminución del negocio.
4. Comparar claro/oscuro y activar **Vista sin movimiento**. También el teclado y la preferencia reducida del sistema producen el estado final inmediato. **Inspeccionar movimiento** ofrece reproducción lenta ×4 y un registro local de duración/limpieza; son controles exclusivos de revisión.

No hay API, envío, almacenamiento, proveedor, dato real o librería nueva. Escenarios siguen restableciendo solo los casos/borradores del piloto; el filtro gráfico no modifica la conversación ni sus borradores.

## Decisión técnica y contrato

El movimiento responde a **indicación de estado** y continuidad de una aparición/desaparición ocasional. El teclado, búsqueda, elección de hilo y tareas repetitivas permanecen inmediatos. Se utiliza **Web Animations API** para controlar interrupción y salida, y transiciones CSS explícitas para los colores de superficies. No se necesita comparar o instalar una librería: CSS/SVG y la API nativa cubren los dos gráficos sin añadir un adaptador a React durante esta fase independiente.

| Elemento | Implementación | Tiempo normal / curva | Límite |
|---|---|---|---|
| Entrada de barras/dona | `clip-path` revela geometría final; `opacity` confirma aparición. | 250 ms / `--ease-out` existente. | No `scale(0)`, rebote, giro del arco, contador numérico o cambio de ejes. |
| Actualización de barras | Nueva máscara desde el estado computado visible; geometría base de ancho completo. | 200 ms / `--ease-in-out` añadida. | No animar `width` ni alterar labels durante interpolación; última interacción gana. |
| Categoría que desaparece | Opacidad a cero conservando máscara anterior. | 150 ms / `--ease-out`. | No dibujar un descenso ficticio a cero; valor textual cero inmediato. |
| Salida de Resumen | Snapshot visual de gráficas, inerte y `aria-hidden`; la ruta cambia inmediatamente. | 150 ms / `--ease-out`. | Ningún ID duplicado ni descendiente enfocable; sin eventos de puntero; retirada tras terminar/cancelar. |
| Tema | Color de fondo/texto en superficies, sin repetir marcas. | 150 ms / `ease`. | Propiedades explícitas, sin `transition: all`. Sin coreografía por tarjeta. |
| Control pulsado | Feedback V2/V3 conservado. | 140 ms / `--ease-out`. | Solo puntero fino; teclado y reducción sin transformación. |

Los tiempos **250/200/150 ms** concretan una variante más rápida que los rangos exploratorios V1–V3 (entrada 300–500, actualización 250–350): el piloto operativo usa respuesta menor de 300 ms y deja el movimiento expresivo a las marcas. La reproducción ×4 es una herramienta de inspección explícita y no un nuevo tiempo de producto. No se añadió otra paleta: 35 roles cromáticos por tema son idénticos a V3/V2.

| Before | After | Why |
|---|---|---|
| Geometría V3 estática. | Marcas con entrada, actualización y salida; cifras y tabla siempre finales. | Comunica cambio sin retrasar lectura. |
| Un cambio rápido podría reiniciar una animación desde cero. | Se lee la máscara/opacidad computada antes de cancelar y se retoma desde ella. | Evita saltos y conserva la última intención. |
| `display:none` cortaría una salida. | Snapshot inerte se desvanece mientras la ruta nueva recibe foco. | La salida es observable sin bloquear navegación ni mantener controles ocultos activos. |
| Marcas originales podían continuar en una ruta oculta durante la primera prueba. | Tras capturar el snapshot se cancelan; reentrada cancela también el clon. | Desmontaje real y cero animaciones residuales del origen. |
| Valores adicionales dependerían de hover. | Etiquetas directas y **Ver datos y alcance**, divulgación nativa con tabla completa. | La misma información funciona con teclado y toque; no requiere tooltip oculto ni otra biblioteca. |

## Cancelación, accesibilidad y datos

La implementación fija el estilo final antes de iniciar el efecto y conserva un único efecto por marca. Interrumpir captura primero el estado visual vigente; cancelar queda seguro porque el estilo subyacente ya es el destino más reciente. Las promesas `finished` tienen manejo de rechazo: `cancel()` puede rechazarlas con `AbortError`, como documenta [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Animation/cancel). Salir de la página o esconder la pestaña cancela efectos y retira copias transitorias.

La preferencia [`prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion) se escucha dinámicamente. La opción del piloto puede forzar reducción, nunca anular la preferencia del sistema. Cualquier interacción de teclado cancela movimiento activo y toma el camino inmediato. Cambiar tema no inicia ni reinicia las marcas; no hay triggers de hover o scroll. Navegación, foco y borradores conservan el comportamiento V3.

El filtro de gráficas usa únicamente los cuatro fixtures existentes: **Solo WhatsApp** selecciona Persona Demo A, etapa Interés, estado Abierta. No cambia las fuentes ni transforma ausencia en categoría nueva. La alternativa textual contiene cuatro etapas y tres estados, con el mismo filtro y valor final desde el primer render. La dona solo anima presencia/ausencia: cambiar 4 abiertas por 1 abierta mantiene 100 % abiertas y **no** anima una proporción falsa.

La copia de salida es decoración temporal del gráfico anterior, no una segunda fuente accesible: `inert`, `aria-hidden`, sin IDs ni controles. Al volver a Resumen se cancela/retira. La tabla de valores pertenece solo al estado actual y nunca se clona. Las dimensiones de barras y dona se reservan; no se anima layout.

## Evidencia y medición

| Capa | Comprobación | Resultado / límite |
|---|---|---|
| Preservación | SHA-256 antes/después de 59 archivos de app, tres archivos V3 y ajustes IA. | **63/63 exactos**; `.local/ui-v4-evidence/baseline.json`, `structural.json`, `preservation.json`. No es regresión exhaustiva de negocio. |
| Sintaxis/estructura | `node --check`; IDs/referencias/recursos locales, roles de tema, ausencia de API/almacenamiento. | **69 IDs**, **18 referencias**, dos recursos locales; 35 roles exactos por tema. |
| Comportamiento aislado | Ocho casos en jsdom con WAAPI simulada, sin instalar paquetes. | Valores inmediatos, subset real, última actualización, tema sin reentrada, salida inerte/limpieza, borrador, reducción/control de sistema y teclado, vacío. `.local/ui-v4-evidence/motion-check.json`; no prueba visual, interpolación real, timing ni preferencia del SO. |
| Navegador | Resumen/Inbox × claro/oscuro × 390/768/1440 px sobre JS final. | **12 combinaciones sin overflow horizontal**; entrada/interpolación, subset, interrupción/salida/reentrada, teclado, reducción, vacío y tabla comprobados. Consola sin advertencias/errores. `.local/ui-v4-evidence/browser.json`. |
| Medición local | `performance.now()` desde inicio a finalización/cancelación, duración configurada y conteo de efectos/capas. | Visible en **Inspeccionar movimiento**; tiempo de callback puede diferir del nominal. No mide FPS, coste de render completo, CPU ni tareas largas. |

No se ejecutó build/suite de app: sus archivos no cambiaron. Los snapshots estáticos finales prueban composición, no la animación por sí solos. La evidencia de movimiento requiere muestras intermedias de máscara/opacidad y finalización/limpieza. La preferencia del sistema, lector de pantalla, zoom y teléfono físico deben distinguirse de la opción de reducción del piloto; no se declara conformidad WCAG global ni rendimiento de producción.

### Observaciones del navegador

- Entrada lenta ×4: cinco marcas activas; máscara de barra `81,3133 %` y opacidad `0,747468`, mientras los valores ya son **1/1/1/1** y total **4**. Velocidad normal: entrada configurada **250 ms**, cinco efectos observados interpolando. En una actualización rápida final, el callback se registró a **265,5 ms** para 250 nominales; no equivale a tiempo de CPU ni pérdida de frames.
- Subset Todos→WhatsApp actualiza cifras finales inmediatamente a **0/0/1/0**, total **1**. Todos→WhatsApp→Todos termina en **1/1/1/1**, total **4**, cero animaciones/capas pendientes. Cambiar tema desde reposo mantiene cero efectos de gráfica.
- Después de la corrección de limpieza, salida durante entrada cambia ya a **Conversaciones**, foco en `page-title`, una sola capa y efecto de salida, inerte, `aria-hidden`, sin eventos de puntero ni descendientes enfocables. Reentrada rápida cancela la capa anterior: cero capas y cinco marcas nuevas, sin conservar animaciones originales ocultas.
- Teclado Enter en **Repetir entrada**: cero efectos, duración inmediata. Override **Vista sin movimiento**: filtro 4→1 inmediato, valores correctos y cero efectos; vacío con total cero y las cinco marcas a opacidad cero. La preferencia del SO se inspeccionó en código y se simuló en el harness; **no se emuló el SO en navegador**.
- Borrador y contacto A se conservaron en ficha/tema oscuro/A→B→A antes de la corrección exclusiva de limpieza. La matriz de 12 tamaños/temas y los recorridos afectados de cancelación se comprobaron después. Tabla nativa con siete categorías y recuentos del filtro; móvil 390×844 inspeccionado visualmente.
- Capturas finales: `overview-light.png`, `overview-dark.png`, `mobile-dark.png`. Baseline V3 capturado a 1280×720: área de barras 490,328×128,75 px, dona 164×164 px y sin overflow. Esta referencia más el diagnóstico temporal **no constituyen un benchmark comparativo de rendimiento o tareas largas**.

## Salida y continuación

V3 aceptada para este piloto; V4 preparada y comprobada en el alcance local descrito. La aprobación humana del movimiento y la integración V5 quedan separadas. V5 debe trasladar roles/contratos validados a los componentes compartidos React/Tailwind conservando lógica y estado; no copiar el simulador, su filtro gráfico o sus controles de diagnóstico como funciones de negocio. P-003/P-015 y los contratos conectados mantienen sus pendientes.
