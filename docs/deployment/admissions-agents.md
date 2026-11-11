# Operación local de agentes de admisiones

## Sustitución local del orientador por Bety — aplicada, 2026-10-21

Por solicitud posterior del propietario, el coordinador ejecutó preflight y aplicación de `backend/tools/switch_bety_primary.py` sobre tres perfiles existentes, revisiones esperadas 3/2/1. Ambos exit 0, mismo identificador de operación. Bety quedó activa v3/r4; anterior archivado v2/r3; programa 331 activo v2/r2 con Bety como padre. Configuraciones del anterior y del programa, objetivos/reglas de Bety y resto de instrucciones conservados. No se modifica el índice único, no se añade un endpoint de sustitución y el cambio normal de ámbito sigue restringido.

La herramienta es un mantenimiento específico ya aplicado, no un procedimiento general para restaurar perfiles ni una migración automática. Exige IDs, estados, versiones, revisiones y dependencias exactos; preflight de grafo propuesto, bloqueo transaccional, historial/idempotencia/invalidate y comprobación final. No contiene bindings SQL nulos ni DDL. Una desviación aborta; no usar otro identificador para intentar eludir una revisión cambiada. El rollback de una transacción fallida conserva íntegramente el estado anterior; no borrar perfiles o historial como reversión.

La aceptación posterior desde Asistente confirmó dos respuestas Gemini y una conexión SQL nueva confirmó Usage/Execution completados de 4.691/4.803 tokens. Core 3/3/8/0 y Profile=3 conservados, auditoría activa/huella idéntica. Esto habilita el perfil en el CRM local; no constituye despliegue de producción ni activación de transporte o política automática global.

## Liquidación aceptada en el runtime local, 2026-10-21

El coordinador comprobó creación y recarga de dos perfiles reales, respuesta manual Gemini del programa 331 y liquidación posterior desde una conexión nueva: Execution completada, Usage completado de 4.650 tokens; sin envíos ni alteración de ajustes globales o perfil archivado. Conteos finales Contact/Conversation/Message/outbound/Profile/Usage/Execution: 3/3/8/0/3/6/6. Se conservan auditoría y reservas históricas desconocidas.

La operación comparativa real del UPDATE de Execution cambió el identificador de transacción con bindings Python nulos y lo conservó al usar NULL literal sin bindings nulos. Drenado y `setinputsizes` por sí solos no corrigieron el problema. La implementación actual usa una lista fija de columnas, parametriza valores presentes, conserva proveedor/modelo ausentes y asigna NULL literal a ausencias permitidas; Usage sigue el mismo criterio. Drena resultados y comprueba coherencia antes de confirmar. Esta evidencia no demuestra una causa interna específica de ODBC/SQL Server. No restaurar el UPDATE anterior ni borrar reservas para ocultar fallos. Una discrepancia devuelve un error de liquidación y mantiene el intento sin anunciar éxito.

