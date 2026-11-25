# P23 · Aspirantes, inscripción y documentos desde RinovaPlus

Estado: en implementación, **0/9 criterios aceptados**. La planificación original del 24 de noviembre tenía 0/7; el 25 se añaden webhook/clasificación y el piloto de volante PRE-ICFES. Los siete criterios originales se conservan. Las aceptaciones de P16 y otras fases no cambian.

25 de noviembre: implementación preparada de las cuatro rutas con clave única, borradores cifrados, once secciones, revisión final, documentos con límites/firma y reserva duradera antes de POST. Una respuesta desconocida bloquea repetición automática. Receptor firmado preparado y clasificación de origen SIIE con exclusión de promociones para inscritos en selección y despacho; coincidencias de teléfono requieren revisión. Publicación y piloto real aún pendientes en este corte. Ver [contrato para el desarrollador de SIIE](SIIE_WEBHOOK_CONTRACT_V1.md).

**No confundir código preparado con aceptación funcional completa:** faltan firma compartida/activación del emisor, catálogos reales de las secciones, pruebas autorizadas de escritura/archivos y conciliación, política de retención y contrato de volantes/PDF. Los envíos finales y la recepción están desactivados por defecto.

Fuente aportada por el titular: `Registration 2.md`, revisión local en `E:/documentos C/cbn/RINOVAPLUS/preinscritos/`. Sus ejemplos son ilustrativos y su instalación declarada no equivale a una prueba funcional en SIIE.

## Hitos de aceptación

1. **Contrato y preparación de SIIE.** Verificar en un entorno de prueba los cuatro endpoints `/Api/CRM/v1/AspiranteRegistro.aspx`, `Inscripcion.aspx`, `DocumentosRequeridos.aspx` y `Documentos.aspx`, sus catálogos y permisos. Confirmar con el responsable SIIE que aplicó `002_inscripciones.sql`; RinovaPlus no ejecutará DDL remoto. `idOferta` identifica el programa ofrecido, no el programa base.
2. **Alta de aspirante revisada.** Capturar campos mínimos, validar oferta/período vigente y mostrar un resumen antes de crear. Conservar recibo e identificadores; gestionar `applicant_exists` sin crear un duplicado. La inscripción no requiere crear previamente un aspirante.
3. **Formulario de inscripción.** Once secciones nativas, catálogos reales sin IDs deducidos, validación por campo y borrador protegido. Consentimiento de tratamiento decidido por la persona. Edad mínima institucional de 16 años para programas, excepción PRE-ICFES; no convertir la validación técnica en una decisión autónoma de admisión. Información sensible en formulario protegido, nunca en prompts ni conversaciones públicas.
4. **Documentos y privacidad.** Requisitos reales por oferta, obligatorios iniciales separados de los pendientes posteriores; 10 MiB por archivo/50 MiB total, fotografía JPG/JPEG/PNG y otros documentos también PDF con firma válida. No URLs públicas, nombres/rutas del cliente ni datos de salud en logs/modelos. Acceso por rol y retención explícita.
5. **Inscribir y conciliar.** Backend con clave existente cifrada y límites de escritura 30/minuto/clave/IP/ruta, lectura 120. Envío final explícito e idempotencia local; la API SIIE no ofrece `operationId`. Ante timeout o resultado desconocido, bloquear repetición automática y conciliar IDs/datos antes de continuar. `registration_exists` no prueba igualdad del cuerpo.
6. **Anexos posteriores y fallos.** Subir documentos con IDs confirmados; no sobrescribir archivos ni interpretar marca DB como archivo existente. Probar duplicado, contenido distinto, reutilización, límites, error SQL, `commit_outcome_unknown`, `storage_outcome_unknown` y `file_cleanup_required`. No borrar archivos inciertos ni reintentar POST a ciegas.
7. **Piloto y operación.** Prueba dirigida con datos de ensayo autorizados, matrícula/inscripción/documentos conciliados, permisos, auditoría sin datos sensibles, manual y reversión. Confirmación del titular antes de aceptar la fase y habilitar uso institucional.
8. **Webhook y clasificación SIIE.** Evento posterior al commit, firma HMAC con reloj, GUID estable y secuencia por persona, recibo duradero/dedupe, origen SIIE filtrable en el listado CRM junto a importados Excel y redes. Preinscrito separado de inscrito; inscritos excluidos de promociones incluso si la audiencia ya estaba preparada. Sin fusión por teléfono, sin otorgar consentimiento ni afirmar matrícula/pago. Piloto real productor→receptor pendiente.
9. **Volante PRE-ICFES.** Flujo aprobado por el titular el 25: corroborar inscripción e identidad/contacto, confirmar expresamente contado o financiado, pedir a SIIE el volante y recibir/enviar PDF al contacto verificado. Contrato de generación/consulta/descarga e idempotencia pendiente del desarrollador. No hay cobros, órdenes ni PDFs enviados por esta preparación; generalizar a otros programas requiere validar primero el piloto PRE-ICFES.

## Límites y dependencias

- La inscripción crea estudiante, inscripción y secciones, **no** matrícula académica, cobros, usuario de acceso ni Moodle. La ficha CRM debe mostrar esas diferencias.
- Se reutiliza la clave única SIIE mediante backend; nunca se expone al navegador público. Verificar que sus permisos contemplan estas nuevas rutas.
- La API conserva documentos en SIIE y no tiene transacción distribuida SQL/archivos. Un fallo de red no autoriza un reenvío automático.
- La implementación está autorizada. Las pruebas de creación real necesitan datos de ensayo concretos; esta preparación no autoriza inventar estudiantes, enviar documentación privada de terceros, aplicar SQL ni aceptar políticas por el estudiante.
- P16 conserva catálogo, oferta, precios/financiación y consultas de aspirantes/estudiantes; P18 aporta revisión de seguridad y P15 notificaciones que se definan para el nuevo recorrido.
