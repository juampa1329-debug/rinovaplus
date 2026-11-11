# P7-ES · Mensajería masiva institucional

P7 tiene **82,29% de avance técnico ponderado y2/5criterios aceptados**, con integración local terminada y aceptación externa pendiente. Los pesos/textos originales de279hitos/56criterios permanecen fijos. No se convierte un proveedor controlado en catálogo o recibos reales de Meta.

Aplicación única: http://127.0.0.1:4178/#/broadcasts. Imagen `crm-cbn-workspace:p7es-r3`, base propia `CBN_P7ES_TRIAL_20261027_c305e024`, perfil privado `.local/p7-es/final-runtime`, receta `compose.broadcast.yaml`, volumen propio `crm-cbn-p7-media`. Mismas credenciales humanas. P6 queda detenido y conservado con imagen/base/perfil/volumen; P5/P4/C5/C9 y SIIE siguen intactos.

## Contrato y comportamiento

Se añaden seis tablas de dominio y un diario: `CRMMasivoPlantilla`, `CRMMasivoCampana`, `CRMMasivoConsentimiento`, `CRMMasivoDestinatario`, `CRMMasivoIntento`, `CRMMasivoCadencia`, `CRMMasivoOperacionMigracion`. Total160tablas (130CRM y30académicas),266FK/130mapeos, con30académicas fuera del acceso de datos de la aplicación. Release `5b9e8e2240cfa82e67a4815c56f3ac30fad0647bbf4c2c3dc1983842b543acd6`,3entradas congeladas; sin DDL de arranque.

El catálogo y sus versiones pertenecen a una cuenta WhatsApp y credencial concreta. Orígenes provider/controlado/operador se distinguen; crear un borrador nunca aprueba una plantilla. La API registra creación Meta como operación durable y bloquea un nonce nuevo si hay resultado incierto. La sincronización positiva concilia el intento. Se conservan categoría/idioma/cuerpo/cabeceras TEXT/IMAGE/VIDEO/DOCUMENT, ejemplos, pie, QUICK_REPLY/URL/PHONE_NUMBER yallow_category_change. Calidad/rechazo son de lectura del proveedor. Las variables de cuerpo/cabecera/botón son explícitas; no se reutilizan aliases incorrectos del origen.

La audiencia usa identidades C10, contacto canónico CRM, programas declarados, etapas/ciudades/tags/contactos. Excluye no-contactar, atención humana, conversación cerrada, duplicados, consentimiento ausente/revocado/vencido y contexto cambiado. Filtros de pago/tipo/intención del origen no se inventan en el modelo educativo; business_name/assistant_name pueden mapearse como texto fijo. Scentra no aportaba importación de audiencia CSV/XLSX; no se declara esa función. CSV sí se exporta en el informe.

Preparar sólo registra destinatarios. Activar requiere revisión humana y permisos vigentes. Fecha local+zona IANA se convierten a UTC y rechazan horas ambiguas/inexistentes. La cadencia usa una reserva durable por cuenta en la frontera del POST, incluso con trabajos acumulados; los límites institucionales C10 también se aplican. Una sola cola/despachador C10 transporta plantillas con cuerpo/cabecera/botones. No se monta el worker ni la API legada de campañas. El productor automático B011 y el entrenamiento automático permanecen cerrados.

El POST revalida cuenta, credencial, plantilla aprobada/fresca, identidad, consentimiento, contacto canónico, epoch de campaña/control, autorización y cadencia. Un merge posterior a la primera aceptación bloquea un segundo efecto sobre la persona. Pausar cancela sólo trabajos no iniciados; reanudar revisado prepara un nuevo intento sólo para cancelados que nunca se reclamaron. Los intentos viejos permanecen. Reintento selectivo admite fallo definitivo sin ID de aceptación y reevalúa el consentimiento; nunca reutiliza aceptación ni incertidumbre. Si todos los destinatarios tienen aceptación y no quedan pendientes/inciertos, la campaña se completa sin inventar entrega.

