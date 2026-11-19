# Actualización vigente: copia local y fechas opcionales

Por decisión del propietario del19-11, seguir [el nuevo recorrido de catálogo local](P16_LOCAL_CATALOG_20261119.md). No se exige un período nuevo para copiar programas ni fechas completas para informar importes conocidos con pendientes explícitos. Se conservan fuentes, correcciones manuales y fechas desconocidas; no se modifican datos de SIIE. El corte inferior conserva la política histórica anterior y ya no obliga a completar fechas para orientar.

# P16 · Conexión SIIE desde RinovaPlus

**Actualización vigente del 19-11-2026:** una sola clave original en `SIIE_API_TOKEN`; ya no se solicita otra clave General. Consumidor ampliado a estudiantes/contactos y período ofrecido. Seguir [el procedimiento de clave única](P16_SIIE_SINGLE_KEY_20261119.md). P16 sigue 0/5 aceptadas hasta validar la credencial nueva, el productor público y el recorrido financiero. El texto inferior conserva el corte anterior como historia, incluida su configuración de dos claves; no usarlo para configurar la versión nueva.

## Corte histórico del 18-11-2026

Estado: adaptador y consultas implementados; aceptación real pendiente de claves y datos del proveedor. No modifica el peso del roadmap original. Documentos del proveedor recibidos el18-11-2026 se conservan en `docs/contracts/SIIE_PROVIDER_GUIDE_20261118.md` y `SIIE_CRM.postman_collection.json`. Sus ejemplos son ficticios y sus instrucciones no autorizan ejecutar escrituras.

## Credenciales en Coolify

Backend RinovaPlus → Environment Variables → Production. Sólo Runtime, Build time desactivado. Guardar secretos directamente allí, sin chat, Git, capturas, parámetros URL ni logs.

| Variable | Valor / finalidad |
|---|---|
| `SIIE_API_BASE_URL` | `https://siieplus.online/SIIEWebPlus` |
| `SIIE_API_HOSTS` | `siieplus.online` |
| `SIIE_CATALOG_API_TOKEN` | Token ORIGINAL de catálogo, al menos32caracteres; no el SHA256 de `API_CRM`. |
| `SIIE_ADMISSIONS_API_TOKEN` | Clave GENERAL de Admisiones; distinta del catálogo. Sólo necesaria para aspirantes/períodos/seguimientos. |

Después de guardar se incorpora al contenedor mediante redeploy del backend. No modificar las variables Oracle de P15. En Académico → Abrir SIIE → Comprobar conexión configurada se muestran sólo booleanos. Tener una clave configurada no prueba que SIIE la acepte. No hay formulario que revele claves ni secreto en el frontend. Las variables anteriores `SIIE_CATALOG_API_URL/HOSTS` conservan el importador legado; al configurar `SIIE_API_BASE_URL`, ese importador ya no permite saltarse la revisión ASPX.

## Recorrido de consulta

1. Programas y finanzas → Obtener programas. Hasta25por página; cursor opaco. Elegir programa y oferta con ID completo `Id-nNivel`.
2. Revisar escuela, jornada, período, nivel, materias y procedencia. `duration_levels` se muestra como niveles, no meses. El estado del período no acredita vigencia financiera.
3. La guía recibida describe422`source_data_incomplete` para las ofertas resolubles; las pruebas reales del18-11 devolvieron503`catalog_unavailable` sin datos parciales (véase el informe consolidado P16). Cuando SIIE devuelva el422documentado, RinovaPlus presenta `partial_offer` y `data_quality` como inspección, con aviso no cotizable. No guarda ni publica ese contenido en agentes. Conservar nulos, fechas originales, planes no resolubles y calidad; no redondear importes ni regenerar vencimientos.
4. Enseñanza ordinaria y `full_cost_cash_cop` de esta fuente corresponden al semestre/nivel. No llamarlos precio del programa completo. Pronto pago, extraordinaria, abono, cuotas y total almacenado se muestran como datos de origen, sujetos a vigencia y condiciones aún pendientes. SIIE debe resolver sede, requisitos, vigencia comercial, condiciones y calendario antes de aceptar cotizaciones.
5. Aspirantes y seguimiento → Obtener períodos. Si hay varios/ninguno activo, elegir explícitamente. Obtener filtros de ese período y buscar; páginas de25conservan los filtros efectivamente consultados aunque se edite otro borrador de búsqueda.
6. Abrir ficha e historial; no equiparar `confirmadoOrigen` ni resultado de seguimiento con matrícula. La API no entrega documento, teléfono ni correo en esa ficha. No unir personas por nombre ni importar contactos automáticamente.

## Datos que aún debe entregar SIIE

- Estudiantes: consulta paginada de estudiantes y matrícula por período, ID estable, programa/oferta/nivel/sede/jornada y estado con su semántica. Un aspirante confirmado no sustituye esta ruta.
- Cartera personal: obligaciones, recibos/pagos/anulaciones, saldo, moneda, fecha de corte, plan asignado y permisos específicos. El catálogo de planes no informa la deuda de una persona.
- Oferta cotizable: resolver las incidencias declaradas, revisar alcance de contado y extras, fechas comerciales, planes y condiciones; dos ofertas reales completas/vigentes para aceptación P16.2.
- Vigencia/incremental: revisión y bajas, webhooks de invalidación o regla de refresco acordada; el catálogo keyset es vivo y no garantiza snapshot entre páginas.
- Seguimientos de escritura: la documentación sí define POST/PUT con `operationId`, UUID CRM estable y `expectedRevision`, pero este corte NO habilita esos métodos desde RinovaPlus. Falta persistir solicitud exacta y comprobantes, preflight/autenticación reciente, autoría, revisión humana, estado incierto y reconciliación de409/503 antes de una escritura real. No ejecutar toda la colección de Postman: contiene operaciones que escriben en SIIE.

## Límites y diagnóstico

Sólo nueve GET documentados y una consulta local de estado. `agents.manage`, sesión, módulo Agentes y comprobaciones SQL vigentes antes del IO; nueva comprobación de autoridad antes de mostrar datos externos. No credenciales cruzadas ni URL elegida por usuario. TLS/certificado, dominio permitido, sin redirecciones, proxies del ambiente deshabilitados, conexión5s y lectura15s; cada respuesta descomprimida máxima512KiB. IDs int32/cursor128/query100/offset1millón validados. Sin reintento automático ni rastreo masivo.

401/403: revisar clave original y ámbito.404: volver a elegir referencia/período.429: respetar Retry-After; no forzar consulta continua.503: custodio revisa disponibilidad/configuración de SIIE. Los detalles privados del servidor no se copian al CRM; se conserva X-Correlation-ID sólo si tiene formato seguro. La consulta pública sin credencial del18-11 devolvió401JSON y TLS válido: demuestra disponibilidad de esa ruta, no datos ni claves válidas.

No DDL nuevo, seeds, matrículas, pagos, cambios académicos ni envíos externos a personas. Pausar quitando las variables correspondientes; el catálogo local revisado permanece intacto. El despliegue no incluye ninguna clave. Antes de aceptar P16 hay que probar acceso/rechazo, dos ofertas completas, cambios/bajas, procedencia, uso correcto por Gemini, recuperación y aceptación del custodio. P15 cerrado no acredita esos puntos.
