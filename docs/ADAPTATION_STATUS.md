## P15 en implementación y pruebas — 2026-11-18

Ajustes → Correos y notificaciones incorpora transporte Oracle SMTP/TLS, reglas por evento y destinatarios, grupos, preferencias propias, versiones de HTML y recursos de marca inspeccionados, informes diarios/semanales y outbox cifrado en PostgreSQL. Recuperación por correo sin enumeración y activación revisada desde Usuarios reutilizan códigos de un uso/una hora y conservan 2FA. El consumidor SMTP es independiente de mensajería. SMTP aceptado no equivale a entrega; resultados inciertos no se reenvían automáticamente. Los recibos de Oracle se registran como observación de operador, no como webhook automático.

**P15 sigue abierta: 0/7 unidades aceptadas.** Hay implementación parcial con pruebas; no se declara 100% ni entrega real todavía. Pendientes: propagación/verificación DKIM/SPF, prueba real de SMTP/recibos/invitación/recuperación, validar la cobertura instrumentada de eventos de colas/webhooks y modelo automático, revisión de informes y ensayo de recuperación P15. Oracle: dominio y remitente registrados en Ashburn; credenciales guardadas por el propietario en Coolify, sin valores en el repositorio. Migración manual aplicada: 7 tablas nativas separadas, 155 tablas CRM intactas, runtime sin CREATE ni DELETE; prueba de deduplicación/reclamación con rollback, cero correos persistidos por ese ensayo.

Pasan 329 pruebas backend seleccionadas (32 nuevas P15), 18 frontend seleccionadas, tipos/lint modificado y build de workspace; comprobación de UI/despliegue pendiente. Advertencia previa de bundle grande conservada. Evidencia y manual: `tasks/p15-notifications-progress.json`, `docs/adaptation/P15_ORACLE_OPERATOR_RUNBOOK.md`. Preimágenes: `artifacts/live/history/p15-notifications-20261118/`.

General original P0–P11:100%; P12 auxiliar:100% en el alcance PostgreSQL/Meta aceptado. Las fases adicionales conservan seguimiento separado: P13 Académico/agentes por programa (parcial,0/4), P14 entrenamiento comercial (plan), P15 correos/notificaciones (en pruebas,0/7), P16 API académica/financiera SIIE (diferida,0/5), P17 TikTok (diferida,0/5), P18 seguridad/ciberseguridad (plan,0/8). OPS-05 no se cierra sin alertas realmente entregadas. Los cortes inferiores conservan su evidencia histórica.

## Aceptación vigente P11/P12 en PostgreSQL — 2026-11-18

**Roadmap original P0–P11: 100,00%; 279/279 hitos y 56/56 criterios aceptados. P11:100%, 4/4.** El propietario aceptó explícitamente «Aceptar ese alcance y registrar las mejoras pendientes»: PostgreSQL actual publicado, recorridos acordados P1–P10 y los límites operativos entregados. Sólo se aceptan P11.3/P11.close y se completan sus cinco hitos pendientes; P11.1/P11.2 y todos los cierres previos conservan sus alcances. La referencia SQL2019 se mantiene con modificación humana explícita del destino a PostgreSQL; no se recertifica SQL2019 ni se afirma mapa completo DBSIIE.

P12 queda al 100% como agrupación auxiliar de los 18 hitos originales ya resueltos en el alcance PostgreSQL/Meta, sin añadir peso. Copia externa, custodia de clave, RPO/RTO, retención/espacio, alertas entregadas y conciliación adicional DB/archivos siguen abiertos como OPS-01–OPS-06 en `tasks/operations-hardening-backlog.json`. La aceptación no los declara implementados ni cubre pérdida total del servidor. SIIE y TikTok continúan diferidos.

Evidencia: `artifacts/live/p11-postgres-acceptance-20261118.json`; guía `docs/adaptation/P11_P12_LIVE_ACCEPTANCE.md`; manual `docs/adaptation/P11_POSTGRES_OPERATOR_RUNBOOK.md`; preimágenes en `artifacts/live/history/p11-postgres-20261118/`. Restauración aislada 157 tablas/19 archivos y reversión frontend 19866a7→9d8d608 verificadas, misma sesión y ocho consumidores. Las 117 pruebas backend/16 frontend seleccionadas, tipos/lint modificado/build son de esa revisión; no equivalen a replay SQL histórico integral, cuyos veinte archivos ausentes siguen declarados. No modificar releases/checkers/grafos anteriores ni ejecutar seeds/preparadores sobre bases pobladas.

P0–P11:100% cada una; P12 auxiliar:100% en el alcance aceptado; P13 parcial 0/4; P14 plan; P15 correos planificada 0/7; P16 SIIE y P17 TikTok diferidas 0/5 cada una; P18 seguridad planificada 0/8. Las fases adicionales no forman parte del denominador de 56 criterios; no declarar implementadas todas sus capacidades. Los cortes inferiores se conservan como historia y prevalece esta aceptación nueva.

## Estado vigente P11-ES local; puesta institucional pendiente — 2026-10-28

**Roadmap general:93,62%. P11 original:72,50% (2/4criterios); sprint local de operación:100% dentro de su alcance.** Son261/279hitos y45/56criterios aceptados. El general incluye trabajo parcial mediante los56criterios de peso1; no es promedio de fases ni ratio de tests/hitos. Cada respuesta final debe incluir porcentaje general y avance de todas las fases. P12 es la fase adicional solicitada por el usuario para servidor/URLs/puesta online:ejecución0%,sin añadir peso ni duplicar los18hitos originales pendientes. No declarar el roadmap ni P11 institucional al100%.

Aplicación única acumulada:**http://127.0.0.1:4178/#/settings/operations**. Imagen`crm-cbn-workspace:p11es-r3`,digest`sha256:61d11e928e0c64d6fc52535892e418809afa94086a2721eca0e772eb9e17531d`,base`CBN_P11ES_TRIAL_20261028_e0a14ef5`,perfil privado`.local/p11-es/final-runtime`,volumen`crm-cbn-p11-media`. Receta:`docker compose -p crm-cbn-current-p11 -f compose.operations.yaml up -d --pull never`. Credenciales humanas conservadas en`.local/p11-es/ACCESS.txt`;no publicarlas. `.local/current-preview/access.json` ya apunta a P11. P10 original queda detenido como`crm-cbn-preview-p10-preserved`,con base/perfil/imagen/volumen intactos. SIIE Windows,C5/C9 y todas las copias anteriores se conservan.

P11 no añade tablas de dominio ni DDL de arranque:SQL2019,motor15/compat150,TLS/CA/nombre validados,185tablas/330FK/155bindings y30académicas protegidas incluidas en185. Principal y cookie propios. Runtime sin lectura/escritura académica,DDL,administración ni respaldo/restauración. En cada transacción nueva se comprueban identidad/modelo/contexto/diarios/ACL completos;P11 recorre una vez la cadena P5–P10 conservando P3/P4. Sin caché entre peticiones. Mismo perfil sobre imágenes R2/R3 reproduce273→121consultas (160→46dehistoria);los tiempos no son SLA. No editar releases/checkers/grafos anteriores ni`es_schema_catalog_v2.py`.

Ajustes→Operación es sólo lectura con`users.manage`:SQL fresco,ocho consumidores con comprobación por etapa/frescura180s,totales completos de colas y recibo HMAC ligado a base/institución/principal/perfil/release. Liveness no es readiness;Docker usa readiness SQL+workers. El recibo se emite después de recuperar SQL y archivos,no sustituye el ensayo ni rehash continuo del`.bak`. Más de24h se muestra vencido;es alerta local,no RPO institucional. No hay API de backup/restore/migración,borrados ni automatización nueva. La retención conserva todas las copias por instrucción humana.

Ajustes reutiliza recurso ligado a ruta+CSRF+secuencia+ciclo de vida;respuestas tardías no cambian otra sección. Los errores de recarga se muestran conservando borradores,incluso en Shell. Credencial cargando/error no se muestra ausente. Comentarios sigue la capacidad Inbox;Canales se puede administrar mientras su procesamiento está pausado. Navegación usa tokens claros/oscuros Glass,sin rediseño. Proxy propio P11:90s para APIs con varias transacciones acotadas;SQLquery20s/applock15s intactos.

Pasan440backend/354frontend,tipos/lint. Autoridad:150rol/acción,188método/ruta y510CSRF (102escrituras×5roles),55lecturas porrol y extras5. Workers22 en segmentos18+4 tras nuevo login real por confirmación vencida;guard8 incluye corrupción rollback-only de seis diarios sin cambiar185tablas. Son recibos distintos,no sumarlos como tests únicos. UI28rutas/112celdas en segmentos84R2+28R3,siete estados de error/carga/borrador,teclado y smoke final R3. Admisiones muestra integración pendiente:no aceptación académica ni auditoría formal de accesibilidad.

