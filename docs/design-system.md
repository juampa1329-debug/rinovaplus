# Un solo sistema visual

## Identidad RinovaPlus · revisión local del 2026-11-15

La referencia del propietario fija verde petróleo `#12343B`, lima `#C4F04D`, blanco cálido `#F5F7F2`, gris petróleo `#52666B` y blanco `#FFFFFF`. El esquema claro y oscuro deriva de esos colores mediante los tokens semánticos de `frontend/src/shared/tokens.css`. Manrope y Source Sans 3 se sirven desde el paquete de la aplicación.

La marca combina el rinoceronte, «RinovaPlus» y «CRM inteligente de CBN». El acceso incorpora «La fuerza de conectar.» y el crédito «© 2026. Software desarrollado por la Corporación Bolivariana del Norte - CBN.» El nombre del producto se usa también en la API, la confirmación de Canales, los nuevos registros del autenticador y la descarga de destinatarios.

## Dirección anterior aprobada — 2026-10-19

El propietario aprobó **Azul noche · Glass** y su aplicación exclusivamente visual a todo el CRM. Sustituye la combinación de acción verde/menta y selección violeta del piloto. Los apartados posteriores se conservan como historial; no definen los colores vigentes.

Fuente única: `frontend/src/shared/tokens.css`, consumida por Tailwind y los estilos compartidos de todas las rutas. Oscuro usa canvas `#061225`, panel `#12243B`, superficie interior navy, texto `#EDF4FF`, secundario `#B7C9DF`, acción `#245BDB`/blanco y hover `#2D63E8`. Enlaces/foco tienen azul claro legible. Series: `#2F6BFF`, `#37C8E8`, `#7CA4FF`, `#537DA8`; los colores semánticos de éxito/advertencia/error conservan su función y sus etiquetas.

Materiales: vidrio navy con blur de 18–24 px y saturación 145–150 %, luz estática detrás del shell, borde superior y sombra discretos, radios principales de 22 px. La navegación flota; las métricas son más luminosas que los paneles de datos. Controles y paneles anidados permanecen sólidos. Fallback opaco para falta de `backdrop-filter`, transparencia reducida y contraste alto. El modo claro adapta la misma familia azul sin cambiar la preferencia Claro/Oscuro/Sistema, almacenamiento ni listeners.

Movimiento aprobado: entrada/actualización de gráficas 240 ms, salida 180 ms, paneles 180 ms/4 px/opacidad 0,45→1, pulsación 120 ms. Se reutilizan cancelación, curvas y salida inmediata para teclado/movimiento reducido. No se cambian rutas, cálculos, datos, solicitudes, handlers ni reglas de disponibilidad. La propuesta ilustrativa no se convierte en fixtures del producto.

Esta aprobación del diseño no equivale a conformidad WCAG certificada ni a validación conectada. Pruebas, conservación de fuentes y aceptación en navegador se registran por separado en [avance](progress.md).

## Antecedentes conservados

[Roadmap UX/UI y movimiento](ux-ui-roadmap.md): propuesta de refinamiento por cortes, comenzando con Resumen e Inbox; dirección del piloto aceptada e implementada; aceptación global pendiente.

**Fundamentos V2 preparados (2026-10-14):** [tabla candidata y contratos de componentes](design-foundations-v2.md), con [catálogo independiente claro/oscuro](previews/v2-foundations.html). Propone superficies neutrales, identidad verde y acento violeta; incluye 70 pares de contraste comprobados. La dirección fue aceptada para el piloto y se adoptó en [V5](design-integration-v5.md) con alcance Resumen/Inbox; [V6](design-extension-v6.md) extiende esos roles a Clientes, Asistente y Ajustes. Las tablas históricas siguientes permanecen como contexto de los mockups.

**Estado:** contrato de consistencia documentado y dirección **“Institucional sereno” propuesta para los mockups**. Tailwind y refinamiento claro/oscuro autorizados en [ADR-005](decisions/ADR-005-tailwind-appearance.md); aprobación visual definitiva e idioma UI pendientes (**P-003/P-015**). Tokens y controles compartidos en `frontend/src/shared/`; no hay marca oficial disponible ni aprobación visual final.

