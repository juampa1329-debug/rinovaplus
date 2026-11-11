# V6 — Clientes, Asistente y Ajustes en la aplicación local

**2026-10-14 · Rama `codex/disenos-ui`.** El propietario aceptó V5 y autorizó extender el diseño a Clientes, Asistente y Ajustes, conservando funciones y borradores, con transiciones más lentas y naturales. Este corte modifica únicamente frontend y documentación; no incorpora código de otros chats ni cambia backend, proveedores, dependencias, SQL, Git o despliegues.

## Resultado

Abrir `http://127.0.0.1:5173/#/clients`. Las tres rutas adoptan los roles claros/oscuros V2 usados por V5: superficies neutrales, acento violeta para selección, verde para acciones, bordes de formulario visibles y espaciado compartido. Clientes reúne lista, filtros, ficha y configuración CRM existente; indica borradores pendientes sin repetir el encabezado principal. Asistente conserva configuración compartida y ejemplo local en columnas adaptables. Ajustes conserva las siete secciones IA, Canales, APIs, Diagnóstico, Usuarios, Perfil y Seguridad, con navegación horizontal desplazable en móvil.

La plantilla de Asistente sigue siendo una demostración determinista con revisión humana; no se incorpora una conversación de IA de otro worktree. Las operaciones futuras siguen identificadas como pendientes. El panel IA conserva sus controles de proveedor, modelos, fallback, parámetros, prompt, revisión de errores y prueba explícita. Un backend no disponible muestra el error y la acción de cargar; no se simula conexión.

## Estado, edición y guardado

`WorkspaceSessionProvider` se monta en App por encima de las rutas y dentro del reinicio de demo existente. Convive con `InboxSessionProvider`; las pantallas se desmontan normalmente. No se duplican páginas ocultas ni se añaden localStorage/sessionStorage para datos o credenciales.

| Estado | Conservación | Descarte o guardado |
|---|---|---|
| Ficha editada | Mapa por ID, incluida una clave independiente para la ficha nueva; selección y filtros locales. | Guardar valida y actualiza solo esa ficha. Cancelar descarta solo el borrador actual. |
| Campos personalizados y configuración CRM pendiente | Valores dentro del borrador de ficha y campos de edición de etapas/etiquetas/definiciones en RAM. | Acciones existentes mantienen validación y confirmación; no se guardan al navegar. |
| Configuración de plantilla / perfil | Sigue en el dueño App ya existente y se comparte entre Asistente y Ajustes. | Guardar, descartar y revisar continúan separados; editar invalida revisión incluso si se restaura el texto anterior. |
| Respuesta de plantilla | Por contexto Asistente/Inbox y contacto, con cuerpo/revisión vinculados al binding actual. | Cambio de configuración, datos guardados, mensajes o revisión operativa invalida la respuesta derivada; no se reutiliza como manual. Cambiar de destinatario conserva cada respuesta aún válida. |
| Ajustes IA pendientes | Snapshot, borrador no secreto, catálogo, prompt sintético, resultado/historial y estado de solicitud comparten dueño sobre las rutas. | Guardar/descartar/recargar/probar siguen explícitos. Recargar con cambios mantiene confirmación. El aviso antes de salir del navegador permanece activo incluso fuera de Ajustes. |
| Solicitud IA ya iniciada | Volver a la ruta conserva estado ocupado; resolver actualiza el mismo dueño. | Confirmar restablecimiento remonta dueño. Una resolución antigua no repuebla una sesión nueva. No se cancela retroactivamente una escritura explícita ya enviada. |

Navegar, cambiar tema o sección no guarda ni descarta borradores. **Recargar la pestaña o confirmar Restablecer demo descarta datos efímeros**; cancelar restablecimiento los conserva. Los ajustes IA ya guardados mantienen su persistencia previa en backend y no se borran con el reset de demo. No se incorporan campos de credencial: siguen configurándose por el entorno del backend. La preferencia de tema conserva su almacenamiento previo.

## Ritmo y accesibilidad del movimiento

| Efecto | Tiempo nominal | Curva / comportamiento |
|---|---|---|
| Entrada de marcas de gráficas | 450 ms | `--ease-drawer: cubic-bezier(.32,.72,0,1)`, recorrido más gradual. |
| Actualización de barras | 350 ms | `--ease-in-out` existente; texto final inmediato. |
| Salida de gráficas | 250 ms | `--ease-out`; capa inerte, sin puntero ni foco, navegación inmediata. |
| Entrada de panel de Clientes o sección Ajustes/Asistente | 300 ms | Opacidad .8→1 y desplazamiento de 6 px→0; misma curva drawer. |
| Cambio cromático de tema | 300 ms | Fondo/color/borde explícitos, sin `transition: all`. |

