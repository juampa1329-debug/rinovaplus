# Inbox R1.1 — operación SQL local

Fecha: 2026-10-15. Implementado y aceptado en la copia local autorizada, incluido navegador real. Sin migración, tablas nuevas, escrituras core, datos demo, proveedores ni canales externos.

## Resultado

Inbox tiene dueño de datos independiente del snapshot de Clientes/Resumen. La bandeja consulta 25 conversaciones por página; cada hilo carga los 50 mensajes más recientes y permite consultar anteriores por cursor `Sequence` bigint. La búsqueda por nombre, teléfono o último mensaje espera 300 ms, cancela solicitudes y descarta respuestas antiguas. Filtros acumulativos de canal, estado, control, lectura y asignación/responsable se ejecutan en SQL antes de paginar. Limpiar filtros conserva la conversación y los borradores.

Tres paneles en escritorio: lista, mensajes y ficha con desplazamiento independiente dentro del alto disponible. Hasta 1100 px se navega por panel con controles accesibles. Fechas originales de SQL se transportan como UTC y se muestran en `America/Bogota`; no se reconstruye una fecha histórica ausente.

La ficha derecha permite editar los mismos campos humanos de Clientes mediante `ClientFields`: nombre visible, teléfono, ciudad, etapa, programa de interés del catálogo, jornada informada, tipo, intereses, etiquetas, notas y campos personalizados existentes. Comparte borradores por ContactId. No divide nombres ni agrega documento/pagos sin contrato. Análisis, puntaje, contexto y recomendaciones IA serán de lectura con evidencia/versiones; hoy muestran su indisponibilidad, sin evaluación simulada.

## Contrato y preservación

- `GET /api/local/crm/inbox`: filtros parametrizados, orden estable y paginación de servidor; búsqueda literal escapa comodines SQL.
- `GET /api/local/crm/inbox/options`: responsables persistidos completos, independientes de la página. «Local» identifica el único origen implementado; el esquema actual no registra canales externos.
- `GET /api/local/crm/inbox/contacts/{id}`: contacto exacto y metadatos de su conversación, sin leer la población global.
- `GET /api/local/crm/inbox/conversations/{id}/messages`: mensajes del hilo, cursor exclusivo y presentación cronológica. El bigint viaja como cadena para conservar precisión.
- `PUT /api/local/crm/inbox/contacts/{id}`, `PUT /api/local/crm/inbox/conversations/{id}` y `POST /api/local/crm/inbox/conversations/{id}/messages`: transacciones existentes con confirmación compacta. No construyen snapshot después de escribir. La huella vincula acción, entidad y cuerpo; el replay devuelve la revisión original registrada. Conflictos 409 mantienen borradores; guardas impiden enviar en modo IA o hilo cerrado. «Mensaje local» sigue sin envío externo.

Tras una escritura confirmada se refresca el dueño de Clientes/Resumen. Un fallo posterior de esa lectura no revoca el éxito de Inbox. El snapshot antiguo mantiene sus límites de 500 contactos/2000 mensajes; R1.1 elimina esa dependencia de las lecturas y escrituras de Inbox, pero no declara resuelta la escala de Clientes/Resumen. El acceso «Ver Clientes» se conserva como navegación adicional; la edición exacta funciona dentro de Inbox aunque el snapshot global falle.

## Evidencia por capa

| Capa | Resultado comprobado |
|---|---|
| Backend | 25/25 pruebas de Inbox/transacción; corrida final conjunta con contratos: **331/331**. No se suman como pruebas distintas. |
| Frontend | Corrida general **166/167**: una prueba antigua consultó la ficha antes de cargar el detalle AJAX. Corregida la espera; corrida enfocada final **10/10**, incluidas búsqueda/carreras, ficha sin snapshot, 409, borradores compartidos, mensajes/control y altura estable al redimensionar con documento desplazado. No se declara una nueva corrida general posterior. |
| Calidad | Formato, lint, tipos, build y exportación canónica comprobados; `git diff --check` sin errores. Normalización anterior a la verificación. |
| SQL real | **16** comprobaciones: filtros, vacío sin fallback, página fuera de población, detalle/fechas/orden y edición compacta/replay dentro de una transacción revertida. Dos conversaciones existentes. Valores, conteos y revisión del workspace conservados; ninguna operación técnica final. El rollback prueba ejecución transaccional, no COMMIT durable nuevo. |
| HTTP real | **18** comprobaciones: resultados de filtros combinados, detalle y mensajes coinciden con SQL; misma población preservada. Sin escrituras de negocio. |
| Docker local | Preview del proyecto existente `crm-cbn-integration-20261014`, puerto privado 4173, imagen `sha256:171d4a06b7616cbac015c447f503170a8bd20b6dfd15eb3deb738a93f4f29dcf`, healthy. Snapshot CRM y volumen IA idénticos; Admisiones operativa, router fixture ausente y fuente congelada sin cambios. |
| Navegador | Aceptados filtros AJAX acumulados, vacío/reset, fechas UTC, borradores por hilo y compartidos con Clientes, descarte y navegación móvil sin desbordamiento horizontal. Escritorio: paneles de 717 px, scroll derecho independiente de documento/lista/mensajes. Se detectó altura móvil dependiente del scroll al redimensionar: corregida con coordenada estable del documento y observación de layout. Reproducción final escritorio desplazado → 390 × 844 → abrir ficha: borde inferior 791 px, dentro de 844. Escritorio final 1440 × 1000 conserva los tres paneles dentro del viewport. Sin escrituras de negocio en estas pruebas. |

Evidencia saneada: `.local/inbox-r11-20261015/repository-result.json`, `http-result.json`, `docker-final.json`, `runtime-freeze.json`, `browser-result.json` y captura segura `browser-inbox-mobile.jpg`. Las suites SQL usan dobles sintéticos solo en pruebas. La población local real es pequeña: paginación y aislamiento más allá del límite se verifican con contratos/dobles; no se afirma carga masiva real ni rendimiento con miles de contactos.

## Continuación

R1.1 no activa tareas, identidad multiusuario, SLA, análisis continuo, riesgo, temperatura ni banco de agentes. R2 requiere identidad y política operativa; R3A puede avanzar con los mensajes locales actuales sin esperar completar R2 o conectar un canal. R4 mantiene análisis durante atención humana y separa estrictamente inferencia de permiso para responder/enviar. Conservar la separación entre campos humanos editables y derivados IA de lectura.
