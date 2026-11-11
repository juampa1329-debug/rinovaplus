# P3: Inbox, mini CRM, CRM y análisis de abandono

P3 alcanza **100,00% de sus cinco criterios canónicos** en la composición local de SQL Server 2019. El preview general separado es [CRM CBN](http://127. 0. 0. 1:4178/). La cuenta propietaria y su contraseña están únicamente en `.local/p3-es/ACCESS.txt`, con ACL del usuario y SYSTEM. La copia limpia tiene una cuenta y cero contactos, mensajes, tareas o secretos de prueba.

## Comportamiento integrado

- Inbox consulta en SQL las bandejas, etapas y canales antes de paginar; asigna usuarios institucionales elegibles, conserva control humano/IA y lectura hasta la secuencia observada. El takeover incrementa el epoch y cancela sólo bots sin iniciar. Los envíos iniciados/inciertos se conservan y advierten al operador.
- CRM e Inbox usan una sola ficha editable: etapas, etiquetas y campos configurados, notas con autor, tareas, actividad y origen institucional. La unificación crea vínculos reversibles; no reparenta ni borra contactos o mensajes ni reemplaza autoridad académica.
- Clientes y tareas consultan 25 elementos por página; mensajes, 50 con cursor bigint numérico. Las páginas posteriores requieren ancla de revisión y rechazan cambios concurrentes. Los borradores sobreviven al cambio de persona/sección durante la sesión. Una respuesta perdida conserva la misma acción y revisión para recuperar su resultado sin duplicarlo.
- CRM, Inbox y mini CRM comparten riesgo con estado, origen, frescura, razones, fecha y siguiente acción. La evidencia debe corresponder a identidad/conversación/etapa/watermark vigentes y ejecución completada. Sin evidencia válida aparece «Sin evaluación». Interés manual, SLA, rúbrica y predicción entrenada mantienen significados separados.
- Se conserva Azul noche · Glass, claro/oscuro, tres paneles en escritorio y composición móvil. La ayuda técnica y las razones extensas se despliegan a petición. No hay rótulos de ensayo en las pantallas finales.

## Persistencia y protección

Base limpia `CBN_P3ES_TRIAL_20261026_606a9bec`, perfil propio revisión 2, SQL Server motor 15/compatibilidad 150 y TLS validado. Release `cbn_workspace_spanish_v1`, SHA256 `7d4c3f55654d8d683246c2cd2547d29da5274825170f304b2c6b069e914d379b`, añade seis tablas: cinco de trabajo y su diario. La composición tiene144 tablas,229 FK y114 bindings. Las tres entradas comprometidas SQL/modelo y las14 entradas del release P2 permanecen inmutables. El arranque no ejecuta DDL.

El principal de aplicación conserva DENY sobre30 tablas académicas. La imagen final tiene usuario 10001, raíz de sólo lectura, capacidades retiradas y perfiles/CA de sólo lectura; no monta contraseña administrativa ni volumen de calificación. La cookie propia evita colisión con P2 en4177. Los previews4173/4176/4177 y sus perfiles permanecen independientes.

La comparación conectada preserva catálogo y firmas binarias de **seis bases Windows y77 copias SQL2019 anteriores**. No se importaron registros académicos a la composición española ni se cambiaron SIIE/C5/C9/C13. El esquema proporcionado sigue siendo estructura académica; sus enlaces reales conservan aceptación institucional pendiente.

## Verificación ejecutada

| Evidencia | Resultado y alcance |
|---|---|
| Backend puro |127 pruebas en cinco suites institucionales; DTO, UTF16, permisos, riesgo y regresiones. |
| Frontend |81 pruebas en nueve archivos, Node 24. 20, red deshabilitada; conflictos, borradores, roles, lectura y revisión original tras respuesta incierta. |
| SQL/API base |25 comprobaciones,602 contactos; filtros, edición compartida, notas, tareas, merge/undo, CAS, viewer y CSRF. |
| Riesgo y operación |16 comprobaciones únicas/17 instancias; evidencia sintética de reglas, frescura, invalidación, SLA, handoff, cursores y volumen. |
| SQL/API final |24 comprobaciones de las fuentes actuales; doce colas, programa, límites int, contacto canónico de tareas, anclas requeridas/obsoletas y umbral manual74/75. |
| Navegador real |12 checks de recorrido; mensaje comprometido con respuesta interrumpida y un único registro tras reintento, borradores, paneles a1200/1440 px, teclado, claro/oscuro y móvil sin desbordamiento. Ocho checks del perfil limpio, más sesión opaca conservada tras reemplazo de aplicación. |
| Migración/recuperación |Tres fallos, reintento/NOOP, concurrencia committed/noop, transacción del llamador intacta, drift/destino/release rechazados, cuatro denegaciones SQL. Restore nativo poblado: dos cuentas, secretos autenticados, diario no reescrito y huellas de negocio iguales. |
| Reinicio |15 tablas de cuentas/configuración/secretos/sesiones/auditoría/diarios/trabajo idénticas antes/después; se reemplazó sólo la aplicación P3. |
| Continuidad offline |993 preimágenes; checker P2 original reproduce sus935 fuentes y el checker P1 original. Una dependencia de registro P2 se verifica por su archivo inmutable de872 entradas y cuatro evidencias por hashes ya fijados en el ledger P2. No se relajan los checkers anteriores. |

Los informes base de25 y16 casos corresponden a sus versiones inspeccionadas. Las correcciones finales de ancla obligatoria y cola hot se calificaron con24 casos nuevos; sus preimágenes se conservan. Un fallo previo de collation y otro de orden lexicográfico del cursor se corrigieron en el consumidor, sin cambiar las columnas. Los fallos y copias candidatas se conservan como historia y no se cuentan como aceptación.

## Límites y reversión

El100% corresponde al contrato canónico P3 local. Las tareas usan título, fecha, prioridad, responsable y estados pendiente/completada/cancelada; no se afirma identidad literal con descripción/in_progress de Scentra. La asignación y ejecución de agentes IA pertenece a P5. Proveedores, webhooks públicos y entrega externa pertenecen a P4; campañas, automatismos y entrenamiento siguen sus fases. La prueba de churn usa una ejecución sintética explícita; no acepta un proveedor ni un modelo entrenado.

La reversión conserva la base P3 y devuelve el consumidor a su imagen/perfil/base anteriores, todavía disponibles. No se presenta un ticket de138 tablas a144 ni se elimina el nuevo esquema para hacer pasar un guard antiguo. La restauración poblada a otra copia conserva catálogo/datos/secretos/cuentas del checkpoint, retira sesiones/códigos copiados y conserva el origen del diario. La recuperación sin fuente disponible y puesta en servicio institucional mantienen su aceptación en P11.

La medición conserva56 criterios y279 hitos ponderados:147 completados y132 pendientes; 20 criterios aceptados. P0–P3 =100,00%; P4=38,29%; P5=45,00%; P6=33,90%; P7=38,57%; P8=30,83%; P9=6,25%; P10=8,00%; P11=25,00%. [Desglose por criterio](../WORK_PROGRESS.md), [aceptación](../../../artifacts/p3-es/acceptance-review.json), [contrato](P3_ES_CONTRACT.md), [grafo](../../../graphify-out/p3-es/graph.html).

Retomar con `python -B backend/tools/check_p3_es_checkpoint.py --self-test`, offline. Los calificadores conectados crean datos y no son comandos de arranque ni deben repetirse sobre destinos poblados.
