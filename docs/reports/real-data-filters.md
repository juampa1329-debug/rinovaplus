# Filtros de Clientes y Admisiones — 2026-10-15

**Estado:** implementados y verificados en pruebas automatizadas, SQL local, HTTP y navegador real sobre el preview privado `127.0.0.1:4173`. La aceptación de esta ampliación está completada, incluidos los nuevos filtros y la vista móvil emulada. El corte conserva los contactos, conversaciones, seguimientos y volumen de configuración IA existentes.

## Comportamiento entregado

Clientes busca por nombre o teléfono mientras se escribe, con espera de 300 ms. Etapa, etiqueta, ciudad, tipo de contacto y programa de interés se combinan mediante AND en `/api/local/crm/clients`. El servidor filtra el snapshot completo admitido por el contrato actual; la respuesta filtrada controla únicamente la lista visible, sin reemplazar el propietario de datos de Inbox ni los borradores de las fichas.

Ciudad y tipo proceden de contactos guardados y se comparan sin espacios exteriores ni distinción de mayúsculas. La etiqueta se compara como miembro completo de la lista, no como fragmento. Etapas y etiquetas también conservan las opciones de configuración vigentes. El programa utiliza el catálogo institucional y las representaciones existentes: seleccionar un ID acepta ese ID y los contactos antiguos sin ID cuyo texto coincide; las opciones «texto guardado» seleccionan exclusivamente esos contactos antiguos. No se asignan ni corrigen identidades al filtrar. Una selección de texto conservada sigue enviando su predicado aunque desaparezca de las opciones actualizadas.

Admisiones busca automáticamente por nombre o documento. Programa y «Jornada del programa» se aplican en SQL antes de `OFFSET/FETCH`, siempre dentro de `ACAspirante.Id_Periodo`. `/api/local/admissions/filters` devuelve opciones observadas en aspirantes del período elegido; programa viene de la oferta asociada y jornada de `ACProgramas.Id_Jornada`. No se interpreta esa jornada como asignación individual ni como disponibilidad de una oferta. Se conserva la distinción entre período de aspiración y período de oferta.

Cada cambio de texto, programa o jornada vuelve a la primera página. Cambiar período limpia programa/jornada; restablecer filtros conserva el período elegido. Las consultas anteriores se cancelan y sus resultados se descartan. Los borradores de seguimiento permanecen separados por aspirante/período; los de Clientes y la selección de ficha se conservan. Errores, carga y cero coincidencias se muestran sin datos de respaldo.

## Evidencia por capa

| Capa | Resultado y alcance |
|---|---|
| Backend aislado | 351 pruebas aprobadas: filtros, Admisiones, workspace y contratos. Después del ajuste final de límites compatibles con `Contact`, 45 regresiones enfocadas aprobadas; exportación contractual verificada de nuevo. |
| Frontend aislado | 163 pruebas aprobadas, incluidas 16 enfocadas de Clientes/Admisiones: escritura sin enviar formulario, espera de búsqueda, filtros acumulados, respuestas anteriores, página reiniciada, borradores, conflictos y flujos existentes. |
| Calidad y compilación | Ruff, Prettier, ESLint, TypeScript, build y `git diff --check` aprobados. Normalización anterior a la verificación correspondiente. |
| SQL local | Lecturas con TLS validado: 71 combinaciones de opciones del período activo; una combinación comprobada contra COUNT de SQL produjo 39 aspirantes, 25 en la primera página y 14 en la segunda, sin repetidos entre páginas. Programa, jornada y búsqueda inexistentes devolvieron vacío. |
| HTTP real | Respuestas del preview coinciden con SQL para opciones y combinación programa/jornada. Los dos contactos actuales se comprobaron con filtros acumulativos; los filtros inexistentes devolvieron vacío y conservaron las conversaciones del propietario. No se insertaron registros de prueba. |
| Runtime | Proyecto Docker existente `crm-cbn-integration-20261014`, contenedor preview saludable. Snapshot CRM completo y bytes del volumen IA preservados. Imagen `sha256:a8bf929da951b3392bb864a315dd0a61b0654985368dbccf87e34602f3b5fcfc`; fuente congelada coincide con el runtime. |
| Navegador | Clientes: nombre real sin enviar formulario y cinco selectores combinados devolvieron una fila; búsqueda imposible devolvió cero y restablecer recuperó dos con filtros limpios. Admisiones: programa 100/jornada 1 en período 128 devolvió páginas de 25 y 14; nombre exacto automático devolvió una fila e imposible cero. Restablecer conservó período; seleccionar 127 mostró solo aspirantes de 2026-A. Ambas vistas sin desbordamiento a 390 px; captura de escritorio a 1440 px sobre estado vacío sin datos personales. Se restauraron período 128, búsqueda vacía, 25 filas y viewport normal. Sin escrituras de negocio. |

Evidencia local saneada en `.local/filters-20261015/`: `repository-result.json`, `http-result.json`, `docker-build.json`, `docker-final.json`, `runtime-freeze.json` y `browser-result.json`; captura de estado vacío `browser-admissions-filters.jpg`. Los informes contienen conteos, condiciones, hashes y metadatos técnicos; no se guardaron registros personales ni credenciales.

## Límites conservados

No se modificó el esquema ni el core, ni se crearon alumnos, matrículas o contactos por filtrar. No se añadieron servicios, índices ni migraciones. Clientes mantiene el límite previo del snapshot de 500 contactos/2000 mensajes; escalar esa arquitectura sigue siendo una unidad independiente. Admisiones permanece paginada en servidor y no copia la población a CRM. No hubo commit, push ni despliegue externo.