Recuperación de fixture y principal final:backupCOPY_ONLY/CHECKSUM/VERIFYONLY,comparación inicial185tablas,CHECKDB,secretosAccess/C10/Ads autenticados y cuatro archivos privados validados. Tras revocar sesiones/OAuth/autoridad copiada y pausar productores/modelos,171tablas estables conservan huellas. El panel valida el recibo de su propia recuperación. Reinicio real:15checks,misma sesión,182tablas estables y cuatro archivos descargados/verificados porhash. Seis lecturas de mensajes con concurrencia2:4.660–6.909ms;observación local,no carga institucional. Reversión8checks sobre una recuperación P10 NUEVA con imagen congelada;P10 original conserva185tablas. P11 vuelve a4178 con182tablas estables;Session/Audit/RateBucket se excluyen expresamente por ser volátiles.

Se conservan11contactos/11conversaciones/26mensajes,3agentes,5packs,256muestras y4artefactos sintéticos. Modelos restaurados pausados hasta revisión. Cero consentimientos comerciales concedidos,intentos masivos,inscripciones,cuentasAdsconectadas o efectos externos nuevos. Aprendizaje sigue siendo variante logística JSON,con datos numéricos revisados y finalidad explícita;no equivalencia con HistGradientBoosting ni eficacia institucional. Abandono sin evidencia vigente se muestra sin evaluación,no inventar resultados demo. HORARIOSSIIE es un fragmento:no afirmar mapeo completo DBSIIE.

Fallos conservados en`artifacts/p11-es/failures.json`:preparaciones rechazadas,backup concurrente rechazado,primer503deauditoría no reproducido,arnés UI corregido y reversión repetida con volátiles explícitos. Timeout real de mensajes motivó ajustes P11;no se ocultaron intentos ni se debilitaron guardas. Las copias fallidas se conservan:no escoger base por fecha/nombre parecido.

Continuidad:`tasks/p11-es-progress.json`,`tasks/p12-online-backlog.json`,`docs/adaptation/sql/SQL_P11_ES_REVIEW.md`,`P11_OPERATOR_RUNBOOK.md`,`P11_ES_CHECKPOINT.md`,`artifacts/p11-es/criteria-matrix.json`,`docs/adaptation/sql/p11_es_validation.json` y`graphify-out/p11-es/`. Checkoffline:`python -X utf8 -B backend/tools/check_p11_es_checkpoint.py --self-test --replay-parent`;grafo:`python -X utf8 -B backend/tools/p11_es_graphs.py check`. Replay exacto1.769preimágenes P10→P9→P8→P7→P6→P5→P4→preview→P3→P2→P1,sinSQLIO. Siete ZIPinmutables se enlazan sólo trasSHA,no código mutable. Revisiones semánticas son estáticas;tokensUNMEASURED yparserSQLopcional ausente.

No reejecutar preparadores/seeds/calificadores en bases pobladas. El preparador P11 usa P10 como base de fixtures;trabajo futuro debe partir del P11 vigente. El contenedor`crm-cbn-p11-reversal-preserved`,perfil`.local/p11-es/reversal-p10-runtime` yvolumen`crm-cbn-p11-rollback-media` son otra recuperación P10 para ensayo,no el P10 original. Revertir exige detener primero la ocupante de4178,preservar base/perfil/media/recibos y comprobar readiness al regresar. PendienteP12:Linux+DNS/HTTPS,SQL/mapeos completos,appsMeta/TikTok,custodios/retención/RPO-RTO yaceptación institucional. No pedir contraseñas porchat ni fabricar verificación externa.

| Fase | Avance técnico con parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 100,00% | 5/5 |
| P7 | 82,29% | 2/5 |
| P8 | 95,00% | 3/4 |
| P9 | 93,75% | 3/4 |
| P10 | 95,00% | 4/5 |
| P11 | 72,50% | 2/4 |

P12:0,00% de ejecución online auxiliar, fuera del denominador general.

## Historia anterior a P11; prevalece el estado superior

## Estado vigente P10-ES parcial — 2026-10-28

**Roadmap general: 90,23%. P10: 95,00%; cuatro de cinco criterios aceptados localmente y 23 de 24 hitos realizados.** El hito P10.close.m4 exige cerrar P8/P9, que conservan dependencias externas pendientes. No declarar P10 al 100%. Cada cierre debe incluir el porcentaje general y el avance por fase, contando trabajo parcial. El general suma equivalentes realizados en 56 criterios de peso uno y divide por 56; no es un promedio simple de fases ni el ratio de 279 hitos.

La aplicación acumulada sigue en **http://127.0.0.1:4178/#/intelligence**. Imagen `crm-cbn-workspace:p10es-r2`, digest `sha256:d053356e8ea6b5aa23d09ae9422a9e6d1464955748dfc0ca9ce9bcee567e08c1`, base `CBN_P10ES_TRIAL_20261028_014cc86f`, perfil privado `.local/p10-es/final-v2-runtime`, volumen `crm-cbn-p10-media`. Receta: `docker compose -p crm-cbn-current-p10 -f compose.learning.yaml up -d --pull never`. Se mantienen las credenciales humanas; están guardadas privadamente en `.local/p10-es/ACCESS.txt`. P9 R9 queda detenido como `crm-cbn-preview-p9-preserved`, con imagen/base/perfil/volumen intactos. No redirigir SIIE, C5/C9 ni copias anteriores.

Inteligencia integra packs/versiones, autorización por finalidad, muestras revisadas y correcciones append-only, datasets temporales, modelos JSON, evaluación frente a baseline y por segmento, inferencia sombra, deriva, promoción humana y reversión. Son cuatro tareas: prospectos, abandono, seguimiento y anomalías. Las observaciones son numéricas y humanas: se verifica el origen CRM, sujeto y fecha, pero no se reconstruyen automáticamente features históricas desde mensajes. El consentimiento comercial no autoriza entrenamiento. Revocaciones, correcciones o cambios de identidad invalidan usos posteriores afectados sin borrar evidencia.

Se usa regresión logística binaria determinista, identificada como variante institucional; no se afirma equivalencia con el HistGradientBoosting de Scentra. No se carga pickle/joblib ni se añade una red neuronal. Reglas CRM, memoria/ADN, LLM y modelo entrenado permanecen distinguidos. La separación temporal y de sujetos y la normalización sólo de entrenamiento evitan fugas estructurales. Promoción exige evaluación, autoridad reciente y cuatro sujetos distintos en sombra de la revisión actual, con autorizaciones y bindings vigentes. La reversión a un artefacto aprobado sigue disponible al detener nuevos entrenamientos.

SQL Server 2019, motor 15/compatibilidad 150 y TLS validados: **185 tablas, 330 FK y 155 mapeos CRM**, más las 30 tablas académicas protegidas incluidas en el total. Nueve tablas nuevas de dominio y su diario; release congelada `831c4a3f667aa67a94d2b2ae9465be0bbc000388b8b8d40cbd21ec6b4747c67c`. Runtime sin DDL ni acceso académico, con perfil propio, CAS, idempotencia y validación íntegra de modelo/historial/permisos. Un drift real en otra copia es rechazado después de un check válido; no hay caché entre peticiones. No editar releases/checkers/grafos anteriores ni el lector congelado `es_schema_catalog_v2.py`.

Verificación: **419 pruebas backend y 351 frontend**, tipos y lint; P10 aporta 24 puras y nueve UI. Recibos separados: API16, extras15, gates8, almacenamiento12, recuperación8 y fronteras6. El navegador completa 25 checks funcionales y cinco de apariencia/móvil/teclado en segmentos declarados; reinicio real12 conserva la sesión y huellas de 182 tablas. La imagen coincide con 222 archivos de aplicación. No sumar esos recibos heterogéneos como pruebas únicas. Recuperación poblada conserva 171 tablas estables y cuatro blobs privados, autentica secretos existentes y pausa modelos/productores; su snapshot de fixture precede al seed del preview y no acredita efectos posteriores.

El preview conserva 11 contactos, 11 conversaciones, 26 mensajes y las funciones/datos P2–P9. Añade cuatro packs ficticios, 256 muestras y cuatro modelos con 48 muestras de entrenamiento/16 de validación por tarea. Las mejoras medidas son sintéticas, no eficacia institucional real. El navegador añade un quinto pack ficticio vacío, con entrenamiento detenido y autorización ficticia revocada. Cero consentimientos comerciales, intentos, inscripciones, gasto o envíos externos nuevos. Packs/autorizaciones y listados paginan; el catálogo inicial limita contextos CRM y campañas recientes a 200. No afirmar mapeo completo DBSIIE.

Se preservaron fallos de preparación: constraint duplicado corregido antes de congelar; prueba inválida del último propietario sustituida por un usuario de consulta separado; generador demo inicial con grupo incorrecto rechazado y conservado como prototipo `CBN_P10ES_TRIAL_20261028_cea278a8`. No reparar sus muestras inmutables con UPDATE ni apuntar el preview a él. El destino válido es `final-v2`. La revisión semántica es estática; los recibos SQL/API/UI están separados. Tokens no medidos; el parser SQL opcional no está instalado.

