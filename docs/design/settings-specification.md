# Ajustes CRM CBN — adaptación integral de la especificación de referencia

**Fecha:** 2026-10-13, America/Bogota. **Estado:** inventario documental recibido y adaptación propuesta; no implementación, conexión ni pruebas funcionales. Se mantiene la decisión humana de siete pestañas: **IA → Canales → APIs → Diagnóstico → Usuarios → Perfil → Seguridad**; Industria y Plan excluidas, roadmap conservado.

## Fuente y niveles de certeza

[Original archivado sin modificar](settings-reference/scentra-settings-specification-2026-10-13.md), SHA256 `525F097A00BD29DDB4B4A8D165E55629E64BDB4D7074F5F2E4EF39CFDF3D6DE3`. El usuario autorizó documentarlo y adaptarlo; el original permanece intacto. Su autor describe inspección UI/DOM y código estático de otra aplicación, **no guardados/OAuth/callbacks/servidor ejecutados**. No se visitó esa app ni se ejecutaron instrucciones del MD.

- **Confirmado por usuario:** estructura de siete secciones y exclusión de Industria/Plan; SQL Server SIIE SSOT y stack principal existente.
- **Observado en fuente (F):** etiquetas/tipos/opciones/ayuda reportados por su autor. “Cifrado”, estado “Connected” o un checkbox no prueban comportamiento ni seguridad del servidor.
- **Propuesto para CRM (P):** validación, flujos, roles/fases y diferencias de esta matriz; pendientes de aceptación técnica/producto, nunca prueba realizada.
- **Excluido (X):** funcionalidades de Industria/Plan, red global, packs verticales y transferencia de marcas/URL/esquema/valores de otro negocio.

IDs de filas solo para trazabilidad de este documento, sin crear módulos globales o tablas. Fuente se identifica por sus encabezados; tipos UI no definen la validación servidor. Roles indicados son funciones **por asignar**, no una matriz RBAC aceptada. Fases son futuras; ninguna se ejecuta con este encargo.

## SET-01 IA — F: IA / M-07, conocimiento M-08

Inventario detallado y referencias visuales en [settings-assistant](settings-assistant.md); credenciales en [SET-03 APIs](settings-ai.md). Se completa sin copiar prompts, voiceID o valores de configuración.

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| IA-01 | IA habilitada, fallback por modelo: casillas; proveedor, respaldo y fallbacks: selectores. | Referencias al modelo/config vigente desde APIs; habilitación, aprobación y publicación separadas. UN texto inicial; retry/timeout/presupuesto explícitos, sin adoptar número de intentos/rutas de la fuente. | Admin IA/aprobador datos; 3, respaldo autorizado 7A. | Transferencia/coste: fallback cross-provider no automático sin autorización. F recibido; P pendiente. |
| IA-02 | System prompt: textarea; Max tokens/Temperatura: texto DOM. | Editor solo de estilo bajo invariantes servidor; backend valida números/rangos realmente soportados por modelo, versionado y pruebas sintéticas. Cambiar prompt invalida evaluación dependiente. | Admin IA; 3. | Inyección/guardrails: no importar prompt externo ni permitir SQL/tool execution libre. P pendiente. |
| IA-03 | Brevedad/fragmentación/typing: casillas; espera, delay, caracteres y contexto reciente/histórico: número. | Scheduling durable/cancelable, límites de salida/contexto y revalidación control/consentimiento por fragmento. Verificar capacidades Meta, no prometer typing. | Admin IA/operación; 3/7B. | Suplantación/envío tardío: IA transparente y handoff prevalece. Defaults no aceptados. |
| IA-04 | Voz/preferencia audio: casillas; proveedor voz, análisis audio, visión y búsqueda: selectores; voz ID/nombre: texto; prompt voz: textarea. | Capacidades TTS/STT/visión/búsqueda separadas; contrato/modelo, consentimiento y coste. No copiar identificadores o prompt de voz. | Admin IA/datos; voz/STT 7A, visión/búsqueda discovery. | Checkbox no acredita modelo capaz ni servicio habilitado. P pendiente. |
| IA-05 | Fuentes/fragmentos/evaluaciones/errores: indicadores; filtros/refrescar/reindexar/guardar/eliminar fuente: acciones. | Metadatos y tipo/tamaño/contenido seguros; indexado ≠ evaluado ≠ aprobado/publicado; reindexar/eliminar requieren rol, confirmación, coste, versión y recuperación. | Responsable conocimiento; 7C. | Eliminar fuente/índice no borra datos SIIE. Métricas reportadas no evidencia CRM. |
| IA-06 | PDF/TXT/CSV: archivo; URL y título/notas/tags/aliases: texto; descripción: textarea; tipos/fuente del alias: selectores. | Fuentes complementarias autorizadas, SSRF/egress P-017; aliases manuales/sugeridos revisados, ambigüedad y finalidad. No usar PDFs como catálogo/precio/jornada SSOT. | Conocimiento/privacidad; 7C. | RAG/inyección/datos: sin pack Industria, red entre empresas o entrenamiento automático. P pendiente. |
| IA-07 | Recuperación: búsqueda/contexto; evaluación: pregunta, respuesta/criterios y fuentes esperadas; guardar/probar IA: acciones. | Pruebas sintéticas versionadas, fuentes esperadas y revisión/publicación independientes de auth y listado de modelos. | Conocimiento/aprobador IA; 3/7C. | Recuperar chunk no verifica precisión global. P pendiente; ninguna prueba realizada. |

