# V3 — Resumen e Inbox con contexto y atención visibles

**2026-10-14 · Piloto preparado; revisión de composición pendiente.** El propietario aceptó la dirección visual de V2 y autorizó diseñar Resumen e Inbox en ambos temas, preservando lo que funciona. El [piloto independiente](previews/v3-pilot.html) concreta esa dirección con datos ficticios trazados al código actual. La aplicación React/Tailwind y su backend conservan sus archivos; V3 no integra estos diseños ni sustituye la lógica existente.

## Recorrido de revisión

1. Abrir **Resumen**, comparar **Claro / Oscuro** y abrir el hilo de Persona Demo A desde la cola.
2. En **Inbox**, tomar control, escribir un texto ficticio y alternar **Ver ficha / Cerrar ficha**. Cambiar de hilo y regresar conserva el borrador de esta muestra. Añadirlo muestra explícitamente que no se envió.
3. Probar **Sin leer**, una búsqueda sin resultados y **Más filtros**. La selección y el borrador no dependen del resultado de la lista. **Restablecer filtros** recupera la bandeja.
4. Comparar los escenarios **Habitual / Sin datos / Texto extenso**. Cambiar escenario restablece exclusivamente los casos y borradores del piloto. En móvil: bandeja → hilo → ficha, con regreso visible.

Los enlaces de otros módulos abren la app actual en otra pestaña. No transfieren estado ni selección del piloto. La muestra no llama a APIs ni usa almacenamiento; recargar vuelve al tema claro y a los casos iniciales.

## Composición y decisiones

Modo de uso **Operate**: quien atiende admisiones necesita priorizar conversaciones, comprender el contexto y mantener control humano. La identidad se expresa con tipografía clara, superficies neutrales, verde en la acción primaria y violeta en selección/análisis, siguiendo los [fundamentos V2](design-foundations-v2.md). Las referencias suministradas inspiran el ritmo visual; no se copian marcas, personas, ingresos o crecimiento.

| Before | After | Why |
|---|---|---|
| Resumen actual presenta una franja de cifras y una cola extensa. | Indicadores en una banda, distribución por etapa/estado y cola accionable con jerarquía propia. | Separa lectura del conjunto y trabajo individual; evita convertir cada cifra en una tarjeta decorativa. |
| Las cuatro opciones de filtro del Inbox ocupan un bloque permanente. | Búsqueda y vista rápida permanecen visibles; canal/estado pasan a **Más filtros** con contador. | Reduce carga visual conservando acceso y significado. |
| Hilo, operación y contexto compiten por espacio. | Hilo dominante, control humano inmediato, operación progresiva y ficha opcional. | La tarea principal conserva ancho; el detalle sigue disponible. |
| Mensajes y Comentarios comparten acceso dentro del módulo. | Dos subsecciones explícitas con recuento; Comentarios conserva sus tres canales y estados. | Mantiene el mapa mental y evita fusionar mensajes privados con comentarios públicos. |
| Avisos de demo repetidos en distintas zonas. | Un aviso global breve, identificación del canal ficticio y aclaración junto al compositor. | El alcance sigue visible en los puntos de decisión, sin competir con cada dato. |
| La selección y los borradores viven en la vista de Inbox actual. | El piloto conserva borradores por hilo al cambiar ficha, filtros, tema y ancho. | Permite revisar la composición sin sacrificar el contexto; no declara una mejora de persistencia en la app. |

## Fuente de datos y significado

Los fixtures habituales se transcribieron de [demo.ts](../frontend/src/shared/demo.ts), [crm.ts](../frontend/src/shared/crm.ts), [comments.ts](../frontend/src/shared/comments.ts) y [workflow.ts](../frontend/src/shared/workflow.ts). El piloto no importa módulos productivos: mantiene independencia y no activa componentes o efectos del CRM.

