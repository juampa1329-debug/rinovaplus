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