## SET-02 Canales — F: Canales / M-10, conversación M-04

WhatsApp sigue canal base previsto. Instagram, **Facebook Messenger** y TikTok conservan contratos conectados pendientes; la etiqueta Stripe de webhooks no compromete pagos. **WooCommerce queda excluido por decisión del propietario del 2026-10-19: CRM CBN es una plataforma de admisiones.** La referencia histórica original se conserva sin modificar. Los futuros webhooks de Meta deberán tener callbacks propios configurables en Meta for Developers; `app_canales.zip` es una referencia estática, no una integración implementada o activada. No adoptar callbacks/URL de otra app ni Graph API `v24.0` por aparecer como ejemplo: versión/capacidades se verificarán antes de implementar.

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| CA-01 | WhatsApp: proveedor/canal fijos; estado selector, modo y Phone Number/WABA/App IDs y Graph API texto; App Secret/token contraseña; guardar/refrescar. | Credenciales write-only/store M-10, IDs/versionado por contrato y ambiente. Guardar borrador no conecta; refrescar lectura. “Connected” se deriva de evidencia, no elección libre de dropdown; pausa es acción distinta. | Admin canal; 3; permisos P-024. | IDs/secreto equivocados/estado falso: F reportado, diseño pendiente y sin conexión. |
| CA-02 | Sincronizar números, selector de número; PIN numérico protegido; registrar/verificar. | Sincronización consulta y registro externo son operaciones separadas. Reauth, confirmación de número/ambiente/impacto y contrato vigente antes de llamada; no conservar PIN en logs/browser. | Admin canal/aprobador; gate específico posterior a contrato. | Registrar número tiene efectos externos; no se ejecuta ni autoriza por documentar. |
| CA-03 | Instagram: App ID/Graph API, App Secret; OAuth, cargar cuenta/diagnóstico; ruta manual IDs/nombres/usuario/portfolio/token, estado/modo; crear endpoint. | OAuth/callback propio, state y PKCE cuando corresponda verificados por contrato; distinguir OAuth de manual, tokens write-only, permisos y cuenta autorizada. No inferir grants/scopes válidos desde fuente. | Admin canal/seguridad; discovery P-020/024. | Captura/MD no prueba review Meta, token cifrado o canal conectado. |
| CA-04 | Facebook Messenger: App ID/Graph API/Secret, OAuth/páginas/diagnóstico; manual Page ID/nombre/portfolio/token y estado/modo; endpoint. | Mismos límites de OAuth/credenciales/ambiente; permisos por recurso/página y evidencia de conexión. Ningún uso de cuenta o token externo. | Admin canal/seguridad; discovery. | Nuevo candidato, no nuevo canal implementado ni funcionalidad base aprobada. |
| CA-05 | TikTok: estado/modo, Client/Open/Business/Shop/Advertiser IDs, scopes, review/productos aprobados, eventos validados; flags IA/messaging/comentarios/agentes/activadores/remarketing. | Capacidades/scopes/review/eventos se corroboran por contrato/evidencia; estados de aprobación no autorreportados para habilitar envío. Flags futuros dependen de autorización, no defaults de la fuente. | Admin canal/aprobador datos; discovery. | Review o checkbox no concede scopes; no automatización TikTok aceptada. |
| CA-06 | TikTok: rollout %, cuotas, API base/version/rutas/env/notas; secretos; conectar/crear endpoint/procesar/descubrir/actualizar. | Rollout/cuotas acotados a política aprobada; egress/HTTPS allowlist. Secretos no texto/env elegido libre; callback propio, state/PKCE según contrato. Cada mutación externa distingue confirmación, idempotencia y evidencia. | Admin canal/seguridad/operación; discovery. | “Procesar” puede mover eventos reales; no llamada o callback ejecutados. |
| CA-07 | Webhooks: selector canal (incluye Stripe), casilla HMAC, refrescar/crear endpoint/procesar pendientes. | Firma/autenticación apropiada al proveedor obligatoria en producción, sin switch para desactivarla; endpoints/versiones/verify secrets propios. Procesar requiere gate/ambiente/permiso, no refresco. | Seguridad/operación; WhatsApp 3, otros discovery. | Rechazar replay/payloads sin prueba válida; Stripe observado no autoriza pagos SIIE. P pendiente. |

