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