Se respeta la solicitud de un ritmo más pausado. La curva de entrada distribuye mejor el recorrido que simplemente prolongar la curva anterior, que terminaba gran parte del recorrido al principio. No hay rebote, escala, desplazamiento de layout ni animación de cada pulsación. Las entradas se disparan por ruta/sección, nunca por escribir, filtrar o cambiar tema. Las cifras no cuentan desde cero; la dona cambia proporciones inmediatamente y conserva entrada/salida, sin atribuir interpolación visible a sus proporciones.

Teclado y preferencia reducida usan estado final instantáneo. El observador compartido cancela efectos al usar teclado, ocultar la pestaña o activar reducción; desmontaje y reentrada cancelan efectos pendientes. No se espera al final de una animación para operar controles. Se conservan foco visible, textos de estado y acciones existentes.

## Comprobación y límites

Línea base: **74 pruebas/9 archivos**, formato, lint, tipos y build aprobados. Snapshot **78 rutas únicas** y copias previas en `.local/ui-v6-evidence/before/`; hashes en `baseline.json`. Ajustes IA capturados solo como existencia/hash en `ai-settings-before.json`, nunca como contenido.

**Comprobación final: 80/80 pruebas en 10 archivos**, formato, lint, TypeScript y build aprobados. Registro en `.local/ui-v6-evidence/final-check.log`. Las seis pruebas nuevas cubren fichas A/B/nueva y campos personalizados entre rutas/tema, ausencia de guardado implícito, cancelar/reset, plantilla por destinatario y su invalidación, duración/limpieza de panel sin reanimación al escribir, ajustes IA entre desmontajes, catálogo sin recarga implícita y promesas en vuelo frente a un nuevo dueño. Las pruebas previas mantienen controles, validaciones, tareas, comentarios, navegación y barreras de IA.

| Capa | Resultado final | Evidencia y límite |
|---|---|---|
| Preservación independiente | **62/62 archivos protegidos exactos**: 61 rutas del baseline intactas y hash de ajustes IA. 17 cambios de baseline intencionales; cuatro archivos nuevos de producto/prueba/informe. | `independent-verification.md`, `independent-preservation.json`. Backend, contratos, dependencias/configuración, dominio y previews anteriores intactos; índice vacío. |
| Navegador responsive | **24 combinaciones sin overflow**: 18 Clientes/Asistente/Ajustes × claro/oscuro × 390/768/1440 px, más seis con IA extensa. | `browser-verification.json`; capturas claras/oscuras y tres móviles en `.local/ui-v6-evidence/`. No dispositivo físico. |
| Borradores y controles | Fichas A/B/nueva separadas; guardar B y cancelar A actúan por ficha. Etapa/etiqueta CRM pendientes, plantilla compartida, perfil y sección sobreviven rutas/tema. | Recorrido real local con datos sintéticos. Las siete secciones conservan los recuentos de controles del baseline. |
| Movimiento | Panel .8/6 px→1/0 observado; escritura no repite entrada; tema computado 300 ms. Gráficas conservan entrada/salida observables e inert→hidden. | Teclado inmediato comprobado en pestaña de carga fría. Reducción solo automatizada. No se atribuye FPS ni rendimiento de dispositivo. |
| Corrección y consola | Perfil distingue su borrador de cambios de IA; la corrección fue comprobada. Consola de carga fría sin errores. | Durante HMR hubo discrepancia de teclado que desapareció en carga fría; no se presenta como fallo del producto final. |
| Documentos | 167 enlaces locales válidos en seis documentos; diff sin errores de whitespace. | `docs-check.json`; readback del informe y estado del roadmap. |

El backend permaneció apagado en la prueba visual: se conserva el error explícito y la acción de cargar. Pruebas de contratos IA usan mocks controlados; no se ejecutaron proveedores reales. Una recarga de la pestaña original fue rechazada por la revisión automática para proteger sus borradores; se usaron pestañas nuevas, sin forzar esa recarga ni descartar trabajo previo. Por ello, el reinicio completo de dueño en V6 se acredita mediante pruebas automatizadas y no como una recarga manual nueva de la pestaña original.

La suite inicial reveló selectores nuevos que no coincidían con las etiquetas existentes; se corrigieron los tests sin renombrar controles. Una sustitución accidental en un fixture convirtió el nombre de un modelo en regex; se restauró el fixture antes del check final. La revisión visual detectó que el aviso de Perfil hablaba de una plantilla y reflejaba cambios de IA; se corrigió para comparar solo los campos de la sección y se añadió prueba específica. Guardado y revisión mantienen sus contratos anteriores. No se alteraron validaciones para lograr aprobación.

El build pasa de CSS 35,87 kB / JS 320,97 kB a CSS **39,42 kB / JS 323,57 kB**; gzip 7,88→8,41 kB y 98,48→99,45 kB. No se añaden paquetes.

**Siguiente unidad:** V7 para accesibilidad ampliada, aceptación visual final y evidencia del corte. Zoom 200 %, lector de pantalla, dispositivo físico y medición de rendimiento siguen pendientes. El tamaño del build no acredita FPS ni fluidez en dispositivos reales. P-003/P-015 y aprobaciones de marca/idioma mantienen su alcance pendiente.
