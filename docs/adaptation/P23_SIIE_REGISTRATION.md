# P23 · Aspirantes, inscripción y documentos desde RinovaPlus

Estado: planificada, 0/7 (0%). Solicitada el 24 de noviembre de 2026. Amplía la lectura de SIIE de P16 con escrituras explícitas, sin alterar su aceptación ni ejecutar escrituras durante la planificación.

Fuente aportada por el titular: `Registration 2.md`, revisión local en `E:/documentos C/cbn/RINOVAPLUS/preinscritos/`. Sus ejemplos son ilustrativos y su instalación declarada no equivale a una prueba funcional en SIIE.

## Hitos de aceptación

1. **Contrato y preparación de SIIE.** Verificar en un entorno de prueba los cuatro endpoints `/Api/CRM/v1/AspiranteRegistro.aspx`, `Inscripcion.aspx`, `DocumentosRequeridos.aspx` y `Documentos.aspx`, sus catálogos y permisos. Confirmar con el responsable SIIE que aplicó `002_inscripciones.sql`; RinovaPlus no ejecutará DDL remoto. `idOferta` identifica el programa ofrecido, no el programa base.
2. **Alta de aspirante revisada.** Capturar campos mínimos, validar oferta/período vigente y mostrar un resumen antes de crear. Conservar recibo e identificadores; gestionar `applicant_exists` sin crear un duplicado. La inscripción no requiere crear previamente un aspirante.
3. **Formulario de inscripción.** Once secciones nativas, catálogos reales sin IDs deducidos, validación por campo y borrador protegido. Consentimiento de tratamiento decidido por la persona. Edad mínima institucional de 16 años para programas, excepción PRE-ICFES; no convertir la validación técnica en una decisión autónoma de admisión. Información sensible en formulario protegido, nunca en prompts ni conversaciones públicas.
4. **Documentos y privacidad.** Requisitos reales por oferta, obligatorios iniciales separados de los pendientes posteriores; 10 MiB por archivo/50 MiB total, fotografía JPG/JPEG/PNG y otros documentos también PDF con firma válida. No URLs públicas, nombres/rutas del cliente ni datos de salud en logs/modelos. Acceso por rol y retención explícita.
5. **Inscribir y conciliar.** Backend con clave existente cifrada y límites de escritura 30/minuto/clave/IP/ruta, lectura 120. Envío final explícito e idempotencia local; la API SIIE no ofrece `operationId`. Ante timeout o resultado desconocido, bloquear repetición automática y conciliar IDs/datos antes de continuar. `registration_exists` no prueba igualdad del cuerpo.
6. **Anexos posteriores y fallos.** Subir documentos con IDs confirmados; no sobrescribir archivos ni interpretar marca DB como archivo existente. Probar duplicado, contenido distinto, reutilización, límites, error SQL, `commit_outcome_unknown`, `storage_outcome_unknown` y `file_cleanup_required`. No borrar archivos inciertos ni reintentar POST a ciegas.
7. **Piloto y operación.** Prueba dirigida con datos de ensayo autorizados, matrícula/inscripción/documentos conciliados, permisos, auditoría sin datos sensibles, manual y reversión. Confirmación del titular antes de aceptar la fase y habilitar uso institucional.

## Límites y dependencias

- La inscripción crea estudiante, inscripción y secciones, **no** matrícula académica, cobros, usuario de acceso ni Moodle. La ficha CRM debe mostrar esas diferencias.
- Se reutiliza la clave única SIIE mediante backend; nunca se expone al navegador público. Verificar que sus permisos contemplan estas nuevas rutas.
- La API conserva documentos en SIIE y no tiene transacción distribuida SQL/archivos. Un fallo de red no autoriza un reenvío automático.
- Esta planificación no autoriza crear estudiantes reales, enviar documentación privada, aplicar SQL, modificar SIIE ni aceptar políticas por el estudiante. Esas pruebas se concretarán cuando se implemente P23.
- P16 conserva catálogo, oferta, precios/financiación y consultas de aspirantes/estudiantes; P18 aporta revisión de seguridad y P15 notificaciones que se definan para el nuevo recorrido.
