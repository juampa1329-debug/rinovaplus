# P2: administración institucional sobre el esquema español

P2 está aceptada al **100,00% en su alcance local SQL Server 2019**. La aplicación tiene perfil y principal propios, usuarios humanos, permisos, ajustes tipados, canales configurables y una interfaz independiente. La puesta en servicio institucional y las operaciones de proveedores mantienen sus fases posteriores.

La entrega utiliza `CBN_P2ES_TRIAL_20261026_13f95607`, con 138 tablas: las 99 de P1 y 39 adicionales. Hay 108 mapeos lógicos cerrados y 221 relaciones físicas. Los nombres académicos se conservan y el usuario SQL de la aplicación tiene DENY sobre las 30 tablas académicas del paquete. No se importaron registros académicos ni se modificó HORARIOSSIIE.

El release comprometido es `cbn_institutional_spanish_v1`, SHA256 `1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4`. Sus 14 entradas y las dos unidades son inmutables. La principal `CBN_P2ES_TRIAL_20261026_dc85a69e` confirmó las dos unidades y una repetición NOOP. Los perfiles de aplicación adoptan esa historia restaurada sin reescribirla ni fingir que las migraciones se ejecutaron de nuevo en cada destino.

## Funcionamiento aceptado

- Institución, perfil, IA, proveedores/modelos, canales, webhooks, disponibilidad, límites técnicos y configuración CRM conservan tipado, permisos, validación y persistencia. Los formularios conservan borradores ante errores y conflictos, advierten antes de descartarlos y aplican revisión/CAS.
- Models es la autoridad de selección; los modelos derivados de IA se actualizan atómicamente. Hay seis opciones de visión, IDs manuales que sobreviven sin catálogo externo y controles independientes de failover y estilo humano. Los valores decimales se aceptan en los controles HTML.
- Los 115 contextos de Canales están clasificados: 50 inputs de configuración, 13 contextos editables de secretos y sus controles delegados, además de salidas, readonly y transitorios restringidos. Los aliases de formularios/modal comparten credenciales por propietario. Un endpoint UUID reúne configuración, vínculos y secretos de webhook.
- Las cuentas humanas están separadas del empleado SIIE y del agente IA. Se verificaron sesiones opacas, CSRF, permisos por transacción, logout/revocación, cambio de rol/estado/contraseña, invitación/restablecimiento de un solo uso, TOTP, recuperación y protección del último propietario útil.
- Hay 30 acciones y 55 combinaciones instaladas de método/ruta documentadas en `p2-endpoint-permissions.json`. Usuarios, roles, sesiones y auditoría tienen interfaz propia. Se puede definir quién administra agentes, fuentes, campañas, publicidad y usuarios, sin abrir APIs de módulos aún pendientes.
- La disponibilidad institucional se aplica por API y se refleja en la navegación sin F5. Los límites locales de solicitudes y cantidad de cuentas funcionan. Los presupuestos diarios se conservan configurados para futuros consumidores de proveedor; no son planes ni cobros.

## Evidencia ejecutada

`artifacts/p2-es/acceptance-review.json` reúne la aceptación por criterio y las huellas de los resultados.

| Verificación | Resultado |
|---|---|
| Backend institucional y fronteras | 91 pruebas puras aprobadas; Python 3.12 Linux |
| Frontend, identidad de sesión y regresiones compartidas | 72 pruebas en 8 archivos; Node 24.20 Linux, sin red |
| SQL/HTTP inicial | 38 comprobaciones |
| Ciclo de acceso y roles | 13 comprobaciones compuestas, 22 DTOs válidos denegados y 24 casos GET rol/ruta |
| Canales SQL | 7 comprobaciones adicionales de edición, CAS/replay, credenciales/propietario y TikTok |
| Estado MFA de respuesta de login |Coincide con el factor SQL y con `/auth/me`, sin requerir recarga |
| Migraciones | 10 fallos controlados; reconciliación/reintento/NOOP; 5 negativos de datos; concurrencia COMMITTED/NOOP |
| Navegador de integración | 36 comprobaciones base y 16 instancias de workflows; incluye escritorio, móvil, temas, borradores, usuarios/roles y módulos |
| Preview final limpio |Comprobación adicional en la imagen desplegada, sin usuarios/canales ficticios |
| Conservación | 6 bases Windows y 56 copias SQL Server 2019 previas con huellas de catálogo/datos iguales |

