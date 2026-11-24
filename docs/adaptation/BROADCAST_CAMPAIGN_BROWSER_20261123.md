# Listado de campañas compacto — 23/11/2026

El listado sin límite de altura extendía la página completa y mezclaba campañas en curso, borradores y finalizadas. Se incorpora un explorador lateral con búsqueda por nombre/programa (ignora tildes y mayúsculas), grupos Todas/Actuales/Borradores/Finalizadas con contadores, orden por estado y actividad, actividad reciente o nombre, y páginas de 25. Actuales incluye en curso, programadas y pausadas; Finalizadas reúne completadas y canceladas. Los contadores de grupo reflejan el catálogo completo; el rango inferior refleja la búsqueda aplicada.

La lista tiene desplazamiento independiente y altura máxima vinculada a la ventana. El control Ocultar listado amplía el detalle a todo el ancho; al mostrarlo se conservan búsqueda, filtros, orden y página. Filtrar u ocultar no cierra la campaña ni descarta ediciones sin guardar. La selección sigue pasando por la guarda nativa de navegación, y los estados proceden del backend, sin efectos sobre envíos o destinatarios.

Se conserva la paleta institucional (superficie #ffffff, borde #d5ded6, acento #35696b, activo #e4efdc y tinta institucional), fuentes existentes y variantes oscuras por tokens. Una columna bajo 850px; foco visible, región de desplazamiento accesible por teclado, estado seleccionado y botones de paginación identificados. No se añaden animaciones decorativas ni métricas inventadas.

Validación: 28 pruebas frontend pasan, incluidas navegación por 100 campañas, búsqueda en otras páginas, tildes, estados, refresco con menos resultados, colapso y conservación de borrador sin guardar. TypeScript, ESLint de archivos cambiados y workspace build pasan; se conserva advertencia histórica de bundle. Publicación y comprobación visual real pendientes en este corte. Sin cambios de backend, DDL, seeds, servicios, SIIE, modelos ni campañas activadas.

## Publicado y comprobado en vivo

`54c3157` publicado por webhook en Coolify `zipjnxttbcgqb2xza1lz6rsc`: Success, 43 segundos, inicio 24/11/2026 03:20:05 UTC (23/11, 22:20:05 Bogotá), contenedor saludable. No requirió redespliegue del backend.

Catálogo real: 26 campañas, incluidas pruebas históricas; 21 borradores y cinco finalizadas, ninguna actual. Se comprobó segunda página con la campaña 26, filtro Finalizadas con cinco resultados y búsqueda «logistica» que encuentra «Logística». Elegir filtros y ocultar/mostrar conserva el detalle abierto y el texto de búsqueda. Desplazamiento por teclado comprobado: lista de 358px, contenido de 2163px y scrollTop 1805 al final; 25 filas por página. Se deja abierta Logística con Finalizadas seleccionado. Sin guardar documentos de campaña ni realizar envíos durante estas comprobaciones.

Captura privada `.local/campaign-browser/campanas-organizadas.jpg`. El ajuste temporal de viewport no se reflejó en el ancho DOM de esta superficie (continuó 1265px); se restableció antes de cerrar. Se acredita validación visual en escritorio; la regla de una columna bajo 850px está implementada sin acreditar una comprobación visual móvil efectiva. Las pestañas temporales de comprobación se cerraron.