## Historial de implementación de apariencia — ADR-005

**Adopción vigente V5/V6:** `tokens.css` incorpora la paleta V2 aprobada en `.pilot-shell`: canvas claro `#F5F6F9`, oscuro `#12171F`, superficies blanca/`#1C2430`, acento violeta `#6150C8`/`#BAAAFF` y acción verde/menta. Resumen, Inbox, Clientes, Asistente y Ajustes usan estos roles y composición compartida. V6 ajusta gráficas WAAPI a **450/350/250 ms**, paneles a **300 ms** con `--ease-drawer`, tema a **300 ms**; teclado/reducción instantáneos, texto y navegación inmediatos. Los borradores de Inbox y del espacio de trabajo pertenecen a dueños efímeros sobre las rutas; [contrato V6](design-extension-v6.md). No hay nuevas dependencias; módulos fuera del corte conservan su presentación previa.

Tailwind CSS y plugin Vite 4.3.3 fijados. `tokens.css` es la fuente cromática; `tailwind.css` los expone a utilidades y `styles.css` conserva composición específica con componentes `@apply`. Sin Preflight, librería UI ni runtime de animación. Navegación clara `#EDF2EF`, canvas claro `#F4F6F5`, acción `#146747`; canvas oscuro `#111C1B`, superficie `#1A2925` y acción menta existente. Las tablas siguientes conservan referencias históricas de mockup, no sustituyen los tokens actuales.

Selector Claro/Oscuro/Sistema persistido únicamente como apariencia; datos de negocio temporales. SVG de trazo compartido, feedback 150–160 ms y movimiento reducido. Formato/lint/tipos/64 tests/build y detector mecánico comprobados. Navegador del refinamiento y aceptación humana se registran aparte. Las afirmaciones posteriores de selector temporal describen el prototipo anterior a ADR-005.

## Referencia visual propuesta — no aprobada

Una única dirección para los 12 módulos: navegación sobria, superficies claras, jerarquía funcional y datos legibles; sin logos inventados, ilustración decorativa ni estilos independientes por módulo. Usar solo texto **CRM CBN**, que no constituye un logotipo oficial.

| Token semántico propuesto | Valor de referencia | Uso previsto |
|---|---|---|
| navigation | `#102D29` | Navegación institucional verde bosque. |
| primary | `#176B52` | Acción primaria/foco de tarea. |
| active | `#DDECE4` | Selección menta. |
| canvas | `#F5F6F2` | Fondo general blanco cálido. |
| surface | `#FFFFFF` | Paneles/formularios. |
| ink | `#172D27` | Texto principal. |
| muted | `#65746D` | Texto secundario; validar contraste por uso. |
| warning | `#A96917` | Advertencia acompañada de texto/icono. |
| error | `#B74242` | Error acompañado de texto/icono. |

Tipografía de referencia: **sans serif moderna y neutra**; no se elige ni instala una fuente/dependencia nueva. Espaciado consistente, bordes suaves y elevación mínima como lenguaje de mockup; valores definitivos y contraste por combinación pendientes. Estos valores son especificación visual, no código ejecutable ni afirmación de accesibilidad certificada.

- Marco de referencia de escritorio: **1440 × 1024**. Formulario público M-05: **390 × 844**, portrait móvil.
- Idioma de etiquetas del preview: español neutral **propuesto**, todavía no estándar definitivo aprobado.
- Shell compartido de escritorio: navegación lateral, encabezado con contexto/estado y zona de trabajo. Acceso y formulario público usan composiciones reducidas, no el menú de administración.
- Una sola imagen principal por módulo. Resolución del archivo generado se comprueba al recibirlo; no confundir marco de diseño con resolución física del PNG.
- Los datos/nombres/métricas son ficticios y deben indicar “Datos de demostración”. Ningún contador o estado representa DB/proveedor conectado.
- El mapa especifica variantes responsive y estados; una imagen no prueba teclado, lector de pantalla, mobile ni comportamiento.