Informe y CSV filtran estado/búsqueda y paginan en SQL. Incluyen cuerpo, errores, intentos, identificador y fechas. Aceptado/enviado/entregado/leído/fallido son distintos. Las fechas de estado son observaciones de eventos autenticados. Una respuesta sólo se atribuye por context.id explícito, misma cuenta y remitente; no por cualquier entrada. El CSV neutraliza fórmulas. Recibos adelantados se conservan en cuarentena y se concilian después de asignar el ID de aceptación.

## Evidencia ejecutada y límites

Pasan322pruebas backend y323frontend, tipos ylint (permanece una advertencia previa de cleanupEpoch). SQL2019 motor15/compat150/TLS validado:15checksAPI,22de ejecución,6negativas extra,12de almacenamiento,7recuperación y5de catálogo.18checks de navegador y7tras reinicio real. Los conteos son alcances separados.

La ejecución22incluye14checks conservados al reanudar tras corregir una expectativa del calificador: una campaña futura sí tiene destinatarios preparados, pero no debe crear intentos/cola antes de la fecha. La ejecución extra6incluye5checks conservados tras corregir la prueba de permisos: un rol built-in es inmutable; el negativo usa un rol personalizado sin inbox.write. No son dos ejecuciones completas nuevas ni sustituyen recibos externos.

El reinicio expuso una consulta escalar OBJECT_DEFINITION atascada en SQL2019; se canceló únicamente la sesión validada del principal P7 y se reinició sólo el SQL Docker de copias para retirar su rollback no interrumpible. El catálogo ahora obtiene definiciones por JOIN a sys.sql_modules/default_constraints/check_constraints, incluyendo triggers DML/DDL. Se compararon15objetos y NULL de módulos cifrados contra la función escalar en FAULT propio. El perfil conserva exactamente su digest, TLS, permisos y detección de drift; no se reemitieron tickets ni se cambiaron releases. Reinicio real posterior conserva157tablas estables y sesión; P6 sigue igual al respaldo fresco.

El respaldo/restauración poblado conserva150tablas estables, incluidos plantillas/consentimientos/intentos/memorias/vault. Retira sesiones/autorizaciones copiadas y pausa campañas; cancela lo no iniciado y conserva efectos inciertos. Dos IDs inciertos sobreviven y trabajadores nuevos no los reencolan ni hacen POST. No se afirma recuperación de blobs poblados: volumen ready0. Una copia de estado sin archivos requiere conservar el volumen.

La principal conserva8contactos/8conversaciones/26mensajes/3agentes y6registros de conocimiento. Añade cuenta ficticia pendiente, campaña y2plantillas locales; cuenta/cadencia/envío siguen deshabilitados, sin credenciales de proveedor, consentimiento, destinatarios ni intentos falsos. Las filas de cuenta previas permanecen byte a byte; los demás datos heredados se compararon antes/después de añadir el ejemplo. Sólo existen30tablas académicas vacías de la fracción suministrada; no se volvió a consultar SIIE Windows ni se afirma mapeo completo de DBSIIE.

## Aceptación pendiente y reversión

P7.2yP7.3se aceptan en su alcance local SQL2019 con transporte controlado. P7.1.m5/m7 requieren catálogo Meta real aprobado; P7.4.m4/m5 requieren recibos externos; P7.close.m5 requiere el recorrido completo y P4. No hay dominio/apps reales disponibles y P4 continúa82,29%. P7 no está al100% ni aceptada globalmente.

Reversión de campaña: pausar primero; conservar intentos, recibos y resultados inciertos y revisar antes de reanudar. Restauración nativa produce perfil/credenciales SQL propios, retira sesiones/autorizaciones y no repite efectos externos. Reversión de fase: conservar primero P7/base/volumen, detener P7 y arrancar el contenedor P6 retenido; nunca ambos en4178 ni fusionar colas inciertas. Sin migraciones down destructivas.

Continuidad: `tasks/p7-es-progress.json`, `docs/adaptation/sql/p7_es_validation.json`, `graphify-out/p7-es/`. El verificador P7 es offline; reproduce P6→P5→P4→preview→P3→P2→P1 con1382preimágenes exactas y no modifica verificadores anteriores. No volver a ejecutar seeds/preparadores/calificadores sobre copias pobladas. Los grafos anteriores quedan congelados; uso de tokens no medido.
