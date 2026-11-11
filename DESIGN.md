# Diseño vigente — Azul noche · Glass

**Aprobación del propietario, 2026-10-19:** aplicar el diseño aprobado a todo el CRM, conservando funcionalidades, navegación y animaciones. Esta unidad modifica presentación; no incorpora los datos, acciones ilustrativas ni nuevas pantallas del comparador. Los registros históricos siguientes conservan su contexto original.

## Contrato visual aprobado

`frontend/src/shared/tokens.css` define una sola familia azul para todas las rutas. En oscuro: canvas `#061225`, superficie `#12243B`, texto `#EDF4FF`, secundario `#B7C9DF`, acción `#245BDB` con blanco y hover `#2D63E8`; azul `#2F6BFF` y cian `#37C8E8` para las dos primeras series. Materiales de vidrio navy sobre iluminación zafiro estática, borde superior suave y radios principales de 22 px. Navegación/encabezado flotantes, métricas más ligeras y áreas de lectura más opacas; los controles interiores no acumulan capas de vidrio.

Claro conserva una variante azul legible. Claro/Oscuro/Sistema, la clave `crm-cbn-appearance` y su resolución/persistencia permanecen iguales. Tipografía nativa del sistema, sin dependencias ni fuentes externas. Las superficies se vuelven sólidas cuando falta soporte de blur, se solicita menos transparencia o más contraste.

Movimiento: gráficas 240 ms de entrada/actualización, salida 180 ms; panel contextual 180 ms con 4 px de desplazamiento y opacidad 0,45→1. Curvas compartidas, cancelación vigente, teclado/movimiento reducido inmediatos; feedback de pulsación de 120 ms. No se anima blur/sombras ni se añaden bucles.

Los componentes y composiciones funcionales existentes se conservan, incluidos scroll/paginación del Inbox, borradores, operaciones, formularios y avisos de IA. Aceptación por capa y pendientes en [avance](docs/progress.md) y [pendientes](docs/pending.md).

## Historial del diseño provisional

**Estado:** construido para revisión bajo ADR-002, no aprobación visual definitiva. **Modo:** Operate. Fuente: `docs/design-system.md` y mockups existentes; no se reemplaza identidad ni se afirma clonación pixel-perfect.

## Sistema compartido

Paleta institucional verde bosque y superficies claras sobrias; navegación clara integrada y variante oscura con acciones menta. Tokens en `frontend/src/shared/tokens.css`, puente Tailwind en `tailwind.css` y controles comunes en `frontend/src/shared/ui.tsx`. Tailwind CSS 4.3.3 y plugin Vite aceptados por solicitud explícita en ADR-005, sin Preflight ni kit de componentes. Tipografía del sistema, sin descargas o licencias adicionales. Jerarquía centrada en tareas, no decoración o métricas comerciales falsas.

## Composición y flujos

Navegación lateral agrupada, encabezado contextual, aviso permanente de aislamiento. Clientes usa lista y ficha; Inbox bandeja/hilo/contexto; móvil apila superficies sin eliminar estado de control humano. Formulario público tiene composición reducida. Ajustes mantiene siete secciones en orden confirmado. Las expansiones contienen alcance/puertas visibles, no botones falsamente operativos.

## Estados y límites

Foco visible, búsqueda sin resultados, validación asociada a campos, confirmación temporal, botón vacío deshabilitado, cancelación/reset y ruta desconocida. No estados de carga ficticios: fixtures son síncronos. No acceso simulado presentado como sesión real. Apariencia Claro/Oscuro/Sistema con preferencia visual persistida, fallback sin storage y bootstrap previo a React; datos de negocio y borradores siguen exclusivamente en memoria de esta pestaña. Tema visual e idioma de preview pendientes de aceptación humana final. Navegador y aprobación humana se registran por separado.

## Refinamiento ADR-005

Iconografía SVG compartida, grupos y selección legibles, filas de atención con identidad ficticia y superficies de prioridad diferenciada. Tailwind consume tokens únicos. Feedback de 150–160 ms en controles y selección; sin entradas animadas en navegación habitual. Movimiento reducido elimina desplazamiento de pulsación; teclado conserva foco visible. No se añaden métricas, capacidades ni afirmaciones operativas.

## Ampliación funcional local de fase 3

Se conserva modo Operate, identidad/tokens/fonts y aprobación provisional. Inbox mantiene tres zonas: estado/asignación/prioridad cerca del hilo; tareas y timeline en disclosures del contexto. Plantilla de respuesta vive cerca del compositor, con aviso no-modelo, revisión humana y copia local separados de añadir. Asistente presenta configuración compartida IA y preview ficticio; móvil apila ambos sin eliminar controles. Sin nuevas imágenes, iconos, fuentes o dependencias. Navegador de este corte se registra en informe 3; no aprobación humana final.
