# P5 — Agentes educativos integrados en SQL Server 2019

P5 completa sus cuatro criterios canónicos en el alcance local de CRM CBN: constructor educativo, ciclo de vida, simulador por perfil y control de ejecución. La aplicación integrada permanece en http://127.0.0.1:4178/ con los usuarios y datos demo anteriores. Guardar una configuración válida la deja disponible; editar un perfil pausado conserva la pausa y el diagnóstico es opcional. La aprobación de etapas, fuentes y acciones sensibles es independiente.

El destino propio es `CBN_P5ES_TRIAL_20261027_13990dac`, motor15/compatibilidad150. La imagen es `crm-cbn-workspace:p5es-r5`; usa perfil, principal y volumen propios. P4 queda detenida y conservada como `crm-cbn-preview-p4-preserved`, con su base, perfil, imagen y volumen originales. P3 y los checkpoints anteriores se conservan. No se ha vuelto a consultar ni escribir HORARIOSSIIE Windows.

## Constructor y contrato

La comparación con Scentra identifica42campos únicos,41editables y1derivado, y15acciones en `artifacts/p5-es/reference-review.json`. Se reutilizan los tipos, constructor, jerarquía orientador→programa→etapa, modelos por perfil, restricciones heredadas, herramientas, personalidad, objetivos, reglas, variables literales, canales, fallback, cuotas y versiones. Se conservan las instrucciones completas; el límite de contexto de ejecución se valida aparte. El transporte de configuración admite8.000.000bytes y rechaza el exceso; las columnas acotadas respetan unidadesUTF16.

Scentra tiene una prueba de IA general que no fija el perfil seleccionado. CBN mantiene simulación explícita por agente/versión y no convierte esa ruta general en evidencia de uso de un agente. El modelo del perfil se aplica a la inferencia sin reemplazar los ajustes globales. Sólo rechazos conocidos previos a inferencia permiten fallback; timeout/5xx/reintentos agotados conservan incertidumbre. CeroUSD por perfil significa sin techo monetario propio; cero tokens o cero presupuesto institucional bloquean la ejecución. Las tarifas son estimaciones del operador, no facturación del proveedor.

Los programas se guardan en un catálogo CRM declarado con autoridad explícita. Los datos académicos de esta copia española están vacíos; no se fabrican oferta, expedientes ni estados SIIE. Vincular solicitud/período queda cerrado hasta revisar el mapeo académico real. La gestión/publicación e indexación de conocimiento pertenecen a P6; P5 sí controla fuentes publicadas, responsable, vigencia, revisión y ámbito antes de recuperar cuerpos.

## Persistencia y efectos

Release aditivo `9046a8c33a3bbbb9d874ba0fc5451e3db5815c9afcc9b6552aabb6b0d2a2793a`: diario, catálogo declarado y solicitudes durables. Hay150tablas,242FK físicas y120mapeos. Se reutilizan las8tablas de agentes previas. Las14entradas congeladas P2 y los releases P3/P4 permanecen intactos; no se ampliaron tickets antiguos. Las copias R1/R2 con permisos incompletos se conservaron y se preparó R3 con autoridad propia, en lugar de alterar sus tickets.

El perfil SQL no puede leer/escribir tablas académicas, ejecutar DDL ni reescribir diario/historial. Los permisos institucionales y CSRF se revalidan dentro de las transacciones y antes/después de IO. El actor UUID completo se codifica en24caracteres para la columna histórica de30. El replay de contexto también fija la conversación de la URL, además de actor, operación y cuerpo.

La solicitud pagada reclama un lease antes de IO y liga actor, perfil, versión, contenido y conversación. Duplicados concurrentes no vuelven a inferir. Pausa, cambio de contexto o atención humana invalidan resultados en vuelo; las reservas inciertas no se reinician ni se devuelven automáticamente. El borrador de Inbox requiere revisión humana y no encola mensajes. Se mantiene una sola outbox C10; guardar perfiles no inicia productores de IA ni el dispatcher B011.

