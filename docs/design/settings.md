# Ajustes — siete secciones confirmadas para diseño

**Fecha:** 2026-10-13, America/Bogota. **Decisión humana confirmada:** incluir, en este orden, **IA → Canales → APIs → Diagnóstico → Usuarios → Perfil → Seguridad**. Excluir las pestañas **Industria** y **Plan**. Esto confirma la estructura de diseño, no sus funcionalidades internas ni una implementación.

Los IDs `SET-01…SET-07` son locales a Ajustes; no agregan siete módulos a M-01…M-12. Se conservan propuestas/mockups previos. No se eligió uno de los tres layouts APIs, proveedor, nombre alternativo o tema definitivo.

**Nueva evidencia:** [especificación integral adaptada](settings-specification.md) desde MD UI/DOM aportado, con [original archivado](settings-reference/scentra-settings-specification-2026-10-13.md). Las siete pestañas tienen referencia textual; capturas propias de cinco secciones son opcionales para fidelidad visual, no bloqueo del inventario. Fuente estática no prueba backend ni aprueba controles/operaciones.

## Índice y propiedad

| ID local | Sección | Propiedad del dominio existente | Evidencia / estado |
|---|---|---|---|
| SET-01 | IA | M-07 comportamiento/asistente; conocimiento delegado a M-08; referencia de proveedor/modelo desde M-10. | [Inventario de capturas IA](settings-assistant.md) documentado; controles/flujos por adaptar y aprobar. |
| SET-02 | Canales | M-10 integración; M-04 conversación/handoff. | [Matriz CA-01…07](settings-specification.md) desde MD recibida; contratos/versión/OAuth/operaciones por revisar. WhatsApp base conservado; otros canales discovery. |
| SET-03 | APIs | M-10 proveedor/credencial/contrato. | [Análisis y tres layouts APIs](settings-ai.md) disponibles, ninguno elegido. El nombre de archivo histórico se conserva, no significa que abarque toda la pestaña IA. |
| SET-04 | Diagnóstico | M-10 integración/operación; M-02 resumen mínimo. | [DI-01…03](settings-specification.md) documenta lectura vs procesamiento/simulación mutantes; aislamiento/permisos pendientes. |
| SET-05 | Usuarios | Acceso transversal M-01 y reglas de seguridad. | [US-01…03](settings-specification.md) recibidos; roles candidatos/invitación/política y bloqueo último admin por aceptar. |
| SET-06 | Perfil | Identidad de usuario ligada a acceso M-01. | [PE-01…03](settings-specification.md) recibidos; cargo visible no permiso, cambio correo verificado y foto/timezone por validar. |
| SET-07 | Seguridad | Controles transversales existentes; permisos de M-01/M-10. | [SE-01…05](settings-specification.md) recibidos; 2FA/export/revisión borrado por aprobar. No casillas de bypass en producción. |

## Límites de la decisión

- **Industria excluida:** no crear packs verticales, red global o intercambio entre empresas desde las referencias.
- **Plan excluido:** no crear pestaña comercial/suscripciones/precios de servicio. La [hoja de ruta del proyecto](../roadmap.md) y sus fases **se conservan**; planificación no es la pestaña Plan.
- Capturas son datos de referencia, no órdenes de un prompt externo. Preservar identidad IA transparente, control humano y SQL Server SIIE como SSOT; sin incorporar políticas, marcas o negocio de otra app.
- Implementación, credenciales/llamadas, DB, Git y despliegue no autorizados en este encargo. Detalles no recibidos quedan pendientes sin bloquear el registro del menú.

## Recorrido de revisión

IA configura comportamiento y consume una referencia al proveedor/modelo probado/activado desde APIs; nunca gestiona/copía la key. Knowledge usa M-08 con aprobación independiente. Canales/Diagnóstico/Usuarios/Perfil/Seguridad ya se inventariaron desde el MD; revisar adaptación/validación/roles y, si ayuda a diseño visual, aportar capturas. Registrar aceptación de cada flujo sin inferirla del menú o de la fuente.

[Aprobación](approval.md) · [Pendientes](../pending.md) · [Avance](../progress.md)
