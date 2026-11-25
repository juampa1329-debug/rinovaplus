# P23 · Catálogos R7 de inscripción

Fuente: `GuiaImplementacionCRM.md`, aportada por el titular el 25 de noviembre de 2026; SHA-256 `12d9462eeb5c1f18dab11292f1dca327697c9accd7594743f5a31e6764589c52`. Sus ejemplos son ficticios y su compilación declarada no acredita publicación funcional en SIIE.

## Implementación

Se añade la lectura protegida `GET /Api/CRM/v1/CatalogosInscripcion.aspx` con la clave única existente y la carpeta configurada. No se expone la clave en el navegador. La consulta valida período, permiso de creación y catálogos acotados; las ubicaciones conservan país/departamento/búsqueda/desplazamiento y avanzan con `siguienteOffset` sin deducir IDs.

Los campos guardan valores nativos según su contrato: EPS y modalidad textuales, municipio numérico o `valorTexto` según el campo, departamento laboral por nombre nativo, tipo de estudio por ID y título por nombre. Los programas familiares que superan el límite o declaran `admiteCarrera=false` no se recortan para convertirlos en seleccionables. Las opciones fijas proceden de SIIE, conservando etiquetas separadas de los valores.

Cada campo geográfico tiene ámbito propio. Cambiar país/departamento o paginar elimina la selección anterior; una respuesta tardía no restaura la ubicación anterior. Las referencias de ubicación quedan cifradas junto al borrador, no se incluyen como propiedades nuevas del JSON enviado a SIIE. Antes de crear, el backend reconsulta los catálogos y las páginas utilizadas; no admite un ID manual sin esa comprobación. Las consultas remotas ocurren fuera del bloqueo de escritura del CRM.

Se admiten listas opcionales vacías u omitidas, conservando los máximos de tres estudios/dos familiares. `null` no sustituye una lista. Se rechazan nombres reservados de Windows en documentos. Consentimiento, revisión final, edad institucional/excepción PRE-ICFES, documentos iniciales y conciliación siguen vigentes.

Los resultados conservan correlación y límites/espera disponibles. Un conflicto conserva únicamente IDs numéricos de conciliación, sin cuerpos personales ni errores SQL. La UI distingue esas referencias de una confirmación. Las escrituras siguen con intención duradera previa y sin reintentos automáticos, incluso si la respuesta es HTML, redirección, timeout o resultado incierto.

## Verificación

175 pruebas backend focalizadas de SIIE y 18 frontend pasan, con solapamiento respecto de selecciones anteriores. Tipos, ESLint, Ruff y build institucional pasan; aviso histórico de bundle grande. Incluye tipado de selectores, filtros inválidos sin IO, búsqueda/paginación con ámbito, cambios de país y respuestas tardías, períodos históricos, tipos/títulos incompatibles y ubicación laboral coherente. No se declara la suite completa verde.

Publicación y lectura protegida real de R7 pendientes en este corte. La evidencia final se conserva en `artifacts/live/p23-siie-r7-catalogs-20261125.json`. No hay pruebas pagadas de modelos ni creación de personas, inscripción, archivos o documentos privados en SIIE por esta implementación.

## Dependencias conservadas

Esta guía resuelve el contrato faltante de catálogos. No documenta un emisor SIIE→webhook ni generación/consulta/descarga de volantes. Recepción y envíos finales siguen desactivados; firma/emisor, retención, piloto autorizado y contrato de pagos/PDF siguen pendientes. No se aplican scripts, DDL ni cambios al servidor de SIIE. P23 continúa con 0/9 criterios aceptados; otras fases y P22 se conservan.
