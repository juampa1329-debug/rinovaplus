# PRE-ICFES: autorización de lanzamiento y destinos alternativos

## Publicado y activado — corte 25Nov2026 20:25:20 UTC

Código c6c3314 integrado en 77c6524 y publicado en ambas ramas. Backend Coolify k73kwhp7watoeq16jmfrh0il: comprobación ready/healthy, actualización completada, 4m23s. Frontend 77c6524: Success por webhook, 43s. Se preservó la integración SIIE ya publicada en la rama remota; este ajuste no la modifica.

Revisión nativa completada: 100 destinos principales habilitados y dos teléfonos alternativos vinculados a sus mismas fichas, cero casos nuevos para revisión. Los archivos de selección descargados de los recibos fijan 100 y dos identidades respectivamente. Contraste local: los 100 contactos coinciden exactamente con el lote revisado; los dos contactos alternativos pertenecen a ese lote, sus identidades son distintas y los CSV contienen 102 números únicos. El titular de la prueba no está en estas campañas. El único caso de celular incompleto permanece fuera.

Campaña principal de promoción: En curso, versión 3, 100 elegibles de 100 y cero excluidos. Campaña complementaria de teléfonos alternativos: En curso, versión 1, dos elegibles de dos y cero excluidos. Ambas usan cbn_preicfes_promocion_juan_pablo_v1, español, Aprobada por Meta; primer nombre, cuenta CBN y etapa Seguimiento tras recibo real. La principal requirió revisar y guardar la versión vigente de plantilla antes de obtener la audiencia elegible. Se preparó y activó una vez cada campaña, sin reintentos de mensajes.

Corte CSV inicial: principal con un Entregado, un Enviado, un Aceptado y 97 Preparados; máximo un intento por destinatario. Complementaria con dos Preparados y cero intentos. Las dos están activas, pero esto no acredita entrega total ni envío de los números alternativos todavía. Se conserva la cadencia de 1.000 por 24 horas y 30 segundos entre mensajes, compartida con las demás campañas de la cuenta.

El modal de una entrega real muestra la información solicitada PRE-ICFES, etapa actual Seguimiento y objetivo Seguimiento, mensaje con cabecera y botones legibles; no JSON. El panel de gráficos real muestra 100 destinatarios, un recibo de entrega y cero lecturas o respuestas atribuidas en este corte. Una lectura requiere recibo de Meta; no hay métrica independiente de apertura ni clics externos. El titular confirmó que la IA respondió a la prueba; no se infiere respuesta de IA de los destinatarios comerciales todavía.

Evidencia agregada: artifacts/live/preicfes-campaign-launch-20261125.json. CSV, selecciones de destinos, capturas textuales y recibos nominales permanecen sólo en .local/preicfes-import-20261125/. Las secciones siguientes conservan el corte anterior de preparación.

El titular autorizó activar la campaña después de recibir la prueba y confirmar que la IA atendió su respuesta. La plantilla nueva fue sincronizada desde Meta como Aprobada; una prueba aislada al titular obtuvo entrega y lectura con un solo intento. Su permiso temporal se revocó al terminar. La cuenta conservó cadencia habilitada, máximo 1.000 por 24 horas e intervalo de 30 segundos, sin cambios por esta prueba.

Se vincularon por la función nativa las 100 fichas seleccionadas: 100 procesadas, 100 habilitadas y cero para revisión en esa operación. La evidencia registra la declaración previa del titular sobre políticas y el formulario disponible, sin atribuir al agente una verificación jurídica independiente. La vigencia operativa revisada es el 25/11/2026 a las 23:59 America/Bogota. El caso de celular incompleto permanece excluido. Esto por sí solo no acredita mensajes ni activación de la campaña.

## Selección de destinos y segunda campaña

El motor conserva un mensaje por ficha y campaña. Para cumplir la instrucción expresa de contactar dos números en dos casos, se prepara una campaña principal de 100 destinos y una complementaria de dos destinos alternativos, ambas con la misma plantilla. Se conserva una sola ficha comercial por persona y no se cambia la deduplicación global.

La selección de campaña admite ahora destinos de cuenta exactos, además de los contactos. El servidor comprueba institución, cuenta, contacto elegido, existencia y un solo destino por ficha en cada campaña al guardar y al recalcular la audiencia. El SQL mantiene ambos filtros; no sustituye consentimiento, bajas, control Humano, exclusión SIIE o validación de la plantilla. El formato nuevo de archivo evita que una interfaz antigua ignore la restricción de destinos. La interfaz permite descargar las rutas principales y alternativas desde recibos nativos completados.

La vinculación adicional requiere un celular colombiano distinto del principal, una ruta principal ya existente de la misma cuenta/ficha y una conversación importada vacía en IA, sin cierre, unificación ni intervención posterior. Un número vinculado o declarado en otra ficha queda para revisión. Se reutiliza la conversación de la persona, sin crear otra ficha ni un evento entrante. Cada identidad adicional tiene autorización propia; no se sustituyen revocaciones ni bajas. La operación mantiene el intento idempotente y las transacciones nativas de consentimiento.

## Validación preparada

Pasan 161 pruebas backend seleccionadas, 33 frontend, tipos y ESLint; Ruff pasa en los módulos nuevos, la vinculación modificada y las pruebas nuevas. Nueve sentencias nuevas se tradujeron y parsearon como PostgreSQL sin conexión de negocio. La compilación institucional pasa con el aviso histórico de tamaño del bundle. Las selecciones previas de pruebas se solapan y no se suman como suites independientes.

Publicación de este ajuste, vinculación de los dos números, selección de rutas y activación real todavía pendientes en este corte. No se acredita el envío comercial por la prueba al titular. Fuentes, números, textos y recibos nominales sólo en `.local/preicfes-import-20261125/`. Sin DDL, seeds, nuevos servicios, cambios de modelo o escrituras SIIE; aceptaciones previas conservadas.