| Elemento | Fuente / cálculo en el estado inicial | Límite visible |
|---|---|---|
| Fichas | `seedClients`: A, B, C, D → **4**. | Datos ficticios; no alumnos ni matrículas. |
| Sin leer | `seedThreads`: A y C → **2**. Marcar leído en el piloto actualiza sus indicadores locales. | Abrir hilo no lo marca leído automáticamente. |
| Tareas pendientes | `workflowOf`: ninguna tarea creada → **0**. | No confundir con comentarios pendientes ni tareas ejecutadas. |
| Abiertas | Cuatro hilos sin workflow propio → fallback `Abierta`: **4**, espera **0**, cerradas **0**. | La dona representa estado, no éxito ni completitud. |
| Barras por etapa | Nuevo C, Contactado D, Interés A, Solicitud preparada B → **1** cada una. | Longitud = cantidad / total de fichas; 25 % visual cada barra. Etiqueta y valor permanecen en texto. No tasa de conversión. |
| Cola | Cuatro hilos en el orden de los fixtures, cada uno abre su `clientId`. | No prioridad predictiva ni clasificación nueva por IA. |
| Mensajes | Textos y modos originales A/C IA simulada; B/D humano. | Añadir texto requiere control humano; no envío, respuesta automática ni persistencia. |
| Comentarios | Facebook A pendiente, Instagram B pendiente, TikTok C respondido. | Muestra de composición; respuestas y filtros completos se prueban en la app actual. |
| Texto extenso | Variante de estrés sobre el caso A: nombre, mensaje y referencia larga ficticios. | No es información adicional del CRM ni escenario de operación real. |
| Sin datos | Cero fichas/hilos/comentarios, barras sin valor y dona sin segmento. | Vacío conocido con recuperación; distinto de carga/error. |

No se muestran ingresos, conversión, tendencia histórica o tiempos medios. No existe una fuente adecuada en el conjunto actual. Las probabilidades configuradas en CRM no alimentan una métrica de conversión.

## Estados, navegación y adaptación

| Superficie | Escritorio | Tablet | Móvil <704 px |
|---|---|---|---|
| Shell | Navegación textual de 208 px; Resumen/Inbox visibles, otros módulos en divulgación. | Navegación superior textual; módulos adicionales en lista desplegable. | Resumen/Inbox siempre accesibles; módulos adicionales en dos columnas. |
| Resumen | Banda de cuatro indicadores; gráficos comparables y cola con columnas. | Las gráficas se distribuyen según espacio; etiquetas y valores directos. | Indicadores 2×2, gráficas apiladas y cola con mensaje en varias líneas. |
| Inbox | Lista + hilo; ficha tercera columna desde 1380 px. Entre 704–1379 px aparece debajo. | Lista + hilo, ficha debajo; scroll normal del documento. | Un panel a la vez: bandeja → hilo → ficha. **Volver a bandeja** y **Cerrar ficha** recuperan contexto y foco. |
| Texto extenso | Nombre completo envuelve; vista previa del mensaje acotada. | Misma identidad y lectura del hilo sin recortes. | Mensaje completo y cadena sin espacios envuelven; el compositor no fuerza ancho. |

La propuesta mantiene **trece destinos**: doce de [navigation.ts](../frontend/src/shared/navigation.ts) más Creadores, definido aparte en [App.tsx](../frontend/src/App.tsx). Dos tienen composición en el piloto; once abren la app actual. Ajustes conserva sus siete secciones **IA / Canales / APIs / Diagnóstico / Usuarios / Perfil / Seguridad** mediante ese enlace; no se rediseñan ni reimplementan aquí.

Los filtros **Míos · Demo** (sin asignados), **Sin asignar**, **Humano**, **IA**, canal y estado operan sobre los fixtures. La lista vacía no borra la conversación seleccionada. Cambiar a Comentarios y volver conserva el borrador de Mensajes. Los controles deshabilitados muestran motivo: **Ya leído** o la ayuda de control humano/campo vacío del compositor. No se inventan esperas o skeletons para datos síncronos.

## Contrato de interacción y movimiento

| Acción | V3 visible | Anotación para la siguiente fase |
|---|---|---|
| Entrada / salida de gráficos | Geometría estática, valor final inmediato, etiquetas legibles en ambos temas. | V4: barras 300–450 ms; dona 300–500 ms; salida por opacidad 120–180 ms. No simular un descenso a cero. |
| Actualización | Los indicadores cambian inmediatamente al marcar leído; las gráficas conservan su universo. | V4: interpolar desde el valor visible 250–350 ms, última actualización prevalece, ejes estables. |
| Tema, búsqueda, hilo y navegación | Cambio inmediato; sin coreografía de entrada por tarjeta. | No reiniciar gráficos por hover, tema o scroll ni bloquear foco/navegación. |
| Ficha | Abre con foco en título y cierra al botón de origen; si el destino queda fuera de pantalla, lo muestra con desplazamiento inmediato mínimo. Borrador independiente del panel. | Si V4 justifica transición: opacidad/desplazamiento breve, nunca animar ancho o desmontar el borrador. |
| Pulsación | 140 ms de desplazamiento 1 px solo con puntero fino, sin `transition: all`. | Teclado y movimiento reducido sin transformación. |
| Movimiento reducido | CSS elimina la transición de pulsación. | V4 muestra resultado final instantáneo de gráficos; no reduce solo la duración. |