Roadmap fijo: **252/279 hitos realizados y 43/56 criterios aceptados**. P4/P7 permanecen en 82,29%, P8 en 95% y P9 en 93,75%; no hay dominio/apps reales de proveedor para cerrar sus dependencias.

| Fase | Avance técnico incluido parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 100,00% | 5/5 |
| P7 | 82,29% | 2/5 |
| P8 | 95,00% | 3/4 |
| P9 | 93,75% | 3/4 |
| P10 | 95,00% | 4/5 |
| P11 | 25,00% | 0/4 |

Continuidad: `tasks/p10-es-progress.json`, `docs/adaptation/sql/SQL_P10_ES_REVIEW.md`, `artifacts/p10-es/acceptance-review.json`, `docs/adaptation/sql/p10_es_validation.json` y `graphify-out/p10-es/`. Check offline: `python -X utf8 -B backend/tools/check_p10_es_checkpoint.py --self-test --replay-parent`; grafo: `python -X utf8 -B backend/tools/p10_es_graphs.py check`. El replay conserva 1660 preimágenes exactas y la cadena P9→P8→P7→P6→P5→P4→preview→P3→P2→P1 sin SQL IO ni modificar checkers anteriores. No reejecutar preparadores, seeds o calificadores sobre copias pobladas.

Revertir: pausar predicción/entrenamiento y seleccionar un artefacto aprobado previo conservando muestras/evaluación. La recuperación crea base/perfil/media nuevos y exige revisión de selecciones pausadas. Para volver a P9, conservar P10/base/volumen, detener P10 e iniciar sólo P9 retenido en 4178. Próximo: aceptación externa cuando existan apps/dominio o P11 bajo una nueva solicitud. Una modificación futura del estimador requiere nueva versión de algoritmo y evaluación; no reinterpretar artefactos existentes.

## Historia anterior a P10; prevalece el estado superior

## Estado vigente P9-ES parcial — 2026-10-27

**Roadmap general:82,46% técnico ponderado, incluido trabajo parcial. P9:93,75%,3/4criterios aceptados;17/18hitos. Pendiente P9.close.m4 por cierre de P4. No declarar100%.** Preferencia humana permanente: cada respuesta final de trabajo debe incluir porcentaje general del roadmap y porcentajes por fase. General=suma de equivalentes realizados en56criterios de peso1 /56; no promedio simple de fases ni ratio de279hitos. Se conservan pesos/textos/denominadores fijos y aceptación separada.

Aplicación única acumulada: **http://127.0.0.1:4178/#/ads**, imagen `crm-cbn-workspace:p9es-r9`, base propia `CBN_P9ES_TRIAL_20261027_94ba4b55`, perfil privado `.local/p9-es/final-runtime`, volumen `crm-cbn-p9-media`, receta `docker compose -p crm-cbn-current-p9 -f compose.ads.yaml up -d --pull never`. Mismas credenciales humanas en `.local/p9-es/ACCESS.txt`, privadas. P8R7 queda detenido como `crm-cbn-preview-p8-preserved`; imagen/base/perfil/volumen/evidencia/grafo intactos. P7/P6/P5/P4/C5/C9 y SIIE no se redirigen.

Publicidad adapta la fuente Scentra real: cuentasMeta/TikTok, campañas y presupuestos/CTR/CPC/leads registrados con período, formularios/leads, comentarios de anuncios,6indicadores y vínculos CRM/Inbox/programa/etapa. La fuente no tiene MarketingAPI HTTP/publicación/gasto: no se inventa sincronización, gasto ni last_sync_at. OAuth continúa en Canales. AdsCreative/ContentStudio/Advisor/WooCommerce/planes/cobros quedan fuera de este dominio. Estados declarados separados de verificación externa; UI conserva estiloCBN y detalles por cuenta.

Recibos C10 firmados vigentes usan cursor propio Ads sin modificar Status/Attempts/Lease C10. Mapeo explícito de anunciante o formulario/campaña único por canal; ambiguos/incompletos/contexto pausado/no verificado/ruta cambiada quedan en cuarentena, con reintentoCAS revisado e historial. NormalizaciónMeta leadgen/directa yTikTok anidada acotada, aliases con ID externo explícito; firma/client_key y fechas desbordadas probadas. Sin segundo reply worker ni productor B011 automático. Formularios crean contexto CRM humano y nota; no fabrican DM, ventana24h, LastIncomingAt ni consentimiento.

Identidad aislada por institución/cuenta/canal; coordenadas útiles sólo dentro de la misma cuenta. Teléfonos inválidos no colapsan personas. Identity/Note/_crm persisten ContactId histórico, lecturas resuelven canonical; conversiones antes/después de merge yundo preservan vínculo. P4/P9 reutilizan autor/contacto/conversación en ambos órdenes, incluso lead previo al primer comentario. Eventos/secretos AES-GCM versionados append-only; acceso sensible exige permisoCanales yautenticación reciente; revocar retira puntero sin borrar versiones.

SQL2019 motor15/compat150/TLS validado:175tablas/304FK/145mapeosCRM+30académicas protegidas. Siete tablasAds+diario propios. Releasev1P9ES-000/001 congelada; extensión aditivav2P9ES-002 añade ignored yCHECKconversión fuerte sin reescribir historial. Runner conapplock/secuencia/drift/fallos/reconciliación; perfilv2 autentica modelo/diario/base/principal/permisos ysecretos. Sin DDL de arranque, acceso académico ni ALTER del diario desde runtime. Mapeos educativos siguen catálogoCRM declarado, no afirmar DBSIIE completo.

395pruebas backend/342frontend, tipos/lint pasan; P9puras34/UI10. API16/Meta14/extras12/TikTok4/storage12/recuperación8 son recibos separados, no suma de pruebas únicas. SQL fallos/concurrencia/drift en4copias propias; conversión/merge/undo/permisos/CSRF/módulo probados. El navegador detectó GETtardío tras navegar: hookAds por vista+CSRF/secuencia/cleanup, guard de editor descartado y generación paraProcesar/Reintentar;3regresiones diferidas. Prueba históricaSettings espera la misma lectura única asíncrona. Contención nativa3checks: bloqueo exclusivo6s; sóloP9 espera15s porapplock, manteniendo SERIALIZABLE/TLS/validaciones/SQLtimeout5s; perfiles anteriores5s. Logging sóloetapa/clase/tag. Recibos visuales yreinicio real se conservan aparte.

Recuperación poblada mantiene162tablas estables, autentica todas versiones Access/C10/Ads, revoca sesiones/OAuth/aprobaciones ypausa cuentas; cuatro blobsprivadosP8 copiados/verificados en nueva raíz. Ese snapshot precede últimas API16/extras12, no afirmar recuperar efectos posteriores al backup. RespaldoSQL no incluye archivos. Reinicio real conserva172tablas estables, sesión, ejemplosAds yblobP8. FuenteP8 y30académicas de su respaldo fresco conservan huellas; WindowsSIIE no se reconsulta ni modifica.

Preview conserva8contextos originales/26mensajes, notas/tareas/comentarios,3agentes yconocimiento/memoria/ADN/ajustes/canales/borradores anteriores. Añade2cuentasAds pausadas/2campañas enborrador/2leads/1comentario etiquetados Ejemplo ficticio y3contextosCRM humanos. Cero consentimientos/inscripciones/intentos/aprobaciones/gasto/envíos externos nuevos. No hay dominio/apps reales: P4/P7siguen82,29%; P8sigue95% y P9cierre dependeP4.

Roadmap fijo: **231/279hitos realizados,48pendientes;39/56criterios aceptados**. Las pruebas locales no sustituyen la aceptación externa ni alteran definiciones para alcanzar100%.

| Fase | Avance técnico incluido parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 100,00% | 5/5 |
| P7 | 82,29% | 2/5 |
| P8 | 95,00% | 3/4 |
| P9 | 93,75% | 3/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Continuidad: `tasks/p9-es-progress.json`, `docs/adaptation/sql/SQL_P9_ES_REVIEW.md`, `artifacts/p9-es/acceptance-review.json`, `docs/adaptation/sql/p9_es_validation.json`, `graphify-out/p9-es/`. Verificadoroffline: `python -X utf8 -B backend/tools/check_p9_es_checkpoint.py --self-test --replay-parent`; grafo: `python -X utf8 -B backend/tools/p9_es_graphs.py check`. Replay P8→P7→P6→P5→P4→preview→P3→P2→P1 desde1562preimágenes exactas, checkers/graphs/releases anteriores intactos. Uso tokens no medido. No reejecutar preparadores/seeds/calificadores sobre copias pobladas.

Reversión: pausar disponibilidad local de la cuenta, conservar IDs externos/captaciones/procesos/eventos, no tocar anuncios reales para revertirUI. Recuperación siempre nueva base/perfil/media y revisión antes de activar. Para volver aP8, conservar primeroP9/base/volumen, detenerP9 y arrancar sóloP8retenido en4178; nunca fusionar efectos inciertos. Próximo: aceptación externaP4 cuando existan apps/dominio; P10requiere nueva autorización.