Los envíos humanos P5 fijan el epoch de control y comprueban su frontera antes del POST. La prueba de control humano→IA→humano bloquea el intento antiguo incluso cuando el modo final vuelve a humano. Un efecto ya iniciado no se puede deshacer por una transacción SQL; los resultados inciertos se conservan para revisión, sin reenvío automático. P4 conserva su predicado de cancelación anterior.

Las acciones CRM requieren permisos y aprobación propios. Una nota aprobada crea una nota real y una tarea aprobada crea una tarea real, una sola vez. Restaurar configuración crea una versión nueva en pausa; conserva historial, memoria y asignaciones. No reescribe perfiles descendientes: si sus permisos exceden los de la versión recuperada, su ejecución permanece bloqueada hasta revisión.

## Verificación ejecutada

| Evidencia | Resultado |
|---|---:|
| Backend institucional, agentes y regresiones P2/P3/P4 |242pruebas aprobadas|
| Suite frontend completa |311pruebas aprobadas|
| Tipos y lint de la superficie integrada |exit0;1warning histórico de cleanup de epoch|
| Constructor SQL/API |8comprobaciones|
| Ejecución, replay, cuotas, concurrencia y pausa |22comprobaciones;5inferencias controladas|
| Jerarquía, fuentes, acciones, handoff y reversión |18comprobaciones;1inferencia controlada|
| C10 y propiedad durante dispatch |28comprobaciones|
| Archivo, restauración, tarea y techos propios |8comprobaciones|
| Replay de contexto bajo otra conversación |3comprobaciones|
| Fallos, concurrencia, drift y permisos SQL |10comprobaciones|
| Recuperación nativa poblada |5comprobaciones|
| Navegador escritorio/móvil |19comprobaciones y smoke tras reinicio|

Los conteos corresponden a alcances distintos; no son funciones únicas ni pesos del roadmap. Se usaron gateways y transportes controlados, con0llamadas a proveedores reales. No se afirma aceptación externa de IA, OAuth ni mensajería.

La recuperación compara145tablas estables, incluyendo configuración, memoria, asignaciones, solicitudes, historial y vault; retira sesiones copiadas y vuelve a validar TLS/login. La fuente conserva su fingerprint de150tablas durante ese ensayo. Antes de promover,106tablas de negocio heredadas coinciden entre P4 y P5; el negocio P4 coincide con su respaldo fresco. Las30tablas académicas vacías coinciden. El reinicio conserva147tablas estables y la sesión del navegador.

Hay0blobsready en la fuente y el destino finales. Se ejecutó la copia validada hacia un volumen P5 propio, con el volumen P4 montado sólo en lectura. Esta evidencia cubre una partición vacía; no acredita un ensayo de recuperación P5 con archivos poblados. La evidencia de medios anterior permanece en P4.

La interfaz muestra3perfiles educativos ficticios persistidos con un modelo local de ejemplo que bloquea IO. Se conservaron8contactos,8conversaciones,26mensajes,8notas,8tareas y3comentarios. La prueba de navegador recuperó el agente de programa y lo dejó pausado para revisión. No se introdujeron respuestas generadas ficticias en las conversaciones.

## Continuidad y reversión

La receta vigente es `docker compose -p crm-cbn-current-p5 -f compose.agents.yaml up -d --pull never`. El acceso privado está en `.local/p5-es/ACCESS.txt`, con las mismas credenciales humanas. No ejecutar preparadores ni seeds al iniciar o retomar. Un cambio de versión usa la restauración auditada en pausa. Para volver al checkpoint P4, pausar entrada/salida, conservar base/solicitudes/cola/volumen P5 y arrancar el contenedor P4 conservado en4178; nunca copiar datos posteriores sobre P4 ni reenviar efectos inciertos.

El replay offline de1225preimágenes reproduce P4→preview demo→P3→P2→P1 sin editar verificadores. El primer replay P5 agotó el tmpfs de512MiB del helper; se retiró únicamente su copia temporal fallida y el replay completo se trasladó a un directorio privado persistente. No se modificaron archivos fuente anteriores para resolverlo.

P5=100% local; P4 permanece82,29% por dominio/apps/cuentas reales pendientes. P6 y las demás fases conservan su avance parcial. El cierre local de P5 no equivale a validar datos académicos completos o producción institucional externa.
