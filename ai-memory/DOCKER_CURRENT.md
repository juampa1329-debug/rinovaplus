# Estado operativo de Docker · 7 de noviembre de 2026

La única aplicación activa de CRM CBN es [4178](http://127.0.0.1:4178/), con `crm-cbn-current-preview` (P11 R3) y `crm-cbn-p2-sql2019`. Ambos usan `unless-stopped`. Se retiraron 42 contenedores anteriores después de proteger sus configuraciones y los archivos únicos. Se conservaron sus volúmenes, bases, perfiles, respaldos y evidencias.

Ver [instalación local](../docs/adaptation/LOCAL_DOCKER.md) para arranque, topología y recetas bajo demanda de auxiliar y P10. Ese registro actualiza las referencias históricas a contenedores detenidos o auxiliares permanentes en el estado de P11.

Roadmap técnico general **93,62%**. La puesta online de P12 espera URL e infraestructura. El cierre de Docker no cambió los criterios de producto.

## Dominio para P12 · 9 de noviembre de 2026

El propietario informó `rinovaplus.com`. La propuesta de origen público único es `https://app.rinovaplus.com`, con interfaz, `/api/` y `/hooks/` en el mismo host. El propietario confirmó que todavía no tiene servidor. Crear el registro DNS cuando se confirme el destino público y el proxy. Ver [entrega DNS y contrato P12](../docs/adaptation/sql/P12_DNS_HANDOFF.md). P12 conserva 0% de ejecución online y el roadmap general 93,62%.

## Plataforma de P12

El propietario confirmó Coolify. [Contrato de publicación](../docs/adaptation/sql/P12_DNS_HANDOFF.md#publicación-en-coolify). El origen público sigue siendo un ajuste SQL en el código de P11. P12 debe cablear y validar `CRM_PUBLIC_BASE_URL` en su perfil público. Se documentó el contrato, con el código y la publicación aún pendientes.

## Repositorio Rinova Plus · 11 de noviembre de 2026

El propietario indicó GitHub como origen para la publicación de Rinova Plus. La rama main del repositorio privado reúne el código y la documentación de CRM CBN. La puesta en servicio P12 se prepara para Coolify.

[Repositorio Rinova Plus](https://github.com/juampa1329-debug/rinovaplus)

## Conexión SQL para Coolify · 13 de noviembre de 2026

La rama `deploy/coolify-rinovaplus` usa `docker/Dockerfile.coolify` en 4178 y admite SQL Server 2019 mediante `CRM_SQL_URL`, `CRM_SQL_USER` y `CRM_SQL_PASSWORD` de ejecución. Por solicitud del propietario, el modo usa `Encrypt=Yes;TrustServerCertificate=Yes` para conectar por IP sin validar el certificado de SQL Server. La aplicación requiere `CRM_SECURITY_KEY` persistente. `CRM_PUBLIC_BASE_URL` configura el origen y las URLs públicas. El ensayo firmado sigue disponible sin las tres variables SQL y conserva su validación del certificado.

La imagen se probó en una restauración separada con TLS y privilegios acotados. El catálogo del destino y los permisos se verifican antes de arrancar. `python -m app.institutional.deployment` es el diagnóstico de solo lectura para `dbsiie` desde Coolify. El [runbook](../docs/deployment/coolify.md) incluye las salidas SQL separadas para inventario y revisión de permisos.

Roadmap técnico **93,62%** y P12 **0,00% de ejecución online**. El modo SQL quedó probado localmente. Quedan la comprobación de solo lectura desde Coolify y la aceptación institucional.

## Inicio de la migración PostgreSQL · 14 de noviembre de 2026

Coolify muestra el backend de RinovaPlus en la revisión `8a84f9876e5f`, conectado a `DBSIIE_2025A` en SQL Server 2019. La rama local `migration/rinovaplus-postgresql` parte de esa revisión. La copia de solo lectura retuvo 48 filas de 119 tablas CRM y el esquema de 155. Las otras 36 tablas tienen permisos incompletos y cero filas estimadas por el catálogo. Se dejó el archivo privado en Oracle y se conciliaron las 48 filas en `rinova_migration` de la base PostgreSQL 16 `rinovaplus`. SIIE sigue en SQL Server y el CRM activo sigue en su origen.

El mismo destino PostgreSQL tiene `rinovaplus_crm`, con 155 tablas tipadas, 298 claves foráneas y las 48 filas conciliadas. Se instalaron consultas de contactos y mensajes, conteos y selección de cuatro colas. El ensayo SQL revirtió las filas sintéticas y verificó que los envíos con concesión vencida quedaran inciertos. El backend activo sigue en SQL Server y SIIE permanece allí.

El perfil nuevo arranca solamente con `rinovaplus_rehearsal` y verifica rol, catálogo, contexto y huella de la instantánea. En PostgreSQL 16 local, con datos sintéticos, pasaron autenticación, permisos, CSRF y el flujo de un mensaje firmado desde el webhook hasta CRM e Inbox, incluido el almacenamiento de un adjunto de prueba. El proveedor simulado comprueba respuesta idempotente, entrega y estado incierto sin reenvío. Cinco de ocho etapas de workers están integradas (62,50 % de las etapas). Producción y SIIE siguen en SQL Server.

El DBA otorgó el rol temporal de lectura a `WebCRM`. A las 22:11:44 del 14 de noviembre (Bogotá) una nueva conexión desde Coolify verificó la identidad `WebCRM` y obtuvo 36 conteos exactos en `DBSIIE_2025A`. Las 36 estaban vacías para ese usuario. Los mismos conteos en la copia de Oracle también dieron cero. La copia conserva 155 tablas tipadas, 48 filas en el esquema intermedio y la huella del archivo inicial. La comprobación solo leyó ambos motores. El DBA puede retirar el rol con el mismo script.

En Oracle ARM64, la prueba restauró el esquema PostgreSQL 16.16 en una red interna con contenedores desechables. Verificó cinco etapas de Canales con datos sintéticos y el arranque real de Coolify (Nginx, Uvicorn y disponibilidad), además de inicio/cierre de sesión y persistencia del contacto. El recorrido tomó 23 segundos. Una segunda base dentro del entorno aislado restauró los dos esquemas del CRM y confirmó 155 tablas, 298 FK, 48 filas, cero diferencias de conteo y expiración de envíos sin reencolado. El origen PostgreSQL se leyó únicamente y se comprobó el recibo y la identidad de los contenedores activos al terminar. Se retiraron los recursos temporales de Docker. Pasaron 133 pruebas dirigidas en local.

El segundo ensayo en Oracle calificó 8/8 etapas con proveedores simulados. Verificó las lecturas de módulos, la descarga del adjunto recibido, el recibo tardío de masivos, el bloqueo por campaña pausada, el vencimiento de la solicitud de agente, el arranque de Coolify y la restauración de 155 tablas, 298 FK y 48 filas con cero diferencias. Tardó 33 segundos. En local pasaron 139 pruebas dirigidas y el arranque del perfil de prueba con autenticación SCRAM usando `CRM_POSTGRES_USER` y `CRM_POSTGRES_PASSWORD`. Oracle conserva una cuenta propietaria activa con hash PBKDF2.

Una tercera restauración aislada en Oracle verificó cinco recorridos de escritura con datos sintéticos: ajustes, contactos, guardado y simulación de agentes, masivos y campañas. Pasaron 8/8 etapas y el arranque de Coolify. Recorrido de 37 segundos, con 155 tablas, 298 FK y 48 filas conciliadas al restaurar. El cargador atómico para la sincronización final de CRM se probó en PostgreSQL local contra una base vacía y rechazó una segunda carga.

El rol `rinovaplus_app` existe con LOGIN y SCRAM. El backend alcanza el host privado de PostgreSQL por TCP. Coolify tiene guardadas la URL, el usuario, la contraseña literal y la huella de la candidata. Se capturaron 155 tablas y 48 filas del CRM sobre SQL Server 2019 en solo lectura. La candidata en Oracle quedó cargada y conciliada en `rinovaplus_rehearsal`. La revisión preparada con `CRM_DATABASE_ENGINE=postgresql` y origen HTTPS arrancó en Docker local sobre `rinovaplus`. El corte requiere una nueva captura con las escrituras CRM pausadas.

## Corte de RinovaPlus a PostgreSQL · 15 de noviembre de 2026 (UTC)

Coolify marcó exitoso el despliegue `c4e87fd` con `CRM_DATABASE_ENGINE=postgresql`, PostgreSQL 16 y base `rinovaplus`. `/health/ready` devolvió `postgres_deployment`, el estado público de autenticación devolvió HTTP 200 y el endpoint de sesión devolvió 401 anónimo. La ruta `/var/lib/crm-ai` tiene volumen escribible. SIIE sigue en SQL Server. La captura final con escrituras CRM pausadas coincidió en las 155 huellas de tabla y 48 filas. Se conservan `rinovaplus_pre_cutover` y los respaldos privados en `/var/lib/rinovaplus-migration/2026-11-15`. En la restauración del respaldo productivo se conciliaron 154 conteos y se encontró una fila de auditoría posterior al corte. Conciliar las escrituras antes de una eventual reversión a SQL Server.

**Migración 6/8 hitos completos (75,00 %), dos parciales. Roadmap general 93,62 %. P12 3/6 (50,00 %).** Lectura 155/155 tablas y workers 8/8 probados. Quedan escrituras de otros módulos, adjuntos salientes, rendimiento comparativo y aceptación externa. [Procedimiento, grafo y evidencia](../docs/deployment/postgresql-migration.md)
