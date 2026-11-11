# Configurar el runtime SQL de la copia local

## Paquete de mantenimiento SQL-C3

El [release nuevo](../backend/migrations/cbn_foundation/release.json) se ensayó sólo en restauraciones de HORARIOSSIIE. No cambia el selector ni las variables del producto. [Informe y destinos](adaptation/sql/SQL_C3_REVIEW.md), [contrato/privilegios](decisions/ADR-015-foundation-restored-rehearsal.md). Markers nuevos; no usar el modo local_sql_copy para eludir guardas antiguas.

`python backend/tools/foundation_graph.py --check` valida bytes/forma/huellas **offline**. El harness `python -m tools.rehearse_foundation {prepare,reference,rehearse} --work <directorio_privado>` ejecuta mantenimiento real sólo con perfil privado/ticket y paths de ensayo; no usarlo como healthcheck ni arrancarlo desde la app. La preparación administrativa de usuario/schema es distinta de las tres transacciones. Mantener backup, estado, auditorías y versiones retiradas privados; ningún secreto está en el paquete público.

## Selector local de conexión — SQL-C1

Abrir [Ajustes → Base de datos](http://127.0.0.1:4173/#/settings). Se usa servidor TCP/puerto, usuario/contraseña SQL y nombre del certificado TLS. «Listar bases» muestra las bases accesibles; seleccionar, probar, guardar y «Ver estructura». La contraseña guardada no vuelve al navegador; dejarla vacía reutiliza la existente para idéntico servidor/puerto/usuario/TLS. Otro destino requiere su acceso y certificado público confiable, no desactivar TLS.

Perfil AES-GCM en volumen privado `/var/lib/crm-ai/database`: respaldar `profile.enc` y `profile.key` juntos con acceso restringido. Perder la clave impide recuperar el secreto; no borrar el volumen para actualizar imagen. Una única selección; no conexión institucional remota ni autenticación Windows integrada desde el formulario. Endpoints locales `/api/local/database`, `/discover`, `/test`, `/schema`; requieren guard local y `X-CRM-Local: 1`.

**Alcance:** inspección de catálogos, sin SQL libre/filas de negocio ni DDL/DML; no cambia conexiones CRM activas. HORARIOSSIIE actual es fragmento; preview local_demo/outboundfalse. No editar variables del guard de negocio para forzar su activación. Ver [contrato/recuperación](decisions/ADR-014-database-selection.md) y [verificación actual](adaptation/sql/SQL_C1_REVIEW.md).

## Contrato vigente P1.2 — 2026-10-24

La selección de destino usa ahora `CRM_SQL_ENVIRONMENT=local_copy|institutional`, independiente del modo operativo. El [contrato completo P1.2](adaptation/sql/P1_2_CONTRACT.md) exige identidad explícita, motor SQL Server 2019, compatibilidad 130/140/150 y TLS estricto antes de negocio. Conserva permisos mínimos de catálogo y marker/forma CRM. El workspace institucional está bloqueado en esta etapa; completar variables no habilita workers ni escrituras. Se comprobó únicamente con transportes ficticios, sin conectar ni modificar una base. La receta y aceptaciones históricas locales que siguen no acreditan operación institucional.

La aplicación carga el archivo privado `.env` de la raíz antes de crear FastAPI; la plantilla no incluye credenciales. El modo autorizado `local_sql_copy` ya persiste Clientes/Inbox en las cuatro tablas aisladas `crm` de DBSIIE y lee los cuatro catálogos reales. TLS, persistencia tras reinicio y UI sin semillas comprobados. Completar claves Meta no habilita adaptadores ni envíos. [Resultados y límites actuales](reports/crm-local-runtime.md).

## Activación local autorizada

`CRM_APP_MODE=local_sql_copy` exige host TCP local, puerto, usuario/contraseña, `CRM_SQL_EXPECTED_MACHINE` y `CRM_SQL_CERTIFICATE_HOSTNAME=localhost`. Se verifican DBSIIE, instancia SQLEXPRESS, máquina y huella del contrato ADR-006-v1 antes de operar. No se crea esquema al iniciar. El login SA está limitado al alcance expresamente autorizado sobre la copia local; el modo `local_readonly_catalog` mantiene su validación original y no acepta SA.

Docker usa `compose.yaml` junto con `compose.local-sql.yaml` en el proyecto existente `crm-cbn-integration-20261014`, servicio `preview`. El overlay fija `CRM_SQL_HOST=host.docker.internal` y monta exclusivamente el PEM público indicado por `CRM_SQL_PUBLIC_CERT_FILE`, en lectura, como `/run/crm-sql/public.pem`. `CRM_SQL_CA_FILE` señala ese archivo. El arranque combina las CA públicas del sistema y ese PEM en `/tmp/crm-ca-bundle.pem`, con modo 0600, y usa `SSL_CERT_FILE`; conserva `Encrypt=Yes;TrustServerCertificate=No` y la validación del nombre. No modifica el almacén global ni incluye certificados privados.

El preview sigue en `http://127.0.0.1:4173`, UID 10001 y un único backend. Se conserva el volumen `crm-cbn-integration-20261014_ai-state`; no usar `down -v`. `CRM_AI_OUTBOUND_ENABLED=false` evita llamadas a proveedores durante esta aceptación. Las claves existentes permanecen privadas y no se imprimen con `inspect` o `compose config`. La reconstrucción final por copy completó correctamente; resultado e identidad de la imagen en `.local/sql-crm-runtime-20261015/docker-final-copy.json`.

## Archivo y precedencia

1. Editar `.env` en la raíz, usando [`.env.example`](../.env.example) como referencia. No copiar secretos al chat, Git, capturas ni variables `VITE_*`. El archivo ya está excluido de Git y del contexto Docker; no se monta en el contenedor.
2. Completar únicamente las credenciales que correspondan. El contrato local SQL ya fue aceptado; no extender ese modo a otra base o entorno. Las pruebas de proveedor conservan su autorización separada.
3. Al iniciar un nuevo proceso, FastAPI resuelve la misma ruta desde la raíz o desde `backend`. No busca `.env` en directorios vecinos ni otros worktrees. El proceso ya iniciado no se recarga al editar el archivo.

El entorno del proceso tiene precedencia sobre `.env`, incluso si una variable existe vacía. El loader usa `python-dotenv==1.2.1`, `override=False`, `interpolate=False` y UTF-8 con BOM opcional; no ejecuta comandos ni expande referencias contenidas en los valores. Si el archivo falta, se conserva la configuración por entorno y los defaults existentes. Un error de lectura se comunica sin mostrar el contenido.

En Windows, las claves y la activación guardadas mediante **Ajustes > APIs** en DPAPI conservan su precedencia sobre el entorno. La respuesta de conexión ya informa `credential_source` (`local`, `environment` o `none`) y el estado configurado, nunca el valor. No se elimina ni modifica el vault para aplicar este cambio. En Linux, las claves proceden del entorno; no se añade edición DPAPI.

## Sintaxis compartida con Compose

Usar comillas simples alrededor de valores que contengan `$`, `${NAME}`, `#`, espacios o comillas dobles. La prueba utilizó únicamente un valor sintético:

```dotenv
CRM_SQL_PASSWORD='literal$ ${NAME} # spaced "double"'
```

Python y Compose conservaron exactamente ese texto, sin expansión. Los apóstrofes escapados dentro de comillas simples no resultaron equivalentes entre ambos lectores; no transformar el secreto para compensarlo. En ese caso, proporcionar el valor mediante el entorno del proceso/runtime o, para proveedores IA en Windows, Ajustes. No ejecutar `docker compose config` ni `config --environment` sobre credenciales reales para compartir su salida: ambos pueden mostrarlas.

Compose conserva una lista explícita de variables y valores seguros por defecto; no transmite indiscriminadamente el archivo. Las rutas de estado del host no se trasladan: el contenedor conserva `/var/lib/crm-ai` y su volumen actual. El archivo `.env` no se monta ni se incorpora a la imagen.

## Qué configura cada sección

| Sección | Comportamiento y límite |
|---|---|
| SQL Server | `CRM_SQL_HOST`/`CRM_SQL_PORT` seleccionan TCP y requieren usuario/contraseña juntos. `CRM_SQL_SERVER` y `CRM_SQL_DATABASE` comprueban el destino fijo. El modo local autorizado añade máquina, contrato y nombre TLS; el lector restringido conserva principal y token propios. No hay credenciales SQL en el navegador. |
| Texto | `GEMINI_API_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`. Provider/modelo, habilitación y outbound se eligen separadamente; llenar una clave no ejecuta una solicitud. |
| Voz | `ELEVENLABS_API_KEY`, `GOOGLE_TTS_API_KEY`. Voz/modelo y habilitación se configuran aparte. Piper no tiene clave API: utiliza runtime `piper/.venv` y modelos `piper/voices` bajo `CRM_AI_STATE_DIR`; no se instalan con esta unidad. |
| Búsqueda | `TAVILY_API_KEY`, `BRAVE_SEARCH_API_KEY`, `SERPAPI_API_KEY`; opcionales para las funciones correspondientes. |
| Meta reservado | `META_*`, `WHATSAPP_*` e `INSTAGRAM_*` son espacios de configuración pendientes. No tienen adaptadores/lectores operativos ni se inyectan por Compose. No registran cuentas, procesan webhooks ni envían mensajes. |

Los contratos implementados cubren cuatro catálogos de lectura y Clientes/Inbox mediante `/api/local/crm`. [ADR-006](decisions/ADR-006-local-crm-persistence.md) fue aceptado y aplicado tras respaldo/restauración comprobados. Las credenciales no ejecutan DDL ni autorizan escrituras core. Meta necesita un adaptador y alcance propios; no se abren túneles en esta unidad.

## Historial: diagnóstico previo a la implementación — 2026-10-15

Los párrafos siguientes conservan el estado del diagnóstico original. La confianza TLS de producto y la persistencia se implementaron y comprobaron después, como se describe al inicio; sus pendientes históricos no son el estado actual.

Por autorización expresa, el harness conectó con `sa` desde Windows y Docker a `DBSIIE`, instancia SQLEXPRESS; identificó el listener local antes de las lecturas. TLS permaneció en `Encrypt=Yes;TrustServerCertificate=No`. Los dos clientes leyeron las columnas de los cuatro catálogos y los mismos conteos: 32/12/2/228. INSERT en `#CRM_ConnectionProbe` y ROLLBACK retiraron la tabla temporal y dejaron `@@TRANCOUNT=0`. No se encontraron esquemas `CRM`/`CRM_*` ni objetos `CRM_*`; no se crearon objetos persistentes ni se escribieron datos core.

Docker sin confianza adicional rechazó el certificado (`08001`); con el PEM público del certificado vinculado al servidor, `SSL_CERT_FILE` temporal y `HostnameInCertificate=localhost`, el login pasó. No se cambió el certificado, su binding, el almacén global ni el preview. **Esa configuración fue exclusiva del harness:** todavía falta integrarla y verificarla en el runtime del producto. El guard `verify_principal` continúa rechazando `sa`; el ADR propone un modo de copia local separado sin alterar el lector restringido. No intentar activar `local_readonly_catalog` con SA como si el diagnóstico hubiera cambiado ese contrato.

Evidencia saneada: `.local/sql-real-20261015/result.md`, resultados Windows/Docker, controles de preservación y certificado exclusivamente público. El contenedor de diagnóstico se eliminó; `.env` permaneció intacto, sin copiarse ni registrarse, las 131 fuentes no cambiaron y el preview conservó imagen, inicio, volumen, cero reinicios y salud. El diagnóstico no acredita persistencia, aceptación DDL, recuperación de respaldo, IAM o producción.

## Historial de preparación TCP anterior al diagnóstico

**TCP local autorizado y comprobado, 2026-10-15:** el propietario autorizó habilitar TCP/IP en 1433 y reiniciar SQLEXPRESS. Se conservó `ListenOnAllIPs=1`, se habilitó el protocolo y se fijó `IPAll.TcpPort=1433` con `TcpDynamicPorts` vacío. La instancia volvió a Running con nuevo PID y listener 1433; Launchpad volvió a su estado Running, mientras Agent y SQLBrowser permanecieron Stopped. Certificado, ForceEncryption y valores por IP quedaron idénticos. No se modificó firewall ni se ejecutó autenticación o consulta SQL.

En ese corte previo, el socket TCP funcionó desde Windows y desde el preview; se completaron HOST/PORT conservando las demás entradas privadas. El preview no se reinició ni recibió la configuración nueva. Esa evidencia inicial solo acreditaba transporte; el diagnóstico posterior de la sección anterior añade TLS, login y lectura. La validación de arranque sigue exigiendo contraseña cuando HOST está definido, incluso en modo desactivado.

Snapshot mínimo y evidencias en `.local/sql-tcp-1433-20261015/`, sin copia del `.env`. La reversión preparada `change-tcp.ps1 -Action Rollback`, ejecutada con privilegios administrativos cuando se decida revertir, restaura únicamente los tres valores TCP originales y reinicia la misma instancia conservando estados de dependientes. El procedimiento respeta la política IP existente según la [configuración oficial de puerto](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/configure-a-server-to-listen-on-a-specific-tcp-port?view=sql-server-ver17) y el [reinicio requerido al habilitar el protocolo](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/enable-or-disable-a-server-network-protocol?view=sql-server-ver17).

## Evidencia y reversión

Las pruebas de bootstrap usan archivos sintéticos y ejercitan `create_app`; la suite desactiva por entorno la carga del `.env` del operador antes de importar la aplicación. No hay detección de pytest en código de producto. Evidencia saneada, respaldo y manifiesto de fuente en `.local/env-configuration-20261015/`; la prueba Compose verifica solo configuración y no crea contenedores.

**57 pruebas enfocadas aprobadas en 4,97 s**: carga/bootstrap, configuración del contenedor, integración y credenciales existentes. `pip check`, Ruff formato/check y exportación canónica correctos. `compose-literal-proof.json` confirma igualdad de los valores sintéticos documentados. El primer intento de instalación falló por resolución DNS del sandbox; la instalación autorizada de la única dependencia fijada completó correctamente.

El build independiente `crm-cbn-env-check:local` completó en 14,12 s para Linux AMD64; **25/25 comprobaciones de empaquetado y runtime aprobadas** en `docker-verification.json`. La imagen incluye `python-dotenv 1.2.1` y arranca sin archivo privado: UI y health 200, readiness 503 esperado. El contenedor efímero se ejecutó sin red exterior, puertos publicados, credenciales ni montajes, como UID 10001, y se eliminó al terminar. No contiene `.env*` en las rutas de aplicación. El preview 4173 conservó contenedor, imagen, inicio y volumen. Fuente 131/131 y respaldo 275/275 intactos; `git diff --check` correcto. No se repitieron suites completas ni se probaron conexiones reales.

El respaldo previo conserva 275 archivos y los 27 cambios entregados de Clientes. Revertir únicamente los archivos de la unidad de configuración desde ese respaldo; no restaurar HEAD sobre el trabajo anterior ni eliminar ajustes IA. Aquella unidad no ejecutó SQL, proveedores, envíos, publicación ni despliegue. El diagnóstico posterior sí comprobó la conexión local descrita arriba; persistencia y retirada de datos/textos de demostración siguen pendientes del contrato propuesto.
