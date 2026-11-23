# Inbox · Navegación responsive

El titular reporta una ventana estrecha con el menú flotante abierto sin cierre accesible y sin una forma clara de volver a la lista de conversaciones. La captura ronda790px: el menú móvil se activa hasta900px, pero el botón interno de plegar estaba oculto y el retorno al Inbox sólo se mostraba hasta759px.

Se añade cierre dentro del panel, fondo clicable, Escape, foco inicial y retorno al botón que abrió el menú. El foco de teclado permanece en el panel abierto y el contenido principal queda inert; el scroll anterior se restaura al cerrar. Cambiar a escritorio cierra el panel. Pulsar el enlace de la sección actual también lo cierra, sin depender de hashchange. La preferencia de plegado de escritorio se conserva.

El Inbox usa una columna hasta900px. Con una conversación seleccionada oculta el listado y ofrece «Volver a conversaciones», visible y sticky dentro del panel. El borrador sin enviar se conserva al volver y reabrir el chat; la acción no envía mensajes ni cambia el modo IA/Humano. Entre901y1199px permanece el listado junto al detalle; desde1200px se conserva el diseño amplio.

Validación:46pruebas frontend seleccionadas pasan; tipos y lint pasan. Build institucional con vite.workspace.config.ts pasa (advertencia histórica de bundle). Sin cambios de backend, credenciales, límites, agentes ni permisos. Publicación y verificación visual en el navegador del titular pendientes al preparar este corte.

Los envíos de PRE-ICFES, su ficha y el diagnóstico de nombres de Instagram se mantienen como trabajo separado pendiente de acceso efectivo al navegador. No se acreditan mensajes enviados ni cambios académicos por este arreglo de navegación.
