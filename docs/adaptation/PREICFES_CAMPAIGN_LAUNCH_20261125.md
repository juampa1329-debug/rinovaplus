# PRE-ICFES: autorización de lanzamiento y destinos alternativos

El titular autorizó activar la campaña después de recibir la prueba y confirmar que la IA atendió su respuesta. La plantilla nueva fue sincronizada desde Meta como Aprobada; una prueba aislada al titular obtuvo entrega y lectura con un solo intento. Su permiso temporal se revocó al terminar. La cuenta conservó cadencia habilitada, máximo 1.000 por 24 horas e intervalo de 30 segundos, sin cambios por esta prueba.

Se vincularon por la función nativa las 100 fichas seleccionadas: 100 procesadas, 100 habilitadas y cero para revisión en esa operación. La evidencia registra la declaración previa del titular sobre políticas y el formulario disponible, sin atribuir al agente una verificación jurídica independiente. La vigencia operativa revisada es el 25/11/2026 a las 23:59 America/Bogota. El caso de celular incompleto permanece excluido. Esto por sí solo no acredita mensajes ni activación de la campaña.

## Selección de destinos y segunda campaña

El motor conserva un mensaje por ficha y campaña. Para cumplir la instrucción expresa de contactar dos números en dos casos, se prepara una campaña principal de 100 destinos y una complementaria de dos destinos alternativos, ambas con la misma plantilla. Se conserva una sola ficha comercial por persona y no se cambia la deduplicación global.

La selección de campaña admite ahora destinos de cuenta exactos, además de los contactos. El servidor comprueba institución, cuenta, contacto elegido, existencia y un solo destino por ficha en cada campaña al guardar y al recalcular la audiencia. El SQL mantiene ambos filtros; no sustituye consentimiento, bajas, control Humano, exclusión SIIE o validación de la plantilla. El formato nuevo de archivo evita que una interfaz antigua ignore la restricción de destinos. La interfaz permite descargar las rutas principales y alternativas desde recibos nativos completados.

La vinculación adicional requiere un celular colombiano distinto del principal, una ruta principal ya existente de la misma cuenta/ficha y una conversación importada vacía en IA, sin cierre, unificación ni intervención posterior. Un número vinculado o declarado en otra ficha queda para revisión. Se reutiliza la conversación de la persona, sin crear otra ficha ni un evento entrante. Cada identidad adicional tiene autorización propia; no se sustituyen revocaciones ni bajas. La operación mantiene el intento idempotente y las transacciones nativas de consentimiento.

## Validación preparada

Pasan 161 pruebas backend seleccionadas, 33 frontend, tipos y ESLint; Ruff pasa en los módulos nuevos, la vinculación modificada y las pruebas nuevas. Nueve sentencias nuevas se tradujeron y parsearon como PostgreSQL sin conexión de negocio. La compilación institucional pasa con el aviso histórico de tamaño del bundle. Las selecciones previas de pruebas se solapan y no se suman como suites independientes.

Publicación de este ajuste, vinculación de los dos números, selección de rutas y activación real todavía pendientes en este corte. No se acredita el envío comercial por la prueba al titular. Fuentes, números, textos y recibos nominales sólo en `.local/preicfes-import-20261125/`. Sin DDL, seeds, nuevos servicios, cambios de modelo o escrituras SIIE; aceptaciones previas conservadas.
