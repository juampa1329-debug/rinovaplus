# P9 · Publicidad y captación · SQL Server 2019

P9 conserva los módulos integrados en una sola dirección: http://127.0.0.1:4178/#/ads. Imagen `crm-cbn-workspace:p9es-r9`; base propia `CBN_P9ES_TRIAL_20261027_94ba4b55`; perfil privado `.local/p9-es/final-runtime`; volumen propio `crm-cbn-p9-media`; receta `compose.ads.yaml`. P8 R7 está detenido como `crm-cbn-preview-p8-preserved`. SIIE, C5/C9 y perfiles, bases, imágenes, volúmenes y evidencias anteriores se conservan.

## Alcance contrastado con Scentra

La fuente `saas-version/backend/app_saas/ads/router.py` contiene CRUD local y procesamiento de webhooks recibidos. No implementa llamadas HTTP de Marketing API para publicar anuncios, cambiar gasto o descargar métricas. El enlace Conectar Meta abre Canales. Los valores de presupuesto/CTR/CPC/leads son registros declarados, con período explícito. `last_sync_at` sigue vacío mientras no exista sincronización externa comprobada. No se presentan registros locales como verificación del proveedor. Ads Creative, Content Studio, Advisor y marketplace quedan fuera de este dominio; tampoco se incorpora WooCommerce ni planes/cobros.

| Función de la fuente | Adaptación CBN | Evidencia |
|---|---|---|
| Cuentas Meta/TikTok: proveedor, ID externo, nombre, estado, moneda, zona horaria y configuración | Formulario por cuenta, vínculo C10, formularios asociados y programa/etapa CRM declarados; disponibilidad local separada de verificación | API, interfaz y revisión semántica |
| Campañas: cuenta, ID externo, canal, nombre, objetivo, estado, presupuestos e indicadores | Registro tipado; importe en moneda convierte a centavos; CTR/CPC/leads finitos con período; ninguna acción cambia anuncios externos | API, pruebas puras y navegador |
| Formularios/leads: nombre, correo, teléfono, IDs anuncio/campaña/formulario, estado y conversación | Captación por cuenta, contexto CRM humano y nota interna; enlace a ficha e Inbox por UUID de conversación | SQL/API, duplicados, concurrencia y merge/undo |
| Comentarios sociales de anuncios: autor, publicación/padre, texto, enlace, estado y conversación | Referencias tipadas, estados review/resolved/ignored, comparte vínculos con P4 en ambos órdenes | Recibos firmados y extras12 |
| Procesar webhooks recibidos y reintentar | Cursor propio por cuenta+recibo; estado C10 permanece independiente; validación vigente del canal, app, ruta, firma y cuenta | Recibos Meta14 y TikTok4 controlados |
| Resumen de cuentas, campañas, leads abiertos, comentarios abiertos, recibos y conversaciones | Seis indicadores, filtro de cuenta/período de captación, fecha de consulta y origen | SQL/API y navegador |
| Token de acceso | Versiones privadas AES-GCM, permiso de Canales y autenticación reciente; revocar retira puntero sin borrar historial | API16, permisos SQL y recuperación |

La reimportación manual del mismo ID es idempotente; la edición explícita usa revisión CAS. Un recibo firmado posterior enriquece campos no vacíos sin borrar fecha original, estado ni enlace confirmado. Es una corrección deliberada respecto al upsert implícito de la fuente.

## Contrato y ejecución SQL

SQL Server motor15, compatibilidad150 y TLS con certificado validado (`Encrypt=yes`, `TrustServerCertificate=no`). 175 tablas totales, 145 mapeos CRM, 30 tablas académicas protegidas y 304 claves foráneas físicas. Se añaden siete tablas de dominio y un diario: `dbo.CRMPublicidadCuenta`, `CRMPublicidadCampana`, `CRMPublicidadIdentidad`, `CRMPublicidadCaptacion`, `CRMPublicidadProceso`, `CRMPublicidadEvento`, `CRMPublicidadSecreto` y `CRMPublicidadMigracion`.

