# M-10 — Ajustes de proveedores y credenciales

**Ubicación:** **SET-03 APIs**, dentro del [índice de Ajustes](settings.md). Se conserva el nombre histórico `settings-ai.md` para no romper enlaces; este documento no define toda la pestaña IA. **SET-01 IA** se documenta en [asistente](settings-assistant.md).

[Adaptación integral del MD recibido](settings-specification.md) completa el editor reportado en front-end estático: Nuevo valor protegido, Base URL condicional, guardar/cancelar, cargar/guardar modelo y revisar estatus. No acredita cifrado efectivo ni backend. Se mantienen auth/discovery, inferencia y activación separados; API interna JWT/endpoint key del otro CRM no selecciona nuestro mecanismo o arquitectura.

**Estado:** ampliación de diseño/plan propuesta, con **tres alternativas PNG disponibles para selección**; ninguna aprobada ni implementada. **Fecha:** 2026-10-13, America/Bogota. Se incorporan las dos capturas aportadas como referencias de organización, no como prueba de capacidades, cifrado o conectividad. Los 12 módulos y mockups claros/oscuros existentes se conservan.

## Qué muestran las capturas y qué no demuestran

| Observado | Incorporación propuesta en CRM CBN | Límite |
|---|---|---|
| Ajustes con navegación por IA, canales, APIs, diagnóstico y seguridad. | M-10 agrupa capacidades, proveedores y credenciales; M-07 sigue dueño del comportamiento del asistente. | No copiar marca, plan, “industria” o modelo SaaS de otra aplicación. “Nexo” no es nombre aprobado. |
| Tarjetas de proveedores con acción “Añadir”. | Catálogo visible + configuración de un proveedor elegido. | Una tarjeta no acredita conector, compatibilidad o cuenta configurada. |
| Grupos separados de texto, voz, búsqueda y canales. | Separación por capacidad y fase para no mezclar credenciales ni fallback. | No asumir que todos comparten API/auth/modelos ni capacidad TTS. |
| Mensajes de la referencia sobre llaves por empresa, modelos y fuentes. | Estados y auditoría explícitos, como requisitos propios sujetos a aceptación. | La captura no permite verificar almacenamiento, aislamiento, validación o permisos. No inferir multitenancy. |
| API interna y acción de refrescar credenciales de otra app. | Reservar documentación de contratos internos cuando exista backend. | No copiar URL, JWT, endpoints o llaves; no contratar integración con esa app. |

Copias locales originales: [referencia 1](settings-ai/reference-01.png) y [referencia 2](settings-ai/reference-02.png). La referencia visual no autoriza conectar servicios ni leer/escribir SIIE.

## Catálogo de candidatas, no conectores implementados

| Capacidad | Nombres presentes en las referencias | Alcance propuesto / pendiente |
|---|---|---|
| Texto/modelos | Google/Gemini, NVIDIA NIM, OpenAI, Claude/Anthropic, Groq, Mistral, OpenRouter, Kimi/Moonshot AI. | Fase 3: contrato genérico de proveedor y **un proveedor/modelo de texto elegido explícitamente** en P-016 antes de ejecución. Resto candidatas, sin promesa de implementación. |
| Agente | Hermes Agent. | La captura lo describe como agente interno; no tratarlo como proveedor LLM equivalente ni autorizar herramientas. Identidad/API/capacidades requieren discovery. |
| Voz | ElevenLabs, Google Cloud TTS, Piper local. | Fase 7A condicionada a costes, licencia, despliegue local si aplica y prueba OGG/Opus. No se instala Piper ni se configura voz ahora. |
| Búsqueda | Tavily, Brave Search API, SerpAPI. | Fuera del alcance base; requiere aprobación de necesidad, uso de resultados, datos/licencias/costes. Nunca reemplaza catálogo/precios SIIE. |
| Canal inicial | WhatsApp Cloud API. | Canal ya previsto; contratos, sandbox, firma y permisos Meta siguen pendientes. |
| Otros canales | Instagram Business, Facebook Messenger, TikTok. | Contratos conectados pendientes en P-030. WooCommerce excluido por decisión del propietario del 2026-10-19: la plataforma es de admisiones; no se incorpora comercio ni sincronización de productos. La captura histórica se conserva como evidencia. |
| API interna | Referencia de otra aplicación. | Contrato interno del CRM por definir; no se adopta su URL ni su arquitectura/autenticación por la captura. |

