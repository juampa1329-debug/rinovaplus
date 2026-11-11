# V2 — Fundamentos visuales y temas

**2026-10-14 · Dirección visual aceptada para el piloto V3.** El propietario confirmó «Me gusta» y autorizó componer Resumen e Inbox siguiendo estos estilos. El [catálogo independiente](previews/v2-foundations.html) concreta color, tipografía, densidad y estados en claro/oscuro. Conserva la identidad verde vigente y el acento violeta moderado inspirado en las referencias seleccionadas. No sustituye la apariencia actual ni integra componentes en la aplicación; esa adopción corresponde a V5, después del piloto. Esta aceptación no aprueba marca/idioma definitivo ni todo el producto.

## Revisar la propuesta

1. Abrir el catálogo y alternar **Claro / Oscuro**: la selección cambia inmediatamente, sin guardar preferencias ni afectar el CRM.
2. Revisar **Controles / Estados** con puntero o flechas del teclado. Enviar el formulario vacío muestra error asociado y foco; escribir un nombre ficticio permite confirmar la muestra sin persistencia.
3. Comparar **Cómoda / Compacta** y leer filas con nombre extenso. La gráfica estática contiene **20 registros sintéticos independientes**, no los cuatro fixtures del CRM ni un histórico real.

La dirección propuesta es operativa: canvas neutral frío, superficies limpias con radio de 16 px, texto oscuro legible y acciones claras. Violeta identifica selección/análisis; verde conserva las acciones primarias y la identidad textual. La marca oficial y la aceptación definitiva de idioma/estética continúan en P-003/P-015. Las referencias aportan lenguaje visual, no nombres, logos, fotografías ni métricas comerciales.

## Fuente única y adopción segura

Los valores de esta tabla se materializan exclusivamente en las variables del catálogo. Son una **especificación candidata**, no un segundo sistema de producción. En V5, trasladar los roles aceptados a [tokens.css](../frontend/src/shared/tokens.css), exponerlos mediante [tailwind.css](../frontend/src/shared/tailwind.css) y consumirlos desde componentes compartidos. No copiar CSS del catálogo por pantalla ni importar su formulario o datos sintéticos a la app.

Se conservan Segoe UI/fuentes del sistema, escala de espacios, radio base/control y curva vigentes. Se propone separar borde decorativo de borde de control, ampliar semántica de estados, añadir acento/series y neutralizar superficies. El catálogo funciona offline sin fuentes, imágenes, paquetes o peticiones externas. Tailwind 4.3.3 sigue siendo la tecnología aprobada de la app; este archivo HTML de revisión no necesita un nuevo build ni otra dependencia.

## Tokens cromáticos propuestos

Los roles tienen idéntico significado en ambos temas. Un estado siempre incluye texto; un color por sí solo nunca indica éxito, selección, prioridad o error.

