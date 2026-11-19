# P16 · Copia local, fechas opcionales y revisión financiera

Decisión del propietario, 19-11-2026: el catálogo base no requiere un nuevo metadato de período para copiar sus programas. Fechas ausentes no bloquean los importes conocidos. Este alcance reemplaza la anterior exigencia del consumidor de tener todas las fechas para orientar; no modifica los documentos originales de SIIE ni convierte su `quotable=false` en una aprobación del proveedor.

## Recorrido

1. Académico → Abrir SIIE → Obtener programas de SIIE. Si el período no viene, se identifica como catálogo base y la disponibilidad de la oferta sigue por confirmar.
2. **Copiar esta página a RinovaPlus** guarda hasta 25 programas en el catálogo local, con ID de origen, revisión y copia recibida. Cada página se revisa/copía explícitamente; no se inicia un rastreo ilimitado.
3. Seleccionar programa/oferta y **Preparar ficha local con datos disponibles**. Se conservan los importes válidos de contado y planes disponibles aunque falten fechas o condiciones. Planes contradictorios se señalan para revisión sin ocultar un precio de contado válido.
4. Revisar la ficha y **Guardar programa**. En Contado, planes y fechas locales se pueden completar fechas, abono, cuotas, total y condiciones. Los campos desconocidos quedan vacíos/null; no se rellenan con el calendario académico.
5. La IA consulta el catálogo local. Puede explicar los importes conocidos y aclarar que las fechas o condiciones están por confirmar con un asesor. No inventa vencimientos, no anuncia una confirmación o gestión humana que no se haya realizado y no confunde enseñanza de un nivel con todo el programa o extras.

## Sincronización y procedencia

La copia de origen se guarda separada de los datos editables, usando Setting/SettingHistory existentes, sin DDL ni escrituras en SIIE. La copia local funciona aunque la API externa no esté disponible.

La sincronización compara tres versiones: última copia de SIIE, ficha local y respuesta nueva. Actualiza campos no modificados y conserva cambios manuales, incluidas fechas de cada cuota por su número y planes por su ID estable. Refrescar nombres/escuelas del catálogo base no borra las finanzas de una oferta ya revisada. Una fecha de una oferta distinta no se arrastra a otro nivel/período.

Si los importes nuevos y las correcciones manuales dejan un total incoherente, se detiene la aplicación con explicación y la ficha anterior permanece intacta. Las fechas conocidas imposibles o desordenadas, importes negativos, moneda incorrecta y totales contradictorios no se aceptan como correctos. Un cero informado se conserva; null nunca se transforma en cero.

La operación conserva identidad durable, revisión esperada y una nueva comprobación de permisos tras consultar SIIE. Una copia de página es atómica; su repetición no duplica programas ni vuelve a consultar si ya tiene comprobante. Una oferta que cambió desde la revisión debe prepararse de nuevo. No se unen programas sólo por similitud de nombre.

La vigencia desconocida se distingue de una vigencia conocida vencida/futura y de una oferta informada inactiva. Estas últimas no se anuncian como precios actualmente disponibles.

## Alcance y aceptación

Pruebas locales: 168 backend seleccionadas y 31 frontend, con datos ficticios; no sustituyen SQL nativo ni recepción financiera real. Pendientes de este corte: desplegar, copiar programas reales, verificar la respuesta financiera pública actual y contrastar el uso por Gemini. Un 503 sin `partial_offer` todavía requiere que SIIE entregue los datos; el consumidor no puede recuperar precios de un cuerpo de error vacío.

No se solicita una nueva clave: continúa `SIIE_API_TOKEN`. No se cambian usuarios, matrícula, cartera personal, tablas de SIIE ni pagos. P16 conserva su aceptación separada; no se declara al 100% sólo por estas pruebas.