SQL Server SIIE permanece SSOT del negocio. Este encargo no crea esquema, tablas de secretos ni una DB separada. La configuración operacional y la ubicación de sus metadatos se decidirán técnicamente; secretos nunca en tablas académicas ni plaintext.

## Alta, prueba y activación: acciones distintas

1. **Añadir / configurar:** seleccionar capacidad, proveedor, ambiente y alias. Contrato de autenticación/capacidades específico del adapter; endpoint predefinido cuando corresponde, sin URL arbitraria editable por defecto. No se exige un endpoint o método auth genérico común a todos. No activar ni transferir datos de personas.
2. **Guardar borrador:** guardar metadatos y, cuando se autorice la implementación, ingresar credencial solo por flujo backend/secret store. El borrador no ejecuta llamadas, no se vuelve proveedor activo y no escribe SIIE. Una clave ingresada sin guardar se descarta al cerrar/cancelar; no se persiste en navegador.
3. **Validar credencial / descubrir catálogo:** si el adapter lo permite, operación server-side explícita y acotada para autenticación/listado de modelos, con aviso de coste/cuota/destino. Este paso puede preceder a elegir modelo; **no prueba que el modelo funcione**. Si la API no permite listar, usar catálogo validado/configurado del adapter y seleccionar modelo antes de la prueba final; no crear un ciclo que exija modelo para habilitar su propia selección.
4. **Seleccionar modelo/capacidad:** solo entre opciones soportadas por el contrato elegido. En los mockups, “modelo después de validar/probar conexión” se interpreta como después de autenticación/discovery cuando existe, nunca como después de la prueba final de un modelo aún no elegido. Autenticación, catálogo y prueba de inferencia son evidencias separadas.
5. **Probar configuración/modelo:** llamada explícita server-side con payload sintético mínimo, timeout/reintento acotados y aviso de coste/cuota/destino. Confirmar presupuesto antes de llamar; sin chats reales, PII, matrículas ni documentos. Resultado ligado a proveedor, **modelo**, capacidad, ambiente y versión exacta de configuración, fecha y alcance, sin secretos ni respuestas completas. Ninguna activación se apoya solo en autenticación exitosa.
6. **Activar:** permiso/confirmación separados, configuración/modelo vigentes probados y aprobación de tratamiento/coste/ambiente. Cambiar clave/modelo/endpoint/ambiente invalida prueba anterior. Una prueba válida **no activa** el proveedor ni demuestra aceptabilidad de respuestas de admisiones.
7. **Pausar / rotar / revocar:** acciones diferentes; pausar en CRM no revoca una key en el proveedor. No afirmar revocación upstream sin evidencia. Confirmar impacto y reautenticar operaciones sensibles; auditar resultado/estado incierto.

Hoy todas estas acciones son **diseño**, no botones ejecutables ni servicios conectados. No iniciar tests externos o pedir credenciales al usuario con este encargo.

## Seguridad obligatoria antes de implementación

### Credenciales y límites de acceso

Credenciales **write-only**: backend recibe el valor y no lo devuelve a UI; frontend muestra “Credencial configurada”, referencia/versionado y metadatos mínimos. No botón para recuperar key guardada. El navegador solo conserva transitoriamente una nueva entrada necesaria para enviarla; nunca localStorage/sessionStorage, caché, URL, analytics, replay de sesión o exportación. Cifrado/transporte seguro, store backend con claves separadas y acceso de servicio mínimo; redacción de logs, errores y auditoría. Este diseño propone controles, no afirma que estén implementados. OWASP recomienda gestión centralizada, mínimo privilegio y ciclo de vida/auditoría de secretos. [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).