| Rol CSS | Claro | Oscuro | Uso y restricción |
|---|---|---|---|
| `canvas` | `#F5F6F9` | `#12171F` | Fondo general; no usarlo como borde de campo. |
| `surface` | `#FFFFFF` | `#1C2430` | Panel de trabajo y superficie de controles secundarios. |
| `field` | `#FAFBFC` | `#151C26` | Interior de campos. |
| `navigation` | `#EEF1F5` | `#171E28` | Navegación y apoyo neutral. |
| `ink` | `#202735` | `#F1F3F8` | Lectura principal. |
| `muted` | `#596273` | `#B0BACB` | Ayudas, texto secundario y placeholder. |
| `border` | `#DCE1E9` | `#354151` | Separación decorativa; no identifica un control por sí solo. |
| `control-border` | `#7A8494` | `#7F8B9E` | Perímetro visible de campos y botones secundarios. |
| `primary` / `primary-hover` | `#146747` / `#0D5238` | `#80D6AE` / `#A0E7C3` | Acción primaria institucional; una por grupo de tarea. |
| `on-primary` | `#FFFFFF` | `#10281D` | Texto sobre acción institucional. |
| `brand-soft` | `#E8F3ED` | `#213B31` | Apoyo institucional, con texto `primary`. |
| `accent` / `accent-hover` | `#6150C8` / `#4F40AE` | `#BAAAFF` / `#CFC4FF` | Acción analítica y marcas; no recolorear todo el shell. |
| `on-accent` | `#FFFFFF` | `#231943` | Texto sobre acento sólido. |
| `accent-soft` / `selected-ink` | `#EEEBFF` / `#4F40AE` | `#322D50` / `#D7CEFF` | Selección y enlaces. |
| `focus` | `#6150C8` | `#BAAAFF` | Contorno de foco 3 px + separación 3 px, sin ocultarlo. |
| `hover` | `#EEF0F5` | `#293344` | Fondo de hover neutral; texto `ink`/`muted`. |
| `success` / `success-soft` | `#146747` / `#E8F3ED` | `#80D6AE` / `#213B31` | Confirmación con texto. |
| `warning` / `warning-soft` | `#805200` / `#FFF4DA` | `#F2CD80` / `#40341F` | Atención y explicación de recuperación. |
| `error` / `error-soft` | `#A52B3A` / `#FFF0F2` | `#FFB2BE` / `#452932` | Error de campo/aviso; no borrar valores. |
| `info` / `info-soft` | `#245B8A` / `#EAF3FB` | `#A5D2FB` / `#233A4E` | Información neutral de estado. |
| `disabled-ink` / `disabled-surface` | `#626B79` / `#E9ECF1` | `#B0BACB` / `#303B4B` | Deshabilitado legible con motivo próximo. |
| `chart-1` | `#6150C8` | `#BAAAFF` | Serie/categoría 1. |
| `chart-2` | `#146747` | `#80D6AE` | Serie/categoría 2. |
| `chart-3` | `#245B8A` | `#A5D2FB` | Serie/categoría 3. |
| `chart-4` | `#805200` | `#F2CD80` | Serie/categoría 4. |

Las series conservan orden, etiqueta y valor, con longitud de marca proporcional. Esta paleta no demuestra que cuatro tonos adyacentes sean distinguibles por sí solos: usar etiquetas directas; V4 debe definir separación, trazos o patrones si requiere una dona o líneas superpuestas. No asignar colores por posición cambiante después de filtrar.

## Tipografía, espacio y geometría

| Token / regla | Valor propuesto | Aplicación |
|---|---|---|
| Familia | `Segoe UI, system-ui, -apple-system, sans-serif` | Una familia de lectura y controles; monospace únicamente para tokens. |
| `text-caption` / `text-label` / `text-body` | 13 / 14 / 15 px | Metadatos, etiquetas y cuerpo; interlineado 1,55. |
| `text-section` / `text-title` / `text-value` | 20 / 32 / 36 px | Títulos y valor principal; interlineado 1,1–1,35. Título móvil 28 px. |
| Peso | 400 cuerpo; 600 etiqueta/acción; 650–700 título/valor | Sin exceso de negritas. Tracking de título −0,03 em; cuerpo normal. |
| Cifras | `tabular-nums` | Valores no se desplazan al cambiar; texto final inmediato. |
| `space-1…7` | 4 / 8 / 12 / 16 / 24 / 32 / 48 px | Escala existente. 8 px entre label/campo; 16–24 px por grupo; 24–32 px entre zonas. |
| `radius` / `radius-control` / `radius-small` | 16 / 10 / 6 px | Panel, control y marca; píldora solo para badges/segmentos breves. |
| Bordes | 1 px normal, 2 px error, foco 3 px + offset 3 px | Borde sutil para separación, `control-border` para límites interactivos. |
| `shadow-panel` | Claro `0 8px 28px #2027350A`; oscuro `0 8px 28px #00000026` | Elevación discreta de panel, sin borde decorativo simultáneo. |
| `shadow-control` | Claro `0 2px 5px #2027350D`; oscuro `0 2px 5px #00000026` | Reservado para control elevado si el piloto lo necesita; el catálogo no lo aplica a todos. |
| Cómoda | Control 44 px; fila padding vertical 16 px | Valor inicial; siempre mínimo 44 px en tablet/móvil. |
| Compacta | Control mínimo 40 px solo ≥1024 px; fila padding vertical 10 px | Menor espacio, mismo tamaño de texto; no comprimir errores/ayudas ni ocultar acciones. El campo medido ocupa 41,25 px por interlineado/padding. |
| `motion-fast` / `ease-out` | 140 ms / `cubic-bezier(.23,1,.32,1)` | Pulsación con puntero fino: translateY 1 px; sin efecto en teclado o movimiento reducido. |