## Historia anterior a P9; prevalece el estado superior

## Estado vigente P8-ES parcial — 2026-10-27

**P8:95,00% técnico;3/4criterios aceptados (P8.1/P8.2/P8.3). Pendiente P8.close.m5 por cierre real de P7/P4. No declarar100%.** Preview único acumulado: **http://127.0.0.1:4178/#/campaigns**, imagen `crm-cbn-workspace:p8es-r7`, base propia `CBN_P8ES_TRIAL_20261027_1908de72`, perfil privado `.local/p8-es/final-runtime`, receta `docker compose -p crm-cbn-current-p8 -f compose.campaigns.yaml up -d --pull never`, volumen `crm-cbn-p8-media`. Mismas credenciales humanas, guardadas privadamente en `.local/p8-es/ACCESS.txt`. P7 queda detenido como `crm-cbn-preview-p7-preserved` con imagen/base/perfil/volumen intactos. P6/P5/P4/C5/C9 y SIIE no se redirigen.

Campañas, flujos, activadores, segmentos y plantillas CRM funcionan sobre SQL Server2019 con CAS, CSRF, roles, versiones inmutables, copia/restauración revisada y preflight vinculado a sesión/documento. Flujos persistidos de espera/condición/envío, horarios IANA/DST y activadores futuros por mensaje/etapa/programa/inactividad. Identidad canónica, respuesta, consentimiento/no-contactar, rol y control humano se revisan antes de efectos. Pausa/reanudación conserva plazos y partes aceptadas; efectos inciertos nunca se reenvían automáticamente. Una sola cola C10 y dispatcher P7; no arrancar el worker legado de campañas ni B011 automático.

Plantillas CRM admiten bloques texto/enlace/imagen/audio/video/documento, uploads inspeccionados, grabación por gesto, preview/descarga autenticados y demoras persistidas por parte. Caption social es texto independiente; WhatsApp conserva caption de video y nombre editable del documento. Instagram Login usa URL firmada por perfil/institución/cola/media de600s con comprobación de estado, contexto e integridad. Requiere PublicBaseUrl HTTPS institucional. Biblioteca privada y cuota total compartida;5MB/archivo, audio300s, video120s/1920×1080, TikTokimagen3MB+IMAGE_SEND; otros medios TikTok rechazados. La simulación resume pasos, no el cronograma exacto de cada parte. A/B determinista y métricas observadas; respuesta atribuida sólo por contexto explícito, sin conversiones/ganadores inventados.

SQL motor15/compat150/TLS verificado:167tablas totales/284FK/137mapeos CRM+30tablas académicas. Release P8 congelada, seis tablas+diario propios; metadatos media usan Event JSON, sin nueva DDL.361pruebas backend/332frontend, tipos ylint pasan;API16/runtime13/extras6/storage12/recovery9/boundaries3/wait-resync3/media9/caption4/Instagramdelivery6. Espera real2min+reinicio4; navegador20+adjunto3+smoke/reinicio9. Son recibos de alcances distintos, no una suma de pruebas únicas. Runtime13 continúa9 comprobaciones registradas y extras6 continúa5 tras ajustes del calificador. Media9 usó codecR5; correcciones posteriores tienen pruebas actuales361/332 y caption4/delivery6.

Restauración poblada v2 preserva155tablas estables, incertidumbre y11blobs privados en raíz nueva (snapshot anterior a caption/delivery adicionales). El backupSQL solo no contiene archivos. Reinicio real conserva164tablas estables, la sesión y el adjunto demo. Fuente P7 y30tablas académicas de su copia conservan huellas; no se reconsulta Windows SIIE ni se afirma mapa completo DBSIIE. El catálogo usa JOINs de sys.sql_modules/constraints/triggers; no restaurar OBJECT_DEFINITION escalar del código histórico para validación SQL viva.

Preview conserva8contactos/8conversaciones/26mensajes, notas/tareas/comentarios,3agentes y conocimiento/memoria/ADN previos. Añade5registros P8 de ejemplo en borrador y adjuntos ficticios privados; sin inscripciones, consentimiento comercial, intentos o efectos de proveedor. Cuenta pendiente/cadencia deshabilitada. No existen todavía dominio/apps/catálogo/recibos Meta reales; P4 yP7 permanecen82,29% y su aceptación externa no se fabrica.

Roadmap fijo: **215/279hitos realizados,64pendientes;36/56criterios aceptados**. P8 tiene21/22hitos realizados. Su95% sale de3criterios completos+4/5del cierre; se conserva el peso de P8.close.m5. No modificar denominadores ni sustituir aceptación real por fixtures.

| Fase | Avance técnico, incluido parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 100,00% | 5/5 |
| P7 | 82,29% | 2/5 |
| P8 | 95,00% | 3/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Continuidad: `tasks/p8-es-progress.json`, `docs/adaptation/sql/SQL_P8_ES_REVIEW.md`, `artifacts/p8-es/acceptance-review.json`, `docs/adaptation/sql/p8_es_validation.json`, `graphify-out/p8-es/`. Verificador offline: `python -X utf8 -B backend/tools/check_p8_es_checkpoint.py --self-test --replay-parent`; grafo: `python -X utf8 -B backend/tools/p8_es_graphs.py check`. Replay P7→P6→P5→P4→preview→P3→P2→P1 desde1464preimágenes exactas; anteriores grafos/releases/checkers intactos. Uso de tokens no medido. No reejecutar preparadores/seeds/calificadores en copias pobladas.

Revertir: pausar flujo, conservar intentos/aceptación/incertidumbre y restaurar versión como borrador con nueva revisión. Recuperación crea base/perfil/raíz media nuevos y retira sesiones/aprobaciones copiadas. Para volver a P7, conservar primero P8/base/volumen y detener P8 antes de arrancar P7 retenido en4178. Próximo trabajo: aceptación externa P4/P7 cuando existan apps/dominio, o siguiente fase bajo nueva autorización.

## Historia anterior a P8; prevalece el estado superior

## Estado vigente P7-ES parcial — 2026-10-27

**P7:82,29% técnico ponderado;2/5criterios aceptados (P7.2/P7.3). No está cerrada al100%.** Aplicación integrada: **http://127.0.0.1:4178/#/broadcasts**. Imagen `crm-cbn-workspace:p7es-r3`, base propia `CBN_P7ES_TRIAL_20261027_c305e024`, perfil privado `.local/p7-es/final-runtime`, receta `docker compose -p crm-cbn-current-p7 -f compose.broadcast.yaml up -d --pull never`, volumen `crm-cbn-p7-media`. Mismas credenciales humanas conservadas privadamente en `.local/p7-es/ACCESS.txt`. P6 está detenido como `crm-cbn-preview-p6-preserved`, con su base/perfil/imagen/volumen intactos; P5/P4/C5/C9 y SIIE no se redirigen.

Mensajería masiva está integrada con cuentas WhatsApp C10, catálogo/versiones de plantillas, creación a revisión sin aprobación local, cabeceras/pie/botones, variables explícitas, audiencia/consentimiento/no-contactar/deduplicación canónica, zona horaria+UTC, preparación sin IO, pausa/reanudación revisada y cadencia en la frontera real del POST. Una sola cola C10 conserva intentos, aceptación y efectos inciertos. Reintento selectivo sólo para fallo definitivo sin ID proveedor; un merge tras aceptación no permite duplicar a la persona. Catálogo/credencial/contexto/autoridad se vuelven a validar justo antes de enviar. Recibos adelantados se concilian; respuesta atribuida sólo por context.id+cuenta+remitente. Informe/CSV filtrados y paginados en SQL, con cuerpo/fechas observadas y protección de fórmulas. El worker/API legado de campañas y productor automático B011 siguen cerrados.

SQL2019 motor15/compat150/TLS:160tablas (130CRM y30académicas protegidas),266FK/130mapeos,6tablas P7+diario nuevos,3entradas de release congeladas, sin DDL de arranque.322pruebas backend/323frontend, tipos ylint pasan;15checksAPI,22ejecución,6extras,12storage,7recuperación,5catálogo;18navegador+7smoke/reinicio. Son alcances separados, sin sumar como pruebas únicas. Runtime22 continúa14checks ya registrados y extras6 continúa5 tras corregir expectativas del calificador; no son dos ejecuciones completas nuevas. Cero proveedores reales. Catálogo/recibos Meta reales y P4 siguen pendientes; no fabricar aprobación ni reinterpretar hitos para llegar100%.

La calificación de reinicio detectó OBJECT_DEFINITION escalar atascado en validación. Se sustituyó por JOINs equivalentes de módulos/constraints/triggers, probados contra15objetos incluyendo NULL cifrado en FAULT propio. Conserva exactamente el digest del perfil, TLS y todas las validaciones. Se reinició sólo el SQL Docker de copias para retirar el rollback no interrumpible; SIIE Windows no participa. Reinicio real posterior conserva157tablas estables y sesión. Restauración poblada conserva150tablas estables y dos trabajos inciertos; trabajadores nuevos no reencolan ni hacen POST. Fuente P6 coincide con su respaldo fresco y30académicas vacías siguen iguales. No se afirma mapeo completo de DBSIIE ni recuperación de archivos poblados (ready0).