Ver [mapa por pantalla](design/module-map.md) y [aprobación](design/approval.md).

## Variante oscura propuesta — no aprobada

[Galería oscura](design/dark-mode.md) de los mismos 12 módulos, conservando la propuesta clara y sin ampliar funciones. Valores de referencia empleados en los [prompts](design/generation-prompts-dark.json); los tokens provisionales de aplicación son independientes de los píxeles de esos PNG, no se afirma igualdad exacta.

| Token de referencia | Valor propuesto | Uso |
|---|---|---|
| background | `#101918` | Fondo general oscuro. |
| sidebar | `#091412` | Navegación. |
| surface | `#192522` | Paneles. |
| field | `#111D1A` | Campos/superficies interiores. |
| border | `#30413B` | Separadores. |
| text | `#F0F5F1` | Texto principal. |
| muted | `#ABBAB2` | Texto secundario. |
| action | `#80D6AE` | Acción principal. |
| actionText | `#10281D` | Texto sobre acción. |
| selectedNavigation | `#274F3E` | Selección de navegación. |
| selectedText | `#D3F7E4` | Texto de navegación seleccionada. |

Tipografía/distribución/contenido/estados siguen la propuesta existente; el prototipo local usa fuentes del sistema y selector claro/oscuro temporal; no se elige una biblioteca UI ni tema definitivo. Error/advertencia mantienen distinción semántica con texto/icono; contrastes concretos por combinación se validarán antes de UI. Los modos claro y oscuro tienen aprobación independiente pendiente; la petición de ver una variante no selecciona un tema definitivo.

## Fuente única obligatoria al implementar

- Un catálogo compartido de tokens semánticos: color, tipografía, espacios, radios, elevación, breakpoints y movimiento. Tema institucional aprobado, no paletas inventadas por pantalla.
- Un solo origen de componentes: botones, campos, validación, tablas, diálogos, navegación y estados. Una funcionalidad consume estos componentes, no copia su CSS.
- Una biblioteca de UI, si se aprueba, sin mezclar kits. Extensiones justificadas en ADR; versión fijada, licencia y accesibilidad revisadas.
- Mismos patrones para carga, vacío, error, éxito, permisos y confirmación de acciones sensibles. Datos del SIIE se distinguen de recomendaciones/resúmenes IA.
- Sin estilos sueltos/valores mágicos repetidos; excepciones locales justificadas y sin duplicar tokens. Cambios globales se revisan en todas las pantallas representativas.

## Antes de escribir UI

[ADR-002](decisions/ADR-002-local-functional-skeleton.md) autoriza exclusivamente el prototipo local funcional con estos tokens propuestos y español neutral de preview. La muestra de bandeja/formulario se construye ahora para revisión; no representa aprobación definitiva de marca, tema, idioma o conformidad accesible. Antes de funciones conectadas, aceptar dirección, marca/logo, idioma, tipografía/licencias, contraste, densidad, móviles y escritorio. No usar el prototipo como prueba de DB/API o negocio.


## Aceptación propuesta

| Área | Comprobación |
|---|---|
| Accesibilidad | Objetivo WCAG 2.2 AA propuesto: teclado, foco visible, etiquetas, errores asociados, contraste, lector de pantalla y movimiento reducido. Declarar conformidad solo tras evaluación. |
| Responsive | Formulario y control humano útiles en móvil/escritorio; tabla densa con alternativa o scroll controlado, sin perder acciones. Tamaños exactos se aprueban en la muestra. |
| Componentes | Inventario/estados y ejemplos compartidos; prueba visual de pantallas representativas tras modificar tokens. |
| UX segura | Aviso de IA, transferencia humana, baja/consentimiento y tratamiento de datos comprensibles; evitar acciones irreversibles ambiguas. |

Aprobar este contrato y la dirección visual en un ADR antes de implementación. El objetivo de accesibilidad no es todavía una certificación. Consultar [pendientes](pending.md) y [reglas](development-rules.md).
