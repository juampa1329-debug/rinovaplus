# SQL-C13 · Preview general y sprint Docker P1.4

El preview independiente se ofrece en [127.0.0.1:4176](http://127.0.0.1:4176/). Usa `CBN_C13_TRIAL_20261025_1f10a824`, restaurada desde un respaldo COPY_ONLY/CHECKSUM de C12, con VERIFYONLY, CHECKDB y comparación exacta antes de crear el login propio. SIIE, C5, C9, C11 y C12 se conservan. Las 50 tablas y 44.180 filas académicas de la copia permanecen intactas; el diario conserva sus 17 filas.

## Alcance visible

La navegación muestra 14 secciones y el avance general. Resumen, CRM, Inbox, mini CRM y Ajustes CRM reutilizan los componentes y repositorios aceptados, con un workspace C13 que valida su propio destino. Canales muestra lecturas seguras de las cuentas migradas, estados y etapa B006. Las otras secciones muestran su avance y lo que falta integrar; no se montan los productos pendientes ni se presentan como operativos.

El estilo Glass y los archivos C5/C9 se conservan. Un HTML, configuración de build y entrada React nuevos crean esta composición; las fuentes del App y de los manifests antiguos no se alteran. El núcleo CRM permanece montado al visitar otras secciones para conservar los borradores. La nueva versión de capacidades se valida antes de montar la interfaz; un manifiesto ajeno o malformado no cae en modo legacy.

La API tiene un perfil SQL cifrado y principal propios, TLS obligatorio, SID/identidad/catálogo completo/propietarios/ACL/contexto/diario fijados y validación antes de cada transacción. Los permisos de escritura se limitan a los contratos locales CRM y operaciones nuevas. Los secretos/cuerpos sólo permiten proyecciones por columna. No hay DML académico, creación de tablas, migraciones o fallback al arrancar.

Una sesión de propietario local usa cookie HttpOnly/SameSite=Strict, Host y Origin permitidos y cabecera local. Se rechazan acceso remoto, ausencia de sesión y bootstrap desde otro origen. Es un control de ensayo local; usuarios, roles y revocación institucional pertenecen a P2.

## Sprint P1.4

La imagen autónoma `crm-cbn-general:c13` se construye con Python y Node oficiales fijados por digest, ODBC18 fijado y locks de Python/npm. Tiene un Dockerfile y contexto de exclusión propios. Se ensayó también un build sin caché, sin depender de la imagen de desarrollo local. Incluye app, herramientas, releases y documentos requeridos por los loaders; no depende de binds de código ni de HMR.

La composición se ejecuta como usuario10001, raíz de archivos de sólo lectura, capacidades Linux retiradas y no-new-privileges. Publica únicamente loopback4176. Los perfiles y la CA se montan en lectura; el estado IA y `inbox-media` usan volúmenes C13 propios. Los archivos sintéticos y los hashes de perfil/clave/ticket sobreviven a reinicio y recreación. El arranque usa `--no-proxy-headers`; X-Forwarded-* no cambia el peer validado.

El worker durable de ensayo sólo selecciona una acción y actor locales fijos. No acepta URL, transporte, herramienta arbitraria o trabajo de proveedor. Confirma claim/lease antes del efecto; cerca la confirmación con LeaseId, LeaseVersion y vencimiento. El efecto es un marcador local O_EXCL con fsync. SIGKILL antes y después del efecto, reinicio, vencimiento y reconciliación muestran una sola aplicación; evidencia discrepante queda uncertain y no vuelve a seleccionarse. Los contenedores de fallo se conservan detenidos. No se certifican entregas externas, workers educativos/campañas o fallos eléctricos.

El healthcheck comprueba la identidad y el contrato SQL, separado de `/health/live`. Los proveedores y workers heredados no se montan por elegir un modo legacy. La imagen anterior se conserva y se comprueba su compatibilidad con el perfil/datos actuales antes del cierre.

## Validación

| Ensayo | Resultado |
|---|---|
| Backend nuevo | 23 pruebas C13 |
| Backend focalizado total | 265 aprobadas, incluidas242 regresiones |
| Frontend nuevo | 11 pruebas C13 |
| Frontend focalizado total | 52 aprobadas, incluidas41 regresiones |
| HTTP sobre el preview real | 25 comprobaciones: CRUD local, replay, conflicto, mensaje local y bloqueos |
| SQL real | 15 comprobaciones: permisos, drift y preservación de cinco fuentes |
| Docker y recuperación durable | 16 comprobaciones, sin efectos externos |
| Historia | 93 transiciones inválidas rechazadas; prefijos y releases anteriores preservados |
| Estática | AST, Ruff E/F/I, ESLint y TypeScript; build de imagen y frontend aprobados |

La suite general del repositorio no se recertifica. El aviso de bundle superior a500kB permanece visible. La inspección en navegador comprueba navegación compacta, CRM, Inbox, Ajustes, Canales y pendientes; las capturas y el detalle final se entregan en `artifacts/sql-c13/`.

[HTTP](../../../artifacts/sql-c13/http-checks.json) · [SQL](../../../artifacts/sql-c13/sql-audit.json) · [Docker/worker](../../../artifacts/sql-c13/runtime-drill.json) · [Checks offline](../../../artifacts/sql-c13/offline-checks.json) · [Progreso de la unidad](../../../tasks/sql-c13-progress.json).

## Porcentajes y siguiente fase

El propietario precisó que, si el fragmento académico es insuficiente, se cierre el sprint más cercano y se continúe con P2. Se acepta P1.4 al completar sus evidencias técnicas: P1 pasa de3/5 (60%) a4/5 (80%). El sprint C13/P1.4 queda completo; P1.close conserva crédito0. No se cambian los textos, denominadores o pesos de los56 criterios para obtener100%.

P1.close necesita un ensayo de contratos/migraciones y restauración sobre motor SQL2019 real. El motor de esta copia sigue siendo SQL2022 Express/160. Se descargó la imagen oficial2019 para preparación, pero no se inició un servidor2019 ni se restauró un backup2022 sobre él. La aprobación de operación institucional sigue siendo P11, distinta del ensayo técnico de P1.

Los [22 enlaces académicos preparados](academic-bindings-c13.json) son un inventario de candidatos y validaciones, no aliases activos. El propietario confirmará tablas y campos; no se renombrarán objetos SIIE ni se crearán sustitutos ficticios. Véase [contrato de enlace](SQL_C13_BINDINGS.md).

Siguiente sprint: **P2.1**, contrato de ajustes, identidad y permisos institucionales sobre otra copia de ensayo. Esta autorización permite avanzar el subconjunto local sin declarar P1.close o P11 completos. No habilita proveedores, secretos operativos, DDL académico o producción.