Los 52 casos base/workflows incluyen dos guardados distintos de Módulos con la misma etiqueta de prueba; no equivalen a 115 pruebas independientes de campos. Las relaciones físicas del grafo proceden del modelo SQL compilado, no de inferir relaciones de negocio por nombres.

## Reinicio y reversión

El reinicio exclusivo de la aplicación conserva cuentas, roles, ajustes, historial, secretos, factores, sesiones, auditoría y diario. La sesión opaca anterior sigue siendo válida después del reinicio. Los previews 4173 y 4176 siguen activos; no se redirigieron ni reiniciaron las versiones anteriores.

Se respaldó una copia poblada con nueve cuentas y se restauró en `CBN_P2ES_RECOVERY_20261026_b803ab53`. COPY_ONLY/CHECKSUM, identidad/HEADER, VERIFYONLY, CHECKDB y comparación binaria de datos/esquema preceden la adopción. La restauración nace en RESTRICTED_USER; se ajustan ACL y credenciales antes de publicar MULTI_USER. El login SQL heredado pierde CONNECT sólo en la copia nueva. Se autenticaron todos los ciphertexts y se conservaron cuentas, roles, configuración e historial y el prefijo de auditoría.

Las cookies y desafíos antiguos se invalidan, los códigos de recuperación restaurados se retiran y el piso de TOTP se calcula con el reloj SQL, incluso con un reloj de proceso atrasado. MFA permanece activo y se aceptó un TOTP actual nuevo. La imagen anterior compatible `p2es-r2-ui-candidate` leyó las nueve cuentas/auditoría, escribió/restauró configuración y rechazó acceso anónimo y contraseña sola antes del factor. **Revertir la aplicación conserva el esquema y las cuentas; no ejecutar DROP ni migraciones inversas destructivas.**

El respaldo conserva el contenido de su checkpoint, no cambios posteriores de la fuente, que permanece separada. Este protocolo exige que la fuente esté disponible para su validación previa. La recuperación con fuente perdida y el procedimiento institucional fuera de banda cuando se perdió el autenticador quedan en P11; no se desactiva MFA automáticamente.

## Acceso y continuidad

Preview: `http://127.0.0.1:4177/`. La cuenta inicial sólo aparece en `.local/p2-es/ACCESS.txt`, accesible al usuario Windows actual y SYSTEM. Cambiar contraseña y configurar el autenticador desde Ajustes. No copiar credenciales al chat, al grafo ni a artefactos públicos.

El perfil final limpio conserva una cuenta propietaria y cero fixtures. Las copias con datos de prueba y sus perfiles permanecen separados. El contenedor final es rootless, con raíz y perfil/CA de sólo lectura, capacidades retiradas y publicación exclusiva en loopback. No tiene credenciales administrativas SQL ni el volumen privado de calificación montado.

Para verificar sin conectar SQL: `python -B backend/tools/check_p2_es_checkpoint.py --self-test`. El comprobador actual reproduce los archivos P1 originales en un directorio aislado; no se debilitó el checkpoint P1 para aceptar código P2. Se conservaron 872 preimágenes y cuatro fuentes adicionales que ya estaban fijadas por la huella independiente del registro P1. Los 56 criterios y 279 hitos mantienen su definición y pesos.

P4.3.m5 también queda completo en configuración UI, aportando exactamente 20/7 puntos a P4: pasa de 35,43% a 38,29%. OAuth, verificación de números/tokens, recepción pública, entrega, publicidad, workers, Inbox avanzado/churn y el resto de las fases posteriores no se aceptan con esta entrega.