El cambio de tema, tabs, búsqueda y densidad es inmediato. Sin animación de entrada por tarjeta ni carga inventada para fixtures síncronos. El ejemplo de skeleton se identifica como estático y no ejecuta un temporizador. La [matriz V4](ux-ui-roadmap.md#6-movimiento-de-gráficas-e-interfaz) mantiene el requisito de animaciones de gráficas; V2 no prueba ese comportamiento.

## Matriz mínima de componentes

| Familia | Estados cubiertos en el catálogo | Contrato de adopción |
|---|---|---|
| Botón | Primario verde, analítico violeta, secundario, hover, pulsación, foco y deshabilitado | Botón nativo, texto de acción, motivo de deshabilitación próximo; carga real mantiene tamaño y evita envío duplicado. |
| Campo y selector | Label visible, ayuda, placeholder, foco, error asociado, recuperación conservando valor | `aria-invalid`, `aria-describedby`, foco en primer error; no depender de placeholder ni sacudir campo. |
| Tabs | Activo/inactivo y panel asociado; flechas, Inicio/Fin y Tab | Solo tab activo en orden Tab, `aria-selected`, panel oculto fuera de lectura; selección inmediata. |
| Tema y densidad | Botones presionados y estado visible | `aria-pressed`; tema de catálogo no escribe localStorage. La app conserva Claro/Oscuro/Sistema y su persistencia actual. |
| Badge y aviso | Información, éxito, advertencia y error con etiqueta y texto | Nunca solo color. `status` para confirmación real; alerta solo al ocurrir error, sin anunciar todas las muestras estáticas. |
| Fila | Normal, seleccionada textual, nombre extenso, estados Abierta/En espera/Cerrada | Estado y acción no se recortan; futura selección usa patrón accesible apropiado a la lista real. Muestras actuales no son botones falsos. |
| Indicador y gráfica | Total, etiquetas/valores, barras, cero conceptual y no disponible explícito | Mismo universo y unidad; 0 solo si conocido; vacío distinto de error/carga; tabla/lista equivalente desde el primer render. |
| Contenido asíncrono | Skeleton estático rotulado; error con recuperación; vacío con explicación | Carga solo cuando exista trabajo asíncrono real; mantener espacio y valores editados. |

## Composición y navegación propuestas

| Ancho CSS | Regla base para V3 | Comprobación del catálogo |
|---|---|---|
| ≥1024 px | Navegación textual compacta de 208 px, contenido flexible; máximo 1600 px; grupos de trabajo en dos columnas cuando sean legibles. | Marco lateral + paneles, datos/formulario en dos zonas. |
| 704–1023 px | Navegación superior o menú accesible según piloto; conservar etiquetas y acceso a acciones; controles ≥44 px. | Links de sección envuelven; dos zonas sin anchos mínimos rígidos. |
| <704 px | Una columna, acciones envuelven en orden lógico, filas aceptan varias líneas, navegación de alcance visible. | Dos columnas de muestras de color; formularios/datos apilados; sin scroll horizontal del documento. |

Estos puntos de corte responden al contenido del catálogo, no obligan a esconder módulos actuales. V3 fijará el shell de la app conservando las trece rutas y las siete secciones de Ajustes. En Inbox, selección, control humano y acción de volver deben seguir visibles. No cambiar filtros, orden funcional ni ciclo de borradores para acomodar el diseño; la pérdida actual al salir de ruta es un hallazgo V1 y cualquier mejora requiere unidad funcional separada.

## Evidencia y límites

- Comprobaciones estructurales y contraste matemático del catálogo se registran en `.local/ui-v2-evidence/structural.json`; tabla de resultados debajo. No certifican WCAG ni lector de pantalla.
- Navegador del catálogo comprobado por el coordinador después de congelar HTML: 390×844, 768×1024 y 1440×1000, claro/oscuro; seis casos sin overflow horizontal (`scrollWidth = clientWidth`: 375/753/1425 px útiles). Campos cómodos de 44 px y compacto escritorio de 41,25 px. Formulario inválido enfoca campo y asocia error; válido confirma sin guardar; reset recupera muestra. Flechas de tabs actualizan foco/selección/panel; salto a datos enfoca título. Tema independiente vuelve a claro al recargar; consola consultada sin errores/advertencias. Evidencia `.local/ui-v2-evidence/browser.json`, `catalog-light.jpg`, `catalog-dark-data.jpg` y `catalog-mobile-light.jpg`.
- Movimiento reducido revisado en CSS (sin transición/transformación de pulsación); **preferencia del sistema no emulada** en este pase. Sin prueba de lector de pantalla, zoom 200 % o teléfono físico; no conformidad WCAG completa.
- La aplicación conserva sus **59 archivos frontend/backend de código/configuración** del snapshot de separación; no se alteran paquetes, tests, API, persistencia IA ni datos. La preservación por hash no equivale a regresión exhaustiva.
- Pase acotado del coordinador después de separar worktrees: Resumen 4 fichas/2 sin leer → primer hilo; control humano, borrador conservado al ocultar/mostrar ficha y búsqueda vacía. Ajustes cargó revisión persistida 2, IA/salida externa deshabilitadas; sin guardar o invocar proveedor. Consola consultada sin errores/advertencias. Capturas `.local/ui-v2-evidence/app-inbox-after-isolation.jpg` y `app-settings-after-isolation.jpg`. Esto es smoke local, no operación conectada ni suite completa.

### Contraste medido

Comprobados 35 pares por tema, 70 en total, mediante luminancia relativa sRGB sobre los valores hex finales. Texto normal/placeholder: ≥4,5:1; contorno de control/foco/marca frente a superficie: ≥3:1. Los separadores decorativos no se presentan como límites de controles.

| Tema | Mínimo de texto comprobado | Mínimo de contorno/foco/marca comprobado | Resultado |
|---|---|---|---|
| Claro | 4,549:1 | 3,648:1 | Supera los objetivos por combinación usada. |
| Oscuro | 5,792:1 | 4,529:1 | Supera los objetivos por combinación usada. |

Cobertura: `ink`/`muted` sobre canvas/surface/field/navigation/hover; texto de acciones y hover; selección; deshabilitado; estado sobre su fondo; error de campo; foco sobre siete superficies; borde de control sobre surface/field; cuatro marcas sobre surface. El informe conserva cada par, objetivo y razón sin redondear a un aprobado artificial. Estructura: 20 IDs únicos, 16 referencias internas resueltas, cero recursos externos/llamadas de red/almacenamiento. Fuente de app: 59/59 hashes exactos respecto al respaldo previo al aislamiento.

## Estado de salida y continuación

Tabla candidata y catálogo mínimo preparados y comprobados en su alcance local; dirección aceptada por el propietario para V3 el 2026-10-14. V2 define y demuestra fundamentos, **no declara la aplicación rediseñada**. [V3 concreta Resumen e Inbox](design-pilot-v3.md) con estos roles, incluyendo móvil, vacío y texto largo. La integración V5 y la verificación final V7 siguen sus puertas. No se instaló biblioteca, cambió stack, realizó commit/push ni accedió a SIIE o proveedores.
