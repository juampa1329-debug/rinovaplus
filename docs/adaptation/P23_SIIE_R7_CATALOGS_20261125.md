# P23 · Catálogos R7 de inscripción

Fuente: `GuiaImplementacionCRM.md`, aportada por el titular el 25 de noviembre de 2026; SHA-256 `12d9462eeb5c1f18dab11292f1dca327697c9accd7594743f5a31e6764589c52`. Sus ejemplos son ficticios y su compilación declarada no acredita publicación funcional en SIIE.

## Implementación

Se añade la lectura protegida `GET /Api/CRM/v1/CatalogosInscripcion.aspx` con la clave única existente y la carpeta configurada. No se expone la clave en el navegador. La consulta valida período, permiso de creación y catálogos acotados; las ubicaciones conservan país/departamento/búsqueda/desplazamiento y avanzan con `siguienteOffset` sin deducir IDs.

Los campos guardan valores nativos según su contrato: EPS y modalidad textuales, municipio numérico o `valorTexto` según el campo, departamento laboral por nombre nativo, tipo de estudio por ID y título por nombre. Los programas familiares que superan el límite o declaran `admiteCarrera=false` no se recortan para convertirlos en seleccionables. Las opciones fijas proceden de SIIE, conservando etiquetas separadas de los valores.

Cada campo geográfico tiene ámbito propio. Cambiar país/departamento o paginar elimina la selección anterior; una respuesta tardía no restaura la ubicación anterior. Las referencias de ubicación quedan cifradas junto al borrador, no se incluyen como propiedades nuevas del JSON enviado a SIIE. Antes de crear, el backend reconsulta los catálogos y las páginas utilizadas; no admite un ID manual sin esa comprobación. Las consultas remotas ocurren fuera del bloqueo de escritura del CRM.

Se admiten listas opcionales vacías u omitidas, conservando los máximos de tres estudios/dos familiares. `null` no sustituye una lista. Se rechazan nombres reservados de Windows en documentos. Consentimiento, revisión final, edad institucional/excepción PRE-ICFES, documentos iniciales y conciliación siguen vigentes.

Los resultados conservan correlación y límites/espera disponibles. Un conflicto conserva únicamente IDs numéricos de conciliación, sin cuerpos personales ni errores SQL. La UI distingue esas referencias de una confirmación. Las escrituras siguen con intención duradera previa y sin reintentos automáticos, incluso si la respuesta es HTML, redirección, timeout o resultado incierto.

## Verificación

182 pruebas backend focalizadas de SIIE y 18 frontend pasan, con solapamiento respecto de selecciones anteriores. Tipos, ESLint, Ruff y build institucional pasan; aviso histórico de bundle grande. Incluye tipado de selectores, filtros inválidos sin IO, búsqueda/paginación con ámbito, cambios de país y respuestas tardías, períodos históricos, tipos/títulos incompatibles y ubicación laboral coherente. No se declara la suite completa verde.

Publicación comprobada: código inicial `5dd1fc9`, seguido por compatibilidad `8f9143c`. La primera lectura real detuvo la carga porque la metadata usa rutas equivalentes de colecciones. Se admiten únicamente equivalencias revisadas como `municipios.items` y nombres de opciones, conservando la propiedad nativa. Una propiedad distinta sigue bloqueada; diagnóstico sólo con nombres de campo/ruta/propiedad conocidos, sin valores arbitrarios.

Backend `ghwuy168521ldptx3hfjzvnw`: **Success**, 4m22; frontend `dg4ieov07hbut2syrukhypws`: **Success**, 26s. La versión inicial también pasó salud (4m20/46s). Con la clave existente y el borrador vacío de PRE-ICFES se comprobaron las seis clases de catálogos antes pendientes y sus opciones por campo: seis tipos de documento, dos géneros, dos modalidades, 21 EPS y jornada nativa. País→departamento→municipio funciona: Colombia/Magdalena, búsqueda «Santa» que limpia la selección anterior; Antioquia tiene primera página de 100 y segunda de 25, sin conservar una selección de otra página. Se descartaron todas las selecciones temporales mediante recarga, sin guardar datos personales ni aceptar tratamiento. Los dos requisitos de la oferta se volvieron a consultar; archivo desconocido permanece sin comprobar.

Nueve procesos **Al día**, última consulta nativa 12:45:36 Bogotá. Un GET de ajustes durante el rollout mostró un timeout; la recarga posterior respondió correctamente. Esto acredita esa observación, no ausencia universal de fallos ni SLA. El catálogo nativo contiene etiquetas municipales repetidas con IDs distintos y algunas etiquetas de opciones con caracteres mal codificados; se conservan sin fusionar IDs ni alterar valores de solicitud. La limpieza de esos datos corresponde al productor SIIE.

La evidencia final se conserva en `artifacts/live/p23-siie-r7-catalogs-20261125.json`. No hay pruebas pagadas de modelos ni creación de personas, inscripción, archivos o documentos privados en SIIE por esta implementación.

## Dependencias conservadas

Esta guía resuelve el contrato faltante de catálogos. No documenta un emisor SIIE→webhook ni generación/consulta/descarga de volantes. Recepción y envíos finales siguen desactivados; firma/emisor, retención, piloto autorizado y contrato de pagos/PDF siguen pendientes. No se aplican scripts, DDL ni cambios al servidor de SIIE. P23 continúa con 0/9 criterios aceptados; otras fases y P22 se conservan.