Se conservan8contactos/8conversaciones/26mensajes/8notas/8tareas/3comentarios,3agentes y6registros de conocimiento. P7 añade cuenta ficticia pendiente, campaña y2plantillas de ejemplo en borrador; sin consentimiento, destinatarios, intentos o aprobaciones de proveedor falsos. Cuenta/cadencia/envío permanecen deshabilitados. Guardar agente válido sigue disponible, editar pausado conserva pausa, diagnóstico opcional; fuentes/etapas/acciones sensibles conservan sus controles propios. Memoria/ADN privados y colectivos mantienen el contrato P6.

Roadmap fijo: **201/279hitos realizados,78pendientes;33/56criterios aceptados**. P7.1.m5/m7 requieren catálogo Meta aprobado real; P7.4.m4/m5 requieren recibos externos; P7.close.m5 depende del recorrido completo/P4. No hay dominio/apps reales. El progreso técnico incluye trabajo parcial, sin otorgar crédito canónico a un criterio incompleto.

| Fase | Avance técnico, incluido parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 100,00% | 5/5 |
| P7 | 82,29% | 2/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Continuidad: `tasks/p7-es-progress.json`, `docs/adaptation/sql/SQL_P7_ES_REVIEW.md`, `artifacts/p7-es/acceptance-review.json`, `docs/adaptation/sql/p7_es_validation.json`, `graphify-out/p7-es/`. Verificador offline: `python -X utf8 -B backend/tools/check_p7_es_checkpoint.py --self-test --replay-parent`; grafo: `python -X utf8 -B backend/tools/p7_es_graphs.py check`. No volver a ejecutar preparadores/seeds/calificadores sobre copias pobladas. Replay P6→P5→P4→preview→P3→P2→P1 desde1382preimágenes exactas; verificadores/grafos anteriores intactos, uso de tokens no medido.

Revertir campaña: pausar y conservar intentos/recibos/incertidumbre antes de revisión. Revertir fase: conservar primero P7/base/volumen, detener P7 y arrancar P6 retenido; nunca ambos en4178 ni fusionar efectos inciertos. Próximo trabajo: validación real P4/P7 cuando existan apps/dominio, o P8 bajo nueva autorización.

## Historia anterior a P7; prevalece el estado superior

## Estado vigente P6-ES local — 2026-10-27

**P6:100,00% local,5/5 criterios.** Aplicación integrada: **http://127.0.0.1:4178/#/knowledge**. Imagen `crm-cbn-workspace:p6es-r2`; base propia `CBN_P6ES_TRIAL_20261027_a6fc321d`; perfil privado `.local/p6-es/final-runtime`; mismas credenciales humanas en `.local/p6-es/ACCESS.txt`. Receta vigente: `docker compose -p crm-cbn-current-p6 -f compose.knowledge.yaml up -d --pull never`.

Conocimiento PDF/TXT, citas léxicas con página/versión, fuentes revisadas por ámbito/vigencia/visibilidad, memoria colectiva, ADN institucional y memoria privada del Inbox están integrados. Corrección crea borrador; publicación requiere revisión explícita; archivo retira el contenido; recuperar una versión publicada añade versión e historial. Sólo se reconstruyen índices derivados. Datos «Sólo equipo editor» nunca entran al prompt; hechos privados exigen mensaje entrante/cita literal y quedan ligados a conversación/contexto/revisión. Generic simulator no lee esos hechos. Cambios de memoria/ADN/fuentes o de switches de módulos invalidan contexto y replay confirmado sin segunda inferencia. Confianza editorial0 se conserva al cargar y editar.

Pasan288pruebas backend,316frontend, tipos/lint;45checksAPI,14ejecución,13negativas extra,12storage,5recuperación,5replay/switch/carga;15checks de navegador y5smoke/reinicio. Alcances separados. Tres preguntas educativas sintéticas recuperan fuente esperada en posición1; no mide precisión institucional. Cero proveedores reales. PDF/TXT sin URL remota/OCR/CSV/vectores nuevos. Referencias validadas por ID no equivalen a entailment. Productor automático B011 sigue cerrado.

SQL2019 motor15/compat150 con TLS validado:153tablas,249FK,123mapeos. Release P6 `cf32dcab88a1e0467c5ae58fa2863e16df13ce906d246a3df43ceb8eb311f5ff`,3entradas congeladas. Diario, registro tipado y versiones append-only; sin DDL de arranque. Recuperación conserva148tablas estables; reinicio150. Preservación final compara105tablas heredadas y30académicas vacías contra respaldo fresco de P5. No se consultó de nuevo SIIE Windows ni se modifica su estructura/datos. El catálogo sigue declarado CRM, sin afirmar mapeo completo de DBSIIE. Volumen P6 propio con0blobsready; no afirmar recuperación de archivos poblados.

P5 queda detenido en `crm-cbn-preview-p5-preserved`, con imagen/base/perfil/volumen intactos. P4,C5,C9 y demás checkpoints preservados. Para revertir fase: detener P6, conservar primero su base/historial/volumen y arrancar el contenedor P5 retenido; nunca simultáneamente en4178 ni fusionando efectos inciertos. Se conservan8contactos/8conversaciones/26mensajes/8notas/8tareas/3comentarios y3agentes educativos. P6 añade fuentes, criterio colectivo y ADN ficticios; navegador añade guías de ejemplo. La pausa del agente de programa se conserva, sin activar al descendiente para la demostración. Guardar perfil válido sigue disponible, editar pausado conserva pausa, diagnóstico opcional; fuentes/etapas/acciones sensibles mantienen controles propios.

Roadmap fijo: **189/279hitos realizados,90pendientes;31/56criterios aceptados**. Pesos/textos conservados. **P4 sigue82,29%** por aceptación externa pendiente; próxima fase **P7 Mensajería masiva**.

| Fase | Avance técnico, incluido parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 100,00% | 5/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Continuidad: `tasks/p6-es-progress.json`, `docs/adaptation/sql/SQL_P6_ES_REVIEW.md`, `artifacts/p6-es/acceptance-review.json`, `docs/adaptation/sql/p6_es_validation.json`, `graphify-out/p6-es/`. Verificación **offline**: `python -X utf8 -B backend/tools/check_p6_es_checkpoint.py --self-test --replay-parent`; grafo: `python -X utf8 -B backend/tools/p6_es_graphs.py check`. No volver a ejecutar preparadores, seeds ni calificadores SQL sobre copias pobladas. Replay P5→P4→preview→P3→P2→P1 desde1304preimágenes exactas; ningún verificador padre modificado. Tres referencias históricas conservan bytes/SHA en `docs/adaptation/history/p6-predecessors/`. Grafos anteriores congelados; uso de tokens no medido.

## Historia anterior a P6; prevalece el estado superior

## Estado vigente P5-ES local — 2026-10-27

P5 cerrada al **100,00% local,4/4 criterios canónicos**. Un solo CRM CBN integrado: **http://127.0.0.1:4178/#/agents**. Imagen `crm-cbn-workspace:p5es-r5`, base propia `CBN_P5ES_TRIAL_20261027_13990dac`, perfil privado `.local/p5-es/final-runtime`, acceso `.local/p5-es/ACCESS.txt` con las mismas credenciales humanas. Receta vigente: `docker compose -p crm-cbn-current-p5 -f compose.agents.yaml up -d --pull never`. P4 conserva imagen/base/perfil/volumen y contenedor detenido `crm-cbn-preview-p4-preserved`; P3 y los demás checkpoints siguen conservados. No iniciar sus recetas simultáneamente en4178.

Constructor, jerarquía orientador→programa→etapa, personalidad/instrucciones/variables/reglas/objetivos/herramientas/canales, modelos/fallback/cuotas por perfil, diagnóstico opcional, archivo/restauración/versiones y asignación desde el Inbox real están integrados. Guardar válido deja disponible; editar pausado conserva pausa. Etapas, fuentes y acciones sensibles mantienen sus controles separados. Simulación fija agente/versión; actor/nonce/hash/lease evita doble inferencia. Handoff, pausa y epoch invalidan resultados y envíos antiguos. No se activa IA automática por guardar ni se monta el productor B011; una sola outbox C10. Restaurar configuración crea versión nueva en pausa y conserva memoria, historial y asignaciones.

Se conservaron8contactos/8conversaciones/26mensajes/8notas/8tareas y3comentarios, y se añadieron3perfiles educativos y1etapa de ejemplo persistidos. El modelo de ejemplo bloquea IO; la prueba de navegador dejó el agente de programa pausado para revisión. El catálogo nuevo es declarado CRM, con ejemplos marcados sintéticos; no representa oferta académica SIIE validada. Vincular solicitud/período sigue cerrado hasta revisar el mapeo real. Publicación/administración/reindexación de conocimiento pertenece a P6; P5 sí aplica ámbito, responsable, vigencia y revisión al recuperar fuentes.