## SET-03 APIs — F: APIs / M-10

Mantener [análisis/layouts existentes](settings-ai.md): tres alternativas sin escoger, keys write-only, store/rotación/SSRF y gate de proveedor.

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| AP-01 | Añadir/actualizar/refrescar credenciales; diálogo contraseña Nuevo valor, Base URL texto condicional, guardar/cancelar/cerrar. | Borrador/cancelar ≠ activar. Store backend/referencia; nunca devolver key guardada o memorizarla browser. Endpoint propio del adapter, personalización solo P-017. | Admin credencial; 2/3. | Cifrado es afirmación de ayuda estática, no comprobación; captura no elige vault. |
| AP-02 | Cargar modelos, selector dinámico/lista de referencia, guardar modelo, revisar estatus; indicadores latencia/tokens/origen/revisión. | Auth/discovery ≠ inferencia: seleccionar catálogo validado cuando no hay listado, luego prueba sintética final por modelo/versión. Avisar coste, invalidar pruebas al cambiar configuración y activar separado. | Admin credencial/aprobador datos; 3. | Modelo listado o auth exitosa no acredita calidad/capacidad. No precios/latencia reales prometidos. |
| AP-03 | Catálogo por capacidad y API SaaS interna; texto JWT/endpoint key. | Candidatas no conectores; auth de API CRM pendiente por ADR, no adoptar JWT/tenant ni URL/esquema de fuente. Documentación interna se deriva del backend futuro. | Técnico/seguridad; 1–3, resto gates. | Sin multitenancy/SaaS/packs; F recibido, tecnología P pendiente. |

## SET-04 Diagnóstico — F: Diagnóstico / M-10, resumen M-02