`cbn_ads_operations_v1` conserva P9ES-000/P9ES-001 y su modelo/hashes congelados. La extensión separada `cbn_ads_operations_v2/P9ES-002.sql` añade ignored y un CHECK que prohíbe converted sin identidad/fecha; mantiene independiente el estado posterior de una captación ya enlazada. No se reescribió una migración comprometida. El runner serializa la secuencia completa con applock, historial STARTED/COMMITTED y verificación de modelo, destino, release y diario padre. No hay DDL al arrancar la aplicación. Perfil v2 y recuperación exigen exactamente la release v2; no se etiqueta una restauración v1 como v2.

El principal propio no puede leer/escribir académicas, ejecutar DDL, alterar el diario ni reescribir eventos o secretos. Las FK de cuenta/institución y las claves externas impiden reasignar campañas/captaciones a otra cuenta. Motor, modelo, destino, principal, sesión SQL, permisos y firma del perfil se conservan en las validaciones. Programas/etapas vienen del catálogo CRM declarado; no se afirma un mapeo completo DBSIIE.

## Identidad, recepción y límites

No se mezclan personas por teléfono/correo entre cuentas. Dentro de la misma cuenta+canal se correlacionan autor explícito o teléfono ASCII útil/correo; datos inválidos recurren al ID externo. Las referencias persistidas conservan el ContactId histórico de la conversación y las lecturas resuelven el contacto canónico. Esto admite conversión antes/después de merge y undo. El puente P4 también puede reutilizar un lead previo del mismo autor; vínculos ambiguos entre cuentas se rechazan.

Un formulario no concede consentimiento comercial, destinatario DM, ventana de 24 horas ni LastIncomingAt. Sólo se reutiliza una identidad de mensajería ya existente en el canal declarado. Se crea una nota interna y un contexto CRM humano. Comentarios/DM conservan sus reglas P4 y una sola cola C10/P7; no se introduce un segundo reply worker ni worker Ads automático.

El procesador lee únicamente cuerpos C10 autenticados y vigentes. No reclama ni altera Status/Attempts/Lease C10, incluso si C10 puso un formulario en cuarentena por no reconocer su tipo. La cuenta anunciante debe venir explícita o resultar única por formulario/campaña y canal. Eventos incompletos, ambiguos, canal pausado/no verificado o ruta cambiada se ponen en cuarentena sin cambios parciales. Reintento exige revisión explícita y CAS. JSON, tamaño, profundidad, fechas y aliases tienen límites; un timestamp desbordado queda registrado en cuarentena y no atasca la secuencia. TikTok conserva su firma temporal y client_key; no se fabrican IDs a partir del texto.

## Pruebas y preservación

395 pruebas backend y342 frontend, tipos y lint pasan. Nuevas pruebas puras P9:34; interfaz P9:10. Calificaciones SQL separadas: API16, recibos Meta14, extras12, TikTok4, storage12 (cuatro restauraciones propias con fallos/concurrencia/drift), recuperación8. No son una suma de pruebas únicas. Las últimas API16/Meta14/extras12 se repitieron sobre el código final; algunas pruebas anteriores permanecen como historia de la misma copia de trabajo.

La recuperación poblada conserva162 tablas estables y autentica todas las versiones de secretos Access/C10/Ads antes de permitir login. Revoca sesiones/OAuth copiados, pausa cuentas Ads y retira aprobaciones/copias pendientes según contrato anterior. Copia y verifica cuatro blobs privados de plantillas P8 en raíz nueva. Ese snapshot precede las calificaciones finales extras12/API16; no se afirma recuperación de efectos posteriores a su backup. El respaldo SQL por sí solo no incluye archivos. Los consumidores recuperados no hacen POST ni reencolan efectos inciertos.

Se corrigió la espera de una prueba histórica de Settings: ahora comprueba la misma lectura única después del efecto asíncrono, sin relajar su expectativa ni cambiar producción.