Pasan242pruebas backend,311frontend, tipos y lint(exit0,1warning histórico de cleanupEpoch),19checks de navegador y smoke tras reinicio;8constructor/API,22ejecución,18ciclo/fuentes/handoff,28C10/dispatch,8archivo/tarea/techos,3replay de contexto,10storage y5recuperación. Los conteos son alcances separados. Cero llamadas a proveedores reales: las inferencias y transportes de calificación son controlados. No hay dominio/apps reales; **P4 permanece82,29%**, sin aceptar recepción/OAuth/envío externo por esta fase.

Release P5 `9046a8c33a3bbbb9d874ba0fc5451e3db5815c9afcc9b6552aabb6b0d2a2793a`:3entradas congeladas,150tablas,242FK,120mapeos. Se conservan14entradas P2 y releases P3/P4. Se comprobaron106tablas de negocio heredadas y30académicas vacías entre fuente/respaldo/P5; no hubo nueva consulta a SIIE Windows. Recuperación conserva145tablas estables, autentica vault y retira sesiones copiadas; reinicio conserva147tablas estables y sesión. La fuente y destino finales tienen0blobsready: volumen propio y copia vacía verificados, sin afirmar ensayo P5 de archivos poblados. Fuente P4 intacta frente a respaldo fresco.

El ledger conserva pesos y textos: **170/279 hitos done,109pending;26/56criterios aceptados**. Los porcentajes incluyen trabajo parcial, no horas ni producción externa.

| Fase | Avance técnico con trabajo parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 100,00% | 4/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Evidencia: `docs/adaptation/sql/SQL_P5_ES_REVIEW.md`, `artifacts/p5-es/acceptance-review.json`, `docs/adaptation/sql/p5_es_validation.json`, `tasks/p5-es-progress.json` y `graphify-out/p5-es/`. Retomar con `python -X utf8 -B backend/tools/check_p5_es_checkpoint.py --self-test --replay-parent` y `python -X utf8 -B backend/tools/p5_es_graphs.py check`, offline; nunca con preparadores/seeds/calificadores SQL automáticos. Replay transitorio P4→preview→P3→P2→P1 desde1225preimágenes exactas, sin modificar verificadores. Cinco referencias históricas a dos fuentes cambiadas conservan sus bytes/SHA en `docs/adaptation/history/p5-predecessors/`; la evidencia P5 actual está separada. El replay usa un directorio privado persistente del helper para evitar llenar su tmpfs.

Para revertir un perfil: restaurar versión en pausa y revisar permisos descendientes antes de reanudar. Para volver a P4: pausar entrada/salida, conservar base/solicitudes/colas/volumen P5, detener P5 e iniciar el contenedor P4 conservado. No reparentar datos posteriores ni reenviar efectos inciertos. Siguiente: P6; las validaciones externas P4 necesitan dominio/apps/cuentas reales y conservan sus pendientes.

## Historia preservada anterior a P5

## Estado vigente P4-ES local — 2026-10-27

Un solo CRM CBN integrado: **http://127.0.0.1:4178/#/comments**. Imagen `crm-cbn-workspace:p4es-r3`, base propia `CBN_P4ES_TRIAL_20261026_a8ef717a`, perfil privado `.local/p4-es/final-runtime`, acceso `.local/p4-es/ACCESS.txt` con las mismas credenciales humanas. Receta vigente: `docker compose -p crm-cbn-current-p4 -f compose.channels.yaml up -d --pull never`. La copia P3 demo conserva base/perfil/imagen y contenedor detenido `crm-cbn-preview-p3-demo-preserved`; no levantar simultáneamente las recetas históricas en4178.

Canales por cuenta, callbacks/verify token generados por la aplicación, vault C10, OAuth provisional/selección/verificación, comentarios/filtros/estados/conversión/IA humana y una outbox C10 están integrados con SQL2019. Se conservan los8contactos/8conversaciones/26mensajes/8notas/8tareas demo y se agregan3comentarios ficticios con1cuenta pausada sin egress. Los ejemplos bloquean efectos externos. No hay dominio ni apps de proveedor: **P4 no está al100%**. TikTok Login Kit sólo identidad; Business OAuth/renovación y aceptación real por canal siguen pendientes. Cookie Secure/origen humano/proxy HTTPS se deben calificar bajo el dominio real antes de usar OAuth externo.

P4=**82,29%** técnico,2/5 criterios locales aceptados; P4.3.m6/m7, P4.4.m4/m5 y P4.close.m5 pendientes. Totales158hitos done/121pending sobre279,22criterios/56. Se conservaron textos y pesos fijos; los porcentajes no son horas ni aceptación institucional. P0–P3 permanecen100%. El avance parcial de las demás fases no se borró.

| Fase | Avance técnico con trabajo parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 82,29% | 2/5 |
| P5 | 45,00% | 0/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Evidencia: `docs/adaptation/sql/SQL_P4_ES_REVIEW.md`, `artifacts/p4-es/acceptance-review.json`, `tasks/p4-es-progress.json`, `docs/adaptation/sql/p4_es_validation.json` y `graphify-out/p4-es/`. Pruebas170backend,299/306frontend (7fallos previos de agentes reproducidos en preimágenes),4nuevasUI,15checks navegador,13eventos/medios/pausa,23comentarios/IA/medios,9recuperación,26API,3límites Unicode,7storage y2drift; los conteos son alcances separados, no capacidades únicas. Las notas largas respetan2000unidadesUTF16 y conservan íntegro el comentario original. Reinicio conserva142tablas de negocio y la sesión sigue válida al reemplazar la imagen.

Preservación:107tablas de negocio de la fuente comparadas con backup fresco;30tablas académicas vacías coinciden en respaldo/fuente/P4. No se afirma nuevo fingerprint de filas de HORARIOSSIIE Windows ni de todas las copias: no se escribieron ni redirigieron. Release P4 `fd247602e95f7756deb77c7a71dfd53bf4b18f56eb555c499c1cc69a8d438e5b`,147tablas/236FK/117mapeos. Las14entradas P2 y3P3, los grafos y verificadores anteriores se conservan. Replay offline PREVIEW→P3→P2→P1 desde1128preimágenes públicas sin debilitar checks; Linux evita rutas Windows anidadas largas.

Retomar sólo con `python -X utf8 -B backend/tools/check_p4_es_checkpoint.py --self-test --replay-parent` y `python -X utf8 -B backend/tools/p4_es_graphs.py check`. El replay usa únicamente archivos en el helper Docker, sin SQL. No ejecutar preparadores/calificadores/seed por consultar memoria ni en el arranque. No editar releases, ampliar tickets antiguos, vaciar colas ni reenviar POST inciertos. Para revertir: pausar entrada/salida, conservar base/cola/eventos/volumen P4, detener P4 e iniciar el contenedor P3 conservado; nunca reparentar datos/secretos P4 sobre P3. Los siguientes pasos externos requieren dominio/apps/permisos reales; la infraestructura local por sí sola no los acepta.

## Historia preservada anterior a P4

# Estado actual de CRM CBN

## Preview actual único con datos demo — 2026-10-26

Se desarrolla un solo CRM CBN. La dirección de trabajo es **http://127.0.0.1:4178/#/inbox** y ahora muestra datos ficticios persistidos en SQL Server 2019: 8 contactos, 8 conversaciones, 26 mensajes, 8 notas y 8 tareas. Usa exactamente la imagen P3 R6 ya aceptada; integra usuarios/permisos/ajustes de P2, Inbox/CRM/mini CRM/riesgo de P3 y la configuración de Canales disponible. Las fases parciales todavía incluyen contratos/código/pruebas que no equivalen a una función operativa completa.

La copia demo es `CBN_P3ES_TRIAL_20261026_f6b6fa1f`, con perfil y principal propios. La copia limpia P3 `CBN_P3ES_TRIAL_20261026_606a9bec`, su perfil y su contenedor quedan conservados; sólo su contenedor se detuvo para liberar el puerto. No ejecutar simultáneamente compose.workspace.yaml y compose.preview.yaml en 4178. La receta vigente es `docker compose -p crm-cbn-current -f compose.preview.yaml up -d --pull never`. Acceso privado en `.local/current-preview/ACCESS.txt`; correo y contraseña se conservan. La sesión anterior requiere nuevo login en la copia demo.

Los otros puertos son checkpoints históricos conservados, no productos que se desarrollen por separado. En las próximas fases se promoverá la aplicación integrada al mismo 4178, preservando los datos demo mediante copia/migración revisada; no reiniciar los seeds ni dar al usuario otro puerto por cada fase. SIIE y las copias anteriores permanecen fuera del seed; no hay envíos reales. El ejemplo de riesgo es sintético y vence con la frescura normal de 24 horas; una evaluación obsoleta vuelve a «Sin evaluación».