El piloto conserva borradores incluso al navegar entre sus dos composiciones para facilitar revisión; **la aplicación actual no promete esa persistencia al salir de Inbox**, según el hallazgo V1. V5 deberá conservar el contrato real o tramitar su mejora como cambio funcional separado. Las operaciones avanzadas (estado/asignación/prioridad, tareas, cronología, plantillas revisadas, mini CRM y respuestas a comentarios) no se duplican: se señalan sus ubicaciones y enlaces a la app actual.

## Preservación y comprobaciones

- Solo se añaden HTML/CSS/JS de revisión y documentación; sin cambios en app, configuración, paquetes, datos, puertos o procesos de los otros worktrees.
- Línea base local antes de trabajar: **59 archivos frontend/backend** con SHA-256, más hash separado de ajustes IA. Después: **59/59 exactos**, ajustes exactos. Evidencia: `.local/ui-v3-evidence/source-before.json`, `settings-before.json`, `structural.json`.
- `node --check docs/previews/v3-pilot.js`: sintaxis válida. Estructura: **61 IDs únicos**, **17 referencias resueltas**, dos recursos locales existentes. No llamadas de red, API o almacenamiento en JS.
- **35 roles cromáticos por tema idénticos a V2**, verificados por igualdad de variables; no hay paletas por pantalla. La medición matemática V2 permanece como evidencia de esas combinaciones; no representa una auditoría completa de nuevos estados o accesibilidad.
- Navegador del coordinador: **12 casos** (Resumen/Inbox × claro/oscuro × 390/768/1440 px), sin overflow horizontal. Borrador conservado al alternar hilo A→B→A, ficha, tema y búsqueda vacía; móvil bandeja→hilo→ficha→regreso comprobado. Escenarios vacíos de ambas pantallas, tres comentarios y texto móvil largo sin espacios revisados. Teclado: Claro → Tab → Oscuro → Espacio cambia tema; consola consultada sin advertencias/errores. Evidencia `.local/ui-v3-evidence/browser.json`, cuatro capturas finales `overview-light.jpg`, `overview-dark.jpg`, `inbox-light.jpg`, `inbox-dark.jpg`, captura móvil extensa y línea base anterior.
- La inspección encontró foco fuera de la zona visible al cambiar de ruta y abrir ficha debajo del hilo en tablet. La corrección acotada añade scroll inmediato al inicio al cambiar de ruta y desplazamiento mínimo al abrir/cerrar ficha solo si el destino queda fuera del viewport. Confirmación final: Resumen→hilo D conserva identidad y enfoca título con `scrollY=0`; cerrar ficha en tablet devuelve foco a **Ver ficha** visible. Al abrir, el título se desplaza al borde inferior de 1024 px (fondo medido 1024,48 px por redondeo); no se presenta como prueba de visibilidad integral del panel.
- La matriz de layout se midió antes de esa corrección exclusiva de foco/scroll; el pase final confirmó sus recorridos afectados sobre JS final. Movimiento reducido inspeccionado en CSS, sin emulación de preferencia del sistema. Sin lector de pantalla, zoom 200 %, teléfono físico ni certificación WCAG completa.
- No se ejecutó build/suite de la app porque sus archivos permanecen idénticos. La preservación por hash prueba ausencia de modificación de esos archivos, no funcionamiento de SIIE, proveedores, producción o regresión exhaustiva.

## Salida

V2 aceptada como dirección para este piloto; V3 preparada y comprobada en el alcance local anterior para revisar composición, densidad, color y navegación. La aprobación del piloto no cierra P-003/P-015 para todo el producto. Sigue **V4, movimiento de gráficas**, después de revisión y autorización del prototipo; la adopción en React/Tailwind corresponde a V5. No se instaló dependencia, hizo commit/push o activó integración.