OpenAI indica que la key no debe exponerse en código cliente y que se cargue en el servidor. Gemini también recomienda backend para llamadas de producción y secret store. Son referencias de seguridad, **no selección de proveedor** ni promesa de free tier/modelo. [OpenAI Authentication](https://developers.openai.com/api/reference/overview#authentication), [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key#security_and_secret_management).

Sandbox y producción tienen referencias/credenciales/permisos distintos, sin fallback de ambiente. Activar en sandbox no autoriza activar producción. Rotación planificada: crear nueva versión, prueba sintética, cambio autorizado, comprobar consumo y revocar anterior; evitar revocar la única credencial válida sin plan. Ante exposición, contención/revocación inmediata y recuperación segura según incidente; no sacrificar seguridad para continuidad. Evidencia de revocación debe distinguir CRM y proveedor; rotación/concurrencia y recuperación se prueban antes del piloto.

### Endpoint y egress

Endpoint predefinido por adapter; personalización solo tras política aceptada P-017. Allowlist de destinos/puertos/rutas, HTTPS/certificado válido, bloqueo de esquemas inseguros y redes locales/metadata no autorizadas; validación DNS/IP al conectar, no solo regex inicial. No seguir redirects libres; fijar/verificar destino autorizado y política de salida también en reintentos. OWASP identifica SSRF en solicitudes hacia URLs controladas por entradas y recomienda controles de aplicación/red. [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [OWASP API7:2023](https://api-security.owasp.org/editions/2023/en/0xa7-server-side-request-forgery/).

Integraciones locales futuras como Piper requieren contrato/egress propio aprobado; no excepción genérica de acceso interno. Ninguna URL de las capturas se incorpora a configuración del CRM.

### Fallback y datos

Prioridad visual no significa ruta de tráfico habilitada. Sin fallback automático entre proveedores hasta aprobar capacidad equivalente, consentimiento/contrato de datos, coste y riesgo. Un error no autoriza exfiltrar el contexto del estudiante hacia otra entidad. Primer corte: un proveedor texto, sin cascada. Reglas IA, control humano y precios/jornadas SIIE se mantienen fuera del prompt; no SQL/tool execution arbitrario.

## Roles propuestos y estados UI

| Rol por asignar | Permiso propuesto | No permitido |
|---|---|---|
| Asesor | Estado mínimo útil del canal/IA en conversación. | Ver/añadir/probar credenciales o activar proveedor. |
| Administrador técnico | Metadatos, borradores, pruebas sintéticas dentro de ambiente autorizado. | Recuperar valor guardado o activar producción por tener permiso de configuración. |
| Aprobador de operación/datos | Aprobar coste/tratamiento y activación según ambiente. | Saltarse validación de configuración/seguridad. |
| Responsable de seguridad | Autorizar rotación/revocación y consultar auditoría saneada. | Copiar secretos a informes o prompts. |

Permisos se validarán en servidor por acción/recurso/ambiente, con reautenticación al rotar/revocar/activar donde corresponda; personas y separación de funciones pendientes, no RBAC implementado.

| Estado/escenario | Representación/acción propuesta |
|---|---|
| Carga / vacío | Esqueleto o lista vacía con “Añadir proveedor”; no ceros que simulen métricas reales. |
| Borrador / sin probar | Indicadores diferentes; guardar no activa. |
| Credencial validada / catálogo descubierto | Estado limitado a autenticación/discovery del adapter, no a funcionamiento de modelo. Sin activación. |
| Modelo seleccionado / prueba final pendiente | Elección separada y test sintético requerido para esa versión/modelo; no bloquear selección esperando ese mismo test. |
| Probando | Deshabilitar duplicar test; payload sintético/coste/destino visibles sin secreto. |
| Prueba válida, no activo | Resultado acotado/fecha/configuración; activación requiere confirmación/permisos. |
| Prueba desactualizada | Cambio de versión invalida evidencia; pedir nueva prueba antes de activar. |
| Error autenticación / permiso | Mensaje saneado, sin copiar response/key; no decir automáticamente que cuenta no existe. |
| Modelo/capacidad inválidos / endpoint rechazado | Explicar incompatibilidad o política; no ofrecer desactivar validación TLS. |
| Cuota/429 / timeout / error proveedor | No retries ilimitados; espera/cancelación y resultado incierto separados; no activación/fallback automática. |
| Activo / pausado / revocado | Diferenciar operativo en CRM de revocación confirmada upstream; mocks identificados como demostración. |
| Vault no disponible / conflicto de versión | No perder configuración vigente ni recuperar keys al cliente; bloquear operación sensible y preservar evidencia. |
| Rotación pendiente / revocación incierta | Reautenticación, confirmación de impacto y seguimiento; estado no declarado exitoso sin prueba. |
| Sin permiso | Deshabilitar/explicar acción y validar servidor; ocultar control no equivale a control de acceso. |

Escritorio mantiene shell oscuro común CRM CBN; móvil reorganiza lista/inspector o drawer en secuencia de pantallas. Formularios con labels, foco/errores asociados y acciones distintas. Estos estados/adaptaciones están **especificados**, no renderizados/verificados exhaustivamente por una imagen.

## Tres alternativas de layout — disponibles para selección

Ninguna seleccionada o aprobada. El coordinador generó, mostró e inspeccionó las tres imágenes en este orden: **1 lista+inspector, 2 catálogo+drawer, 3 alta guiada**. Estilo oscuro coherente, claves vacías y estados demostrativos Borrador/Sin probar; test/activar están deshabilitados con explicación. No hubo llamadas reales. Los antiguos M-10 claro/oscuro no se reemplazan.

### 1 / A — Espacio de proveedores: lista e inspector

`provider-workspace.png`: lista filtrable por capacidad/ambiente con inspector persistente y acciones separadas. Favorece operación/diagnóstico sin salto de contexto; ocupa más ancho en escritorio y exige secuencia en móvil.

![Propuesta 1 A M-10, lista e inspector disponible para revisión](settings-ai/provider-workspace.png)

### 2 / B — Catálogo compacto y drawer

`provider-catalog.png`: candidatas agrupadas con estado/fase, drawer para configuración puntual. Fácil descubrir categorías; riesgo de confundir catálogo con capacidad instalada, mitigado por etiquetas claras y detalle separado.

![Propuesta 2 B M-10, catálogo compacto y drawer disponible para revisión](settings-ai/provider-catalog.png)

### 3 / C — Alta guiada de credencial

`credential-wizard.png`: capacidad/ambiente → credencial → autenticación/discovery cuando aplica → modelo → test sintético final → revisión, con guardar borrador disponible. Reduce omisiones; más pasos para operador experto. Las agrupaciones visuales de pasos no fusionan autenticación con prueba de modelo. Completar asistente no activa: acción posterior separada.

![Propuesta 3 C M-10, alta guiada disponible para revisión](settings-ai/credential-wizard.png)

[Procedencia, prompts exactos y orden visual](settings-ai/generation-prompts.json) disponibles. Solo diseño raster, no código/app, vault real, prueba de endpoint o elección de proveedor. Símbolos/logos ilustrativos raster no aprueban identidad oficial ni nombre del producto; CRM CBN sigue siendo la referencia textual provisional.

## Puertas y siguiente decisión

D-01 incorpora estas alternativas para revisión; **P-018** registra selección/ajustes. P-016 elige un proveedor texto antes de ejecutar fase 3; P-017 define secretos/roles/egress y controles de fases 0–2. P-019 cubre rotación/operación de fase 6; P-020 discovery de búsqueda/canales fuera de base. Ninguno se cierra por ver la captura. Consultar [fases](../roadmap.md), [pendientes](../pending.md), [aprobación](approval.md).