La demostración facilita revisar lo ya integrado y no añade crédito artificial al roadmap: 147/279 hitos y 20/56 criterios; porcentajes sin cambios.

| Fase | Progreso técnico | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 38,29% | 0/5 |
| P5 | 45,00% | 0/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Detalle vigente: `docs/adaptation/PREVIEW_STATUS.md`, `tasks/current-preview.json` y `graphify-out/current-preview/`. Retomar con `python -B backend/tools/check_current_preview.py --self-test --replay-parent`, offline. Verifica las transiciones de memoria y reproduce P3/P2/P1 congelados; no cambiar sus hashes para aceptar documentos actuales.

## Histórico anterior al preview demo

## Estado vigente P3-ES — 2026-10-26

P3 está cerrada al 100,00% en el alcance canónico local de Inbox, mini CRM, CRM y superficie de riesgo sobre SQL Server 2019. La ficha editable es única, las consultas filtran en SQL antes de paginar y conservan borradores, asignación humana, lectura observada, CAS y reintentos. Notas, tareas, actividad y unificación reversible mantienen el origen institucional. Riesgo por reglas, interés manual y SLA son independientes; evidencia inválida muestra «Sin evaluación». P10 conserva la inferencia entrenada y P5 la asignación/ejecución de agentes IA. Las tareas locales tienen título, fecha, prioridad, responsable y tres estados; no se afirma paridad literal de cada campo Scentra.

Preview general limpio: `http://127. 0. 0. 1:4178/`, base `CBN_P3ES_TRIAL_20261026_606a9bec`, perfil propio revisión 2 y una cuenta propietaria sin fixtures. Acceso humano sólo en `.local/p3-es/ACCESS.txt` con ACL del usuario y SYSTEM. 4177 sigue P2 y4173/4176 sus copias anteriores. Se verificaron intactas6 bases Windows y77 copias SQL2019 anteriores; sin DDL/DML académico, redirección de perfiles ni proveedores.

Release P3 `7d4c3f55654d8d683246c2cd2547d29da5274825170f304b2c6b069e914d379b`:6 tablas nuevas,144 totales,229 FK y114 mapeos; 3 entradas congeladas. No editarlo ni repetir preparadores sobre destinos poblados. Pasaron127 pruebas backend,81 frontend,25 checks SQL/API base,16 únicos de riesgo/17 instancias y24 checks finales de consultas/anclas/umbral74–75. Navegador:12 checks de ficha, reintento tras respuesta perdida, tres paneles, móvil y teclado; 8 checks de perfil limpio y sesión conservada tras reemplazar la aplicación. Tres fallos de migración, concurrencia, restore nativo poblado con2 cuentas/secretos, cuatro denegaciones SQL y persistencia de15 tablas pasaron. Las suites base y las ampliaciones finales conservan sus fuentes y alcances en la revisión.

Hay147 hitos completados/132pendientes sobre279 y20 criterios aceptados/56. Los porcentajes incluyen trabajo parcial con pesos fijos; no son horas, funciones utilizables ni aceptación de producción institucional.

| Fase | Avance técnico con trabajo parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 100,00% | 5/5 |
| P4 | 38,29% | 0/5 |
| P5 | 45,00% | 0/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Evidencia actual: `docs/adaptation/sql/SQL_P3_ES_REVIEW.md`, `docs/adaptation/sql/p3_es_validation.json`, `artifacts/p3-es/acceptance-review.json`, `tasks/p3-es-progress.json` y `graphify-out/p3-es/`. Verificador offline: `python -B backend/tools/check_p3_es_checkpoint.py --self-test`; reproduce los checkers P2/P1 congelados en carpetas nuevas con993 preimágenes y dependencias públicas verificadas por sus hashes originales. No ajustar los hashes de P1/P2 al código P3.

Siguiente: P4, comentarios, canales y webhooks, con la paridad de campos/acciones de Scentra y SQL Server. Conservar SIIE, C5/C9/C13, releases/imágenes/perfiles P1/P2/P3 y sus grafos. El arranque no ejecuta DDL; la devolución al consumidor anterior conserva su propia base y puerto y nunca borra/reparenta datos P3. No ejecutar calificadores para consultar memoria; empezar por checks offline. Proveedores/recepción pública/transporte, campañas, Ads, agentes/memoria operativos y puesta en servicio mantienen sus fases.

## Histórico anterior a P3-ES

## Estado vigente P2-ES — 2026-10-26

P2 está cerrada al 100,00% en administración institucional local sobre SQL Server 2019. Se integraron esquema español, perfil propio, usuarios/permisos/sesiones/MFA, ajustes tipados y UI Glass independiente. El preview limpio está en `http://127.0.0.1:4177/`, sobre `CBN_P2ES_TRIAL_20261026_13f95607`; tiene una cuenta propietaria y cero fixtures. Acceso sólo en `.local/p2-es/ACCESS.txt`, protegido por ACL del usuario y SYSTEM. Sin DDL/DML académico, cambios a SIIE ni redirección de copias anteriores.

Hay 138 tablas, 108 mapeos y 221 relaciones físicas. Release P2 comprometido SHA `1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4`: 14 entradas congeladas, dos unidades y repetición NOOP. No editar sus entradas/diario ni repetir preparadores sobre destinos poblados. Reinicio, restauración poblada de nueve cuentas, MFA/anti-replay y consumidor anterior compatible pasaron. Se conservaron 6 bases Windows y 56 copias SQL Server 2019 previas. 91 pruebas backend, 72 frontend y verificaciones SQL/navegador aprobadas. Las fuentes P1 originales se reproducen desde preimágenes; su checker no se relaja para el código P2.

Los porcentajes cuentan trabajo parcial con pesos fijos: 129 hitos done/150 pending sobre 279, y 15 criterios aceptados/56. P4.3.m5 suma configuración de Canales; P4 pasa a 38,29% sin aceptar proveedores. OAuth, números/tokens externos, webhooks públicos, campañas/envíos, Ads, agentes/memoria operativos, churn y puesta en servicio institucional mantienen sus fases pendientes. No confundir P2 local con producción institucional.

| Fase | Avance técnico con trabajo parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 34,67% | 0/5 |
| P4 | 38,29% | 0/5 |
| P5 | 45,00% | 0/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Ver `docs/adaptation/sql/SQL_P2_ES_REVIEW.md`, `docs/adaptation/sql/p2_es_validation.json`, `artifacts/p2-es/acceptance-review.json`, `docs/adaptation/phase-work-progress.json`, `graphify-out/p2-es/` y `tasks/p2-es-progress.json`. Check actual sin SQL: `python -B backend/tools/check_p2_es_checkpoint.py --self-test`; reproduce P1 en copia aislada. No ejecutar el checker P1 congelado contra archivos actuales y después cambiar sus hashes para hacerlo pasar.

Siguiente fase: P3, Inbox/mini CRM/CRM, filtros antes de paginar y churn/riesgos unificados, sobre una copia propia. Comenzar por comprobaciones offline; los scripts de calificación no son comandos de arranque ni preparadores idempotentes del producto.

## Histórico anterior a este cierre

Actualizado el 26 de octubre de 2026. **P1 cerrada al 100% en su alcance técnico**, con migraciones en una copia restaurada de SQL Server 2019 real (motor 15/compatibilidad 150), TLS verificado, diario, fallos, drift, concurrencia, restauración, reversión y reinicio. P2 continúa en implementación.

El porcentaje principal mide trabajo técnico documentado, incluyendo lo parcial. Se desglosan los 56 criterios canónicos en 279 hitos binarios con pesos fijos: cada criterio conserva peso 1 y sus hitos suman 1. Un hito suma sólo con evidencia revisada; código, prueba pura, SQL, UI y aceptación conservan alcances diferentes. Se usan fracciones exactas y dos decimales para presentar. No mide horas, porcentaje exacto de funciones utilizables ni preparación para producción. La aceptación completa queda en una columna separada; sus dependencias siguen siendo obligatorias.

## Progreso por fase