La versión principal conserva8 contactos/conversaciones originales y26 mensajes, agentes, conocimiento, memoria/ADN, ajustes, canales y borradores anteriores. Añade3 contextos ficticios de Ads,2 cuentas pausadas,2 campañas en borrador,2 leads y1 comentario etiquetados Ejemplo ficticio. No crea consentimientos, inscripciones, intentos o aprobaciones externas. La semilla corrigió pausas de demostración y una referencia de login en pasos controlados, sin borrar los registros parciales ni historial; no debe reejecutarse después de su resultado aprobado.

La huella de negocio P8 y las30 tablas académicas de su backup fresco coinciden; la copia P9 conserva las académicas idénticas. Windows SIIE no se reconsulta ni se modifica. El navegador detectó una respuesta atrasada de una recarga al cambiar de pestaña; el recurso propio Ads publica sólo la respuesta vigente de la vista/sesión. Su prueba diferida evita que leads sustituyan comentarios. Los mensajes temporales del editor no se usan como evidencia de persistencia. Recibos de navegador y reinicio se guardan por separado. El replay offline P8→P7→P6→P5→P4→preview→P3→P2→P1 usa1562 preimágenes exactas y los verificadores históricos sin editar.

La calificación visual reprodujo espera agotada en el bloqueo de transacción (diagnóstico de etapa sin parámetros/secretos). Sólo P9 admite15s de espera por applock, frente a5s anteriores; conserva aislamiento SERIALIZABLE, ambos bloqueos, límite SQL y todas las validaciones de destino/TLS/permisos/modelo antes de ceder acceso. No se reintentan escrituras automáticamente. El ensayo de contención mantiene el bloqueo exclusivo6s y verifica espera real sin bypass, lectura válida tras liberarlo y dominio intacto (`lock-wait-result.json`,3checks). Perfiles anteriores mantienen5s.

La validación P9 comparte sólo dentro de la misma transacción el catálogo completo con su lector estructural propio `p9_catalog_snapshot.py`, derivado del lector congelado. El lector previo y las releases conservan sus bytes. Las verificaciones USER/LOGIN de impersonación se ejecutan por lotes parametrizados de hasta200, con las mismas comparaciones y rechazo deNULL; ninguna se omite. `catalog-reuse-result.json` contrasta modelo/hashes y todos los resultados individuales, valida tres transacciones nuevas sin caché entre peticiones y rechaza drift real en otra restauración propia.

## Cierre, progreso y reversión

P9.1/P9.2/P9.3 quedan aceptados en el alcance real de la fuente. Pasaron25 comprobaciones de navegador y12 de reinicio/smoke en la imagenR9;172 tablas estables, sesión, ejemplosAds yblobP8 sobrevivieron al reinicio real. P9.close.m1/m2/m3 tienen evidencia local; P9.close.m4 conserva su dependencia P4. Sin dominio/apps/aceptación externa todavía, P4 sigue82,29%. No se fabrica el100% ni se cambian pesos para obtenerlo. Se publican porcentajes técnicos parciales y aceptación canónica por separado.

El porcentaje general suma el trabajo realizado de cada uno de los56 criterios de peso1, incluido parcial, y divide por56. No es promedio simple de fases ni ratio de los279 hitos. Desde esta entrega, cada cierre debe mostrar porcentaje general y por fase. Consultar `tasks/p9-es-progress.json`, `docs/adaptation/phase-work-progress.json` y `P9_ES_CHECKPOINT.md` para los valores calculados vigentes.

Para pausar: cambiar disponibilidad local de la cuenta a Pausado; quedan IDs, captaciones, procesos y eventos. No borrar ni modificar anuncios reales para revertir la interfaz. Para recuperación, restaurar siempre a nueva base/perfil/media y revisar cuentas antes de reactivar. Para volver al contenedor P8, conservar primero P9/base/volumen, detener P9 y arrancar sólo P8 retenido en4178. No fusionar intentos inciertos ni reejecutar seeds/preparadores en copias pobladas.
