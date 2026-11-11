# ADR-014 — Selector local de SQL Server y lectura de estructura

Fecha: 2026-10-24. Estado: implementado y verificado para administración local de metadatos (SQL-C1). Complementa ADR-012/013; no declara aceptación institucional.

## Contexto

El propietario pidió seleccionar la base desde Ajustes e introducir credenciales. Aclaró que `HORARIOSSIIE` es sólo un fragmento de DBSIIE. La instancia local SQLEXPRESS responde con TLS validado, motor 16 (SQL Server 2022 Express) y compatibilidad 160. DBSIIE no está entre las bases visibles con el acceso actual. SQL Server 2019 sigue siendo el objetivo institucional.

## Decisión

Incorporar **Ajustes → Base de datos** conservando Glass y componentes existentes. Permite indicar servidor TCP/puerto, usuario/contraseña SQL y nombre del certificado; descubrir bases accesibles, elegir una, probar, guardar y consultar tablas/columnas/relaciones. Todos los comandos SQL de esta función son SELECT fijos de catálogos. No admite SQL libre ni consulta filas de negocio.

El perfil elegido se aplica a esta herramienta de inspección. No cambia conexiones CRM ya activas, ni habilita repositorios, workers, migraciones o proveedores. El preview queda en `local_demo`, con salida IA desactivada. El guard institucional P1.2 mantiene versión 15 y sus validaciones; el selector registra la versión observada sin fingir aceptación SQL 2019.

Se reutiliza el guard local: loopback, Host permitido, Origin validado, `X-CRM-Local: 1`, JSON y límite de cuerpo. No es autenticación institucional ni panel remoto. Cada conexión exige ODBC18, `Encrypt=Yes`, `TrustServerCertificate=No` y validación del hostname. Las entradas se validan y los delimitadores ODBC se escapan. Los errores públicos no reflejan credenciales ni mensajes SQL originales.

Se guarda una única selección cifrada con AES-GCM-256, nonce aleatorio y clave separada en el volumen privado existente, bajo `/var/lib/crm-ai/database`. Las respuestas omiten la contraseña y llevan `Cache-Control: no-store`. Contraseña vacía reutiliza un secreto existente sólo si coinciden servidor, puerto, usuario y hostname TLS. Cambiarlos borra la contraseña del formulario. No se usa localStorage para secretos.

Guardado atómico y revisión optimista evitan sobrescritura silenciosa dentro del único proceso backend configurado. La exclusión es por proceso: antes de añadir workers o réplicas debe incorporarse coordinación entre procesos. El cifrado protege el archivo aislado; un administrador con acceso al volumen y a su clave puede descifrarlo. Respaldar `profile.enc` y `profile.key` como pareja protegida. Si falta la clave o falla la autenticación/formato, el almacén falla cerrado y no la regenera sobre un perfil existente.

## Evidencia y consecuencias

Se verificaron descubrimiento, prueba, guardado, reutilización de contraseña, lectura de estructura, UI y persistencia tras recrear el contenedor. HORARIOSSIIE tiene 50 tablas, 437 columnas y 41 FK visibles con visibilidad de metadatos completa para este acceso. Eso no comprueba índices, defaults, CHECK, triggers, permisos, semillas ni drift final. La captura usa SELECT secuenciales, sin snapshot transaccional de esquema.

Faltan tablas académicas usadas por los mapeos y las cuatro tablas CRM base. No se fabrican tablas SIIE ni se clona el fragmento para llamarlo DBSIIE. La creación CRM local previamente autorizada queda para una copia correcta y restaurable, con análisis de drift y ensayo explícito. No se ejecutó DDL/DML ni migración en esta unidad.

Reversión: retirar el panel/endpoints y su integración, volver a la imagen anterior y conservar el volumen privado; no requiere revertir SQL. La configuración TLS del host tiene su script privado de reversión independiente, sin automatizarlo al retirar el panel. La selección guardada puede conservarse cifrada; nunca publicarla junto a su clave.

Evidencia: [SQL_C1_REVIEW.md](../adaptation/sql/SQL_C1_REVIEW.md), [sql_c1_validation.json](../adaptation/sql/sql_c1_validation.json), [metadatos saneados](../adaptation/sql/observed-schema.json).