| Fase | Avance del trabajo | Aceptación completa | Pendiente principal |
|---|---:|---:|---|
| P0 · Inventario y continuidad | **100,00%** | 5/5 (100,00%) | Mantenimiento de inventario y continuidad. |
| P1 · Base SQL Server 2019 y Docker | **100,00%** | 5/5 (100,00%) | Fundación técnica cerrada; adopción institucional completa corresponde a P11. |
| P2 · Ajustes, usuarios y permisos institucionales | **48,67%** | 0/5 (0,00%) | Migración/perfil de acceso, SQL de usuarios y permisos, UI y aceptación. |
| P3 · Inbox, mini CRM y CRM | **34,67%** | 0/5 (0,00%) | Churn con evidencia, paridad avanzada y aceptación de ficha/CRM/Inbox. |
| P4 · Comentarios, canales y webhooks | **35,43%** | 0/5 (0,00%) | UI completa Scentra, secretos operativos, OAuth, verificación y webhooks/transporte. |
| P5 · Agentes educativos | **45,00%** | 0/4 (0,00%) | Integración y ejecución educativa equivalente, permisos y pruebas completas. |
| P6 · Conocimiento, memoria colectiva y ADN institucional | **33,90%** | 0/5 (0,00%) | CRUD de memoria colectiva/ADN, aislamiento, procedencia y recuperación. |
| P7 · Mensajería masiva | **38,57%** | 0/5 (0,00%) | Audiencias/consentimiento, cadencia, colas y entrega externa aceptados. |
| P8 · Campañas CRM y remarketing | **30,83%** | 0/4 (0,00%) | Flujos multietapa, activadores, audiencias, agentes y transporte. |
| P9 · Meta Ads y captación | **6,25%** | 0/4 (0,00%) | Cuentas/permisos Meta, captación, atribución y pruebas autorizadas. |
| P10 · Inteligencia y entrenamiento evaluado | **8,00%** | 0/5 (0,00%) | Datasets/versiones, entrenamiento evaluado y promoción/reversión. |
| P11 · Aceptación y operación | **25,00%** | 0/4 (0,00%) | Suite integral, datos/objetos DBSIIE, seguridad, puesta en servicio y aceptación. |

La revisión reconoce trabajo previo y parcial; el cambio de medición no significa que se hayan implementado de nuevo esas funciones ni que todas estén activas en el preview actual. Hay **113/279 hitos documentados como completados** y 166 pendientes; esos conteos no ponderan las fases. Se conservan 10/56 criterios plenamente aceptados, P0 y P1 completos. No se calcula un promedio global.

El [detalle por criterio](adaptation/WORK_PROGRESS.md) muestra avances y pendientes; el [registro de hitos](adaptation/phase-work-progress.json) conserva fuente, peso, nivel de evidencia y estado. La [definición fija](adaptation/phase-work-definition.json) y el [contrato de aceptación](adaptation/phase-progress-contract.json) evitan inflar porcentajes al subdividir tareas. La regla anterior de crédito cero para parciales aplica sólo a aceptación, sustituida por petición humana para la columna de trabajo.

## Qué se cerró en P1

El ZIP aportado se revisó como material de referencia: 68 tablas CRM con nombres españoles y 30 estructuras académicas, 795 columnas, 162 índices, 170 CHECK y 125 FK. Se ejecutaron los SQL originales sin alterar en una base aislada SQL2019; un release nuevo y separado añade el diario, para 99 tablas. Pasan 75 pruebas focalizadas, ocho fallos recuperables, ocho negativos, seis cambios de catálogo detectados, concurrencia COMMITTED/NOOP, pérdida de confirmación durante reconciliación y seis sentencias realmente denegadas al perfil limitado. Hay respaldo/restauración antes de aplicar y restauración posterior/reversión a un destino nuevo, sin borrar historial. El reinicio conserva catálogo, datos, diario y perfil.

**SIIE, C5, C9, C11, C12 y C13 conservan exactamente sus catálogos y firmas binarias de datos.** El paquete es sólo estructura: no contiene datos, usuarios, credenciales, procedimientos, vistas ni triggers heredados. No se afirma una restauración completa de DBSIIE ni puesta en producción. Los nuevos nombres `dbo.CRM*` no se han impuesto a los repositorios actuales; su adopción necesita bindings y revisión propios en P2. Los previews 4173/4175/4176 mantienen sus versiones y perfiles; sus porcentajes embebidos son históricos. El estado vigente es esta tabla.

[Informe P1](adaptation/sql/SQL_P1_ES_REVIEW.md) · [Evidencia SQL](../artifacts/p1-es/connected-result.json) · [Revisión de aceptación](../artifacts/p1-es/acceptance-review.json) · [Grafo actualizado](../graphify-out/p1-es/graph.html).

## Próximo trabajo

Siguiente: P2, integrar migración de acceso y perfil propios, sesiones/roles/permisos/ajustes con SQL real, después interfaz completa y pruebas de navegador. Decidir explícitamente el enlace del nuevo namespace español; no basta sustituir nombres en los perfiles anteriores. Mantener la jerarquía educativa, el estilo CBN y los campos/acciones de Scentra. La interfaz final debe omitir rótulos de ensayo y códigos internos; todavía no hay una UI P2 nueva publicada.

Regla permanente: actualizar roadmap, hitos/evidencia, memoria y porcentajes P0–P11 en cada entrega, aunque sólo cambie trabajo parcial. Verificar offline con `python -B backend/tools/phase_work_progress.py --self-test` y `python -B backend/tools/check_p1_es_checkpoint.py --self-test`; no ejecutar un preparador SQL para retomar contexto.

## Historia conservada

Los cortes siguientes describen su fecha de aceptación; no sustituyen la tabla vigente ni el cierre P1-ES.

## SQL-C13: qué cambió

SQL-C13 integra el preview general independiente en `http://127.0.0.1:4176/`, sobre `CBN_C13_TRIAL_20261025_1f10a824` restaurada de C12, con perfil cifrado y principal propios. Muestra 14 secciones: CRM/Inbox/mini CRM/Ajustes CRM locales, Canales en lectura segura y pendientes explícitos. C5 (4173), C9 (4175), SIIE, C11 y C12 se conservan, igual que las 50 tablas/44.180 filas académicas y el diario de 17 entradas. Sin DDL, DML académico ni proveedores. Pasan 265 pruebas backend (23 nuevas), 52 frontend (11 nuevas), 25 checks HTTP, 15 SQL y 16 Docker/worker local durable. La imagen autónoma oficial, volúmenes, healthcheck y recuperación por SIGKILL cierran el sprint P1.4. Los workers de fallo quedan detenidos y sus contenedores conservados. TLS permanece verificado.

Siguiente sprint **P2.1**: contrato de ajustes, identidad y permisos institucionales en otra copia de ensayo. El propietario autorizó cerrar el sprint más cercano y continuar con P2 si HORARIOSSIIE resulta insuficiente. P1.close sigue pendiente de un ensayo real en SQL Server 2019; el motor local es SQL2022 Express/160. Los 22 enlaces académicos C13 son candidatos sin aceptación ni aliases activos; confirmar tablas, columnas, tipos, claves y significado antes de habilitarlos. Conservar campos/acciones Scentra; UI completa de Canales, OAuth, secretos operativos y proveedores mantienen sus pendientes. No redirigir C5/C9, repetir preparadores ni conectar SQL automáticamente al retomar; comenzar por checks offline.

[Informe C13](adaptation/sql/SQL_C13_REVIEW.md) · [Evidencia C13](adaptation/sql/sql_c13_validation.json) · [Sprint 100%](../tasks/sql-c13-progress.json).

## SQL-C12: qué cambió

En la copia independiente `CBN_C12_TRIAL_20261025_7a309d11` se integraron23 correspondencias B011, dos secretos recifrados y en estado staged, etapas B006 y repositorios/API nuevos con perfil propio. El recibo heredado queda en cuarentena y la cola sin ruta completa queda identificada para revisión. TikTok conserva NULL en el ID externo que falta.

La API permite borradores de aplicaciones e integraciones, varias cuentas explícitas, lectura de datos migrados, revisión optimista e idempotencia. Las credenciales y los cuerpos cifrados quedan fuera de sus respuestas y de sus permisos SQL. Se conservaron las65 tablas anteriores, el diario 17, SIIE, C5, C9 y C11.

Validación:42 pruebas nuevas y200 regresiones (242),47 comprobaciones SQL/API,15 escenarios de fallos/drift/recuperación y dos rollbacks de importación. La recuperación independiente reproduce el respaldo C11. Estos resultados aceptan el subconjunto local C12; OAuth, proveedores, usuarios institucionales y UI completa tienen pendientes propios.

[Informe C12](adaptation/sql/SQL_C12_REVIEW.md) · [Evidencia](adaptation/sql/sql_c12_validation.json) · [Seis entregables de la unidad](../tasks/sql-c12-progress.json).

## Dónde revisar las pantallas

| Vista | Alcance actual |
|---|---|
| [Aplicación general · 4173](http://127.0.0.1:4173/) | C5: Resumen, CRM, Inbox, mini CRM y Ajustes CRM. |
| [Canales · 4175](http://127.0.0.1:4175/#/settings) | C9: Ajustes de Canales, configuración y lecturas locales aceptadas. |
| [Preview general · 4176](http://127.0.0.1:4176/) | C13: las 14 secciones, CRM/Inbox/mini CRM/Ajustes locales, Canales seguro y progreso por fase. Cada pendiente se identifica. |

4175 monta sólo Ajustes por su contrato de capacidades. La nueva API no amplía automáticamente sus permisos ni los de4173. C13 reúne los subconjuntos aceptados en otra composición y muestra los pendientes, preservando C5/C9. El siguiente sprint es P2.1. No basta desbloquear menús para declarar paridad Scentra.

[Roadmap canónico e historia](SCENTRA_ADAPTATION_ROADMAP.md). El motor local es SQL2022 Express/160; la aceptación SQL2019 institucional permanece pendiente.