Las dos reconciliaciones puntuales del coordinador usaron exclusivamente tokens ya demostrados por Execution; los intentos sin evidencia permanecen inciertos. No ejecutar reparaciones generales ni inferir consumo cero. [Cierre y límites](../contracts/admissions-agents.md#corte-vigente--guardar-y-utilizar-2026-10-21).

## Expansión vigente de ejecuciones — 020 aplicada, 2026-10-21

El coordinador aplicó explícitamente `020_agent_execution.sql` en la misma copia local, mediante `tools.migrate_agent_execution`, con resultado exit 0. La lectura posterior en conexión nueva verificó destino, 21 columnas, dos índices y tres relaciones CRM; cero ejecuciones iniciales y conteos Contact/Conversation/Message/outbound/Profile/Usage conservados en 3/3/8/0/1/0. El trigger de auditoría DDL permaneció activo y con la misma huella. Esta operación no restauró ni activó el perfil histórico y no cambió conexiones o transporte.

El runner exige `local_sql_copy`, TLS existente, `verify_target` y el bloqueo transaccional compartido antes de comprobar/aplicar. `--preflight` revierte su transacción y no crea objetos. Si el contrato ya existe, verifica columnas/tipos/tamaños/nullabilidad, precisión decimal, relaciones e índices y devuelve sin cambios; un drift se rechaza. No hay creación automática de esquema desde el proceso web.

```powershell
# En backend, usando el entorno autorizado existente:
python -m tools.migrate_agent_execution --preflight
```

En Docker debe conservarse `SSL_CERT_FILE=/tmp/crm-ca-bundle.pem`, el bundle público usado por el runtime. No desactivar TLS ni incorporar credenciales a los comandos. La expansión ya está aplicada; no repetir DDL manualmente ni editar 019 para incorporarla.

Reversión no destructiva: pausar los agentes afectados y detener su consumo mediante las políticas existentes, conservar Execution/Usage/History y volver a una versión de aplicación que tolere la expansión. No eliminar la tabla ni restaurar una base sobre registros posteriores. Una transacción fallida del runner revierte íntegramente sus cambios; no requiere limpiar auditorías ni desactivar el trigger.

La disponibilidad de perfil es directa al guardar una configuración válida; no ejecutar aprobaciones de perfil como paso de despliegue. Las condiciones de fuentes/etapas, la política global y el control humano conservan su contrato. [Guía operativa completa](../guides/agentes-ia.md), [contrato vigente](../contracts/admissions-agents.md#corte-vigente--guardar-y-utilizar-2026-10-21).

## Preparación y aplicación explícita

Usar exclusivamente el mismo proyecto y la copia local autorizada. La migración aditiva `019_admissions_agents.sql` crea siete tablas de `crm_agents`, sin datos de negocio ni DDL core. El runner reutiliza TLS estricto, `verify_target`, conexión ODBC existente y transacción del llamador. No se ejecuta al iniciar ni desde una petición.

Desde `E:\Nuevos_Proyectos\CRM_CBN\backend`, con el entorno local existente:

```powershell
.\.venv\Scripts\python.exe -m tools.migrate_agents --preflight
# Sólo tras revisar el destino, respaldo/restauración y alcance local:
.\.venv\Scripts\python.exe -m tools.migrate_agents
```

En el runtime Docker vigente debe conservarse el bundle TLS y entorno ya utilizado por los runners anteriores. No copiar claves al comando ni desactivar validación. Preflight revierte su transacción. Una ejecución repetida comprueba contrato y columnas mínimas y no cambia datos; un esquema desconocido se rechaza. La comprobación mínima no sustituye una auditoría completa de drift.

## Configuración humana

1. Abrir `http://127.0.0.1:4173/#/agents`. Sin migración aparece estado pendiente; después, colección vacía real.
2. Crear orientador con supervisor opcional, configurar instrucciones/canales/capacidades y elegir proveedor de IA. Seleccionar sus modelos conocidos y presupuesto propio; guardar borrador. Las opciones provienen de la caché o configuración existente. «Actualizar opciones guardadas» sólo lee metadatos locales; para otros modelos, consultar el catálogo explícitamente desde Ajustes → APIs. Revisar la configuración efectiva, aprobar esa versión y activar únicamente si corresponde. Activar un perfil no activa la política automática del Inbox.
3. Elegir programas de la oferta real usando los filtros combinados de escuela y jornada. La selección se conserva si permanece válida. Crear y aprobar etapas propias con condiciones y evidencia. Crear perfiles de programa y etapa con sus supervisores obligatorios; revisar antes de activar. No completar con datos de ejemplo ni asumir que el proceso es lineal.
4. Publicar fuentes en Conocimiento. Aprobar alcance, versión, responsable y vigencia en Agentes → Fuentes; seleccionar las fuentes necesarias por perfil. Los hijos heredan las institucionales y sus límites.
5. En Inbox → responsables, confirmar contexto, programa y postulación exactos, si existe. Confirmar su etapa con evidencia. Seleccionar ese contexto y atención automática, manual protegida o humana. Cada decisión tiene motivo y revisión esperada; otras postulaciones se conservan.
6. Utilizar Simulador con la versión guardada y canal explícitos. La vista previa no consume; generar requiere la casilla de consumo. Revisar Actividad y Supervisión. La prueba no valida exactitud académica ni habilita transporte.

## Validación por capas

Después de normalizar y congelar los archivos, ejecutar comprobaciones enfocadas con herramientas instaladas:

```powershell
# Desde backend, sin SQL real en fixtures:
.\.venv\Scripts\python.exe -m pytest tests/test_agents.py tests/test_inbox_operations.py tests/test_admissions.py -q
# Ampliación de proveedores y modelos, sin red ni SQL reales:
.\.venv\Scripts\python.exe -m pytest tests/test_agents.py tests/test_agent_providers.py -q
# Desde frontend:
.\node_modules\.bin\vitest.cmd run src/modules/agents/agents.test.tsx
.\node_modules\.bin\tsc.cmd --noEmit
```

Resultado registrado el 2026-10-21: `test_agents.py` ejecutado independientemente mediante el venv del host obtuvo **24 passed, 0,46 s, exit 0**. Ruff y formato de los seis nuevos Python pasaron; Impeccable revisó ocho objetivos sin hallazgos (`[]`). La migración 019 se aplicó a la copia local autorizada con exit 0. Navegador abrió catálogo real, colección vacía, constructor y todas sus secciones, con teclado/foco visible y móvil sin desbordamiento. Supervisión mostró cero solicitudes/tokens y ausencia de ejecuciones/uso del proveedor, sin errores. No se guardaron datos ficticios desde la UI ni se aprobaron/activaron perfiles.

El gate global continúa con fallos heredados: TypeScript en Settings/Inbox y mocks (`firstResponseDueAt`, `destinations`, `miniCrm`), sin diagnósticos en `modules/agents`; subconjunto backend 15 aprobadas/1 fallo del cursor `ExternalIdentity`; Vitest 3 aprobadas/12 fallos (once por proveedor `WorkspaceSession` ausente y uno por `destinations` en mock Inbox). No se corrigieron fuentes ajenas ni se declara gate global aprobado. Detalle y límites en el [contrato](../contracts/admissions-agents.md).

El smoke SQL real aprobó diez comprobaciones, exit 0: orientador borrador guardado/leído, replay, actualización a versión 2 y stale409; etapa de programa real guardada/leída, replay, revisión 2 y stale409. Se mantuvieron conteos de negocio dentro de la transacción y se ejecutó `ROLLBACK` en `finally`, con el mismo cursor/applock y `autocommit=False`. Conexión nueva más `verify_target` confirmó Agent/Profile/Stage/History **0/0/0/0**, Contact/Conversation/Message/outbox **2/2/8/0**. No hubo COMMIT, aprobación, activación, proveedor ni envío; los huecos IDENTITY por rollback no se reseedearon y no representan datos persistidos.

Esta evidencia cubre borradores y reversión; inferencia, ciclo completo de aprobación/asignación/entrega y workers SQL concurrentes requieren ejercicio propio. Mantener configuración IA y conteos anteriores. No aprobar, activar o enviar durante la aceptación vacía.

Ampliación posterior: GET local de proveedores confirmó Gemini configurado y su modelo guardado, sin llamada externa; GET local de agentes confirmó dimensiones reales de 127 programas, diez escuelas y tres jornadas. Proveedor/modelos se guardan en el JSON versionado de cada perfil, sin nueva migración. Pruebas focales: 33 backend y cuatro frontend aprobadas; Ruff/formato y ESLint focales aprobados. TypeScript global conserva únicamente los diagnósticos heredados descritos arriba, sin diagnósticos en `modules/agents`. La prueba de ejecución usa un gateway simulado; no se generó inferencia, no se copiaron credenciales ni se activaron envíos.

## Reversión

Primera opción: conservar tablas y pausar perfiles de abajo hacia arriba. Tomar atención humana en conversaciones adoptadas impide salidas automáticas; no eliminar contextos para recuperar el comportamiento legacy. La interfaz y fuentes pueden revertirse selectivamente usando el inventario de esta unidad; no usar reset/checkout sobre archivos con trabajo ajeno.

Una reversión de esquema requiere respaldo/restauración y autorización SQL específica. No se distribuye un DROP automático: eliminar `crm_agents` con conversaciones adoptadas suprimiría su frontera de protección y podría reactivar la lógica anterior. Restaurar la copia local es el límite de rollback de datos; los siete objetos no modifican tablas core. Conservar auditoría y reservas antes de cualquier retirada. No borrar cambios de otras unidades.

Antes de publicar: implementar y aceptar identidad/RBAC institucional, revisar fuentes y tratamiento de expedientes, probar permisos negativos y concurrencia SQL real, y autorizar por separado proveedor/canales/envíos. Estos pendientes no se presentan como capacidades aprobadas.