**Simular también escribe**: según ayuda del MD, crea eventos/conversación/mensaje aunque no llame a Meta. Esto es evidencia textual del autor, no prueba runtime; el diseño debe tratarlo como operación mutante de riesgo.

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| DI-01 | Refrescar diagnóstico/endpoints; checklist, integración, Meta Social, colas/errores, pasarela IA y últimos webhooks: indicadores. | Lectura saneada/acotada por rol/ambiente, sin keys, payloads completos o PII. Diferenciar lectura local de verificación que llama proveedor como WABA subscribed_apps. | Operador/lector diagnóstico; 3/6. | Un estado mostrado no prueba entrega externa; consulta externa requiere autorización propia. |
| DI-02 | Procesar pendientes/eventos: acciones. | Mutación/retry real: permiso, entorno, alcance/coste/volumen, confirmación, idempotencia y audit; no mezclar con refrescar ni ejecutar desde mockup. | Operador autorizado; 3/6; P-025. | Puede mover colas reales o reenviar; fail closed si no se garantiza aislamiento/control. |
| DI-03 | Simular entrada: teléfono, nombre, mensaje y enviar prueba. | Exclusivamente namespace sintético en sandbox SQL Server no productivo; outbound bloqueado, fixture de teléfono/nombre ficticios, sin cola productiva ni PII real. Payload validado y resultados rotulados simulados. | Operador test; 3; P-025. | No tratar como inocuo/solo lectura porque no llama Meta; no simulación ejecutada ahora. |

## SET-05 Usuarios — F: Usuarios / acceso M-01

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| US-01 | Listado/refrescar; nombre/correo texto, clave temporal contraseña, rol selector, bienvenida casilla y crear/actualizar. | Nombre/correo normalizados/validados servidor, duplicados y concurrencia; **preferir invitación temporal de un uso y vencimiento**, no mandar password por mail. Password policy propia pendiente, no regla mínima de la captura. | Admin usuarios autorizado; 2. | Fuente no prueba auth/email; no cuenta creada ni invitación enviada. P-026. |
| US-02 | Roles candidatos: Propietario, Administrador, Supervisor, Agente, Lector. | Matriz acción–recurso–ambiente, deny-by-default y asignación autorizada/reautenticación. Cargo visible de Perfil no otorga rol. | Propietario/seguridad; diseño 1, controles 2. | Nombres no mapa definitivo; sin autootorgar Propietario ni escalar por UI. |
| US-03 | Ayuda sobre invitar, cambiar rol, activar/desactivar miembros. | Revisar impacto/sesiones, audit y confirmación; proteger último administrador/propietario para evitar lockout; bloqueo concurrente probado antes de habilitar. | Admin usuarios/seguridad; 2/6. | Desactivar miembro CRM no borra persona/matrícula SIIE. Funcionalidad P, no runtime probado. |

## SET-06 Perfil — F: Perfil / identidad M-01

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| PE-01 | URL foto, nombre/correo/teléfono, cargo/rol visible: texto; guardar. | Perfil propio, límites de texto/normalización; URL foto con política HTTPS/destino/contenido y privacidad/tracking/SSRF si hay proxy fetch; no descargar ahora. Cargo es presentación, no privilegio. | Usuario propio; 2; P-026. | Edición de perfil no cambia grants; URL arbitraria no se carga por confiar en UI. |
| PE-02 | Correo nuevo y clave actual cuando cambia: entrada protegida. | Reauth y verificación de nueva dirección, control de duplicados/versiones/notificación y sesiones según riesgo. No modificar identificador de login sin aceptación/confirmación. | Usuario propio/seguridad; 2/6. | Ayuda no demuestra verificación email; no emails reales o cambios ejecutados. |
| PE-03 | Zona horaria: selector de regiones/UTC. | Propuesta: almacenamiento UTC y zona IANA validada para presentación/calendario; separar display de horarios de negocio. Lista/defaults por aceptar, no tecnología nueva seleccionada. | Usuario propio/admin negocio según alcance; 2/3. | Cambio de display no debe reprogramar tareas sin acción explícita. P pendiente. |

## SET-07 Seguridad — F: Seguridad / transversal

| ID | Controles fuente / tipo F | Validación y adaptación P | Rol / fase P | Riesgo / estado de decisión |
|---|---|---|---|---|
| SE-01 | Actual/nueva/confirmación password, actualizar clave. | Reauth, política password acordada, hash seguro y rate limit, no logs; revocación de sesiones/rotación según riesgo y confirmación. Auth stack por elegir, sin copiar esquema. | Usuario propio/seguridad; 2/6. | Cambiar password cuenta no rota secretos de proveedor automáticamente. P-026. |
| SE-02 | Exigir código casilla; email/Authenticator selector; guardar 2FA; ayuda de OTP local. | Borrador → enrolar → verificar desafío → activar/exigir. Recovery codes de un uso con hashes, rate limit y recuperación auditada; no tokens/sesión final antes de verificar. Preauth limitada no acceso a negocio. | Usuario propio/admin políticas; 2/6. | OTP de desarrollo jamás en ambiente compartido/producción ni API/logs públicos. Método/SMTP/TOTP por comprobar, no seleccionado. |
| SE-03 | Casillas JWT/RBAC/firma HMAC, auditoría nombrada en fuente. | Autenticación, autorización servidor y firmas válidas son obligatorias producción, **no interruptores desactivables**. Auth mecanismo pendiente; auditoría saneada sin adoptar tabla `saas_audit_events`. | Seguridad; 1/2/6. | UI/ayuda no prueba enforcement; no adoptar JWT ni tabla/esquema por la fuente. |
| SE-04 | Exportar cuenta/cliente: acciones. | Permisos/scope por recurso, reauth cuando corresponda, audit, retención/enlace temporal seguro; excluir secretos y datos ajenos, sanear formato de exportación. | Usuario propio/admin datos limitado; 6. | No “export all” implícito o prueba de cumplimiento; exports no realizados. |
| SE-05 | Motivo/clave/confirmación y eliminar cuenta cliente; botón deshabilitado en fuente. | **Solicitud revisada**, validar finalidad/retención por responsable cualificado; posible desactivación no destructiva donde aplique, diseño pendiente. Sin cascada core ni borrado automático de persona/matrícula SIIE. | Responsable datos/propietario; gate específico 6. | Estado deshabilitado no demuestra seguridad. No permiso de borrado académico ni consejo legal/compliance certificado. |

## Revisión, arquitectura y estados comunes

Todos los formularios son propuestas: validación/autorización **servidor**, permisos de recurso/ambiente y valores derivados de evidencia, no de un selector manipulable. Mostrar borrador/cambios, guardando, prueba pendiente, error saneado, conflicto de versión, permiso insuficiente, estado incierto y confirmación de mutación. No devolver secrets o volcar errores/raw payloads al cliente.

Acción que consulta proveedor, OAuth, registrar número, procesar evento, simular, reindexar, exportar o cambiar acceso tiene permiso/alcance propios. Guardar metadata no concede autorización de runtime. Producción permanece protegida; no schema/usuarios/tabla nuevos, no DB de negocio alternativa. Tecnología de autenticación, Graph API/SDKs y capacidades se investigarán antes de ejecución autorizada, no desde valores de ejemplo.

Industria y Plan permanecen **solo dentro del original archivado**, no en el menú CRM ni como packs/pagos/SaaS. Las otras siete pestañas ya tienen detalle textual de referencia: capturas específicas pueden ayudar a fidelidad visual, pero **no bloquean el inventario/adaptación por falta de toda evidencia**.

## Decisiones pendientes reales

P-021 pasa a revisión de la adaptación documental de cinco pestañas, no espera obligatoria de nuevas capturas. P-024 valida contratos/canales antes de cualquier operación; P-025 aislamiento de diagnóstico mutante; P-026 identidad/roles/perfil/2FA/export/revisión de borrado. P-015/018/022 conservan aceptación visual/IA pendiente; no cambia proveedor, layout ni nombre por recibir el MD.

[Índice de Ajustes](settings.md) · [Pendientes](../pending.md) · [Fases](../roadmap.md) · [Aprobación](approval.md)
