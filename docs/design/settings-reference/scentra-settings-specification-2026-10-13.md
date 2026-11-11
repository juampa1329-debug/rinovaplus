# Especificación funcional de Ajustes — Scentra +AI

**Aplicación revisada:** https://app.scentra-ai.online/  
**Fecha de revisión:** 13 de octubre de 2026

**Adaptación educativa, 24 de octubre de 2026:** esta copia de la referencia excluye conectores de comercio electrónico por instrucción del propietario. Las capacidades del Scentra original no constituyen funciones aprobadas para CRM CBN.

## Alcance y convención

La página **Ajustes** contiene nueve pestañas: **IA, Industria, Canales, APIs, Diagnóstico, Usuarios, Perfil, Seguridad y Plan**. El contenido cambia dentro del panel al seleccionar cada pestaña; algunas secciones de Canales aparecen como acordeones.

Se registran las etiquetas, tipos de controles, opciones visibles, ayudas y acciones que se pudieron verificar en la interfaz. No se incluyen valores reales de la cuenta, claves, tokens, prompts, datos de clientes, correos ni importes de facturas. Las acciones con efectos externos no se ejecutaron. Cuando una función se describe a partir de ayuda o del código estático del front-end, se indica expresamente; no equivale a una prueba de respuesta del servidor.

## Controles comunes de Ajustes

- **Pestañas:** IA, Industria, Canales, APIs, Diagnóstico, Usuarios, Perfil, Seguridad y Plan.
- El panel opera sobre la empresa activa. La cabecera mantiene además selector de empresa, búsqueda, control de tema y cierre de sesión; esos controles pertenecen al marco general de la aplicación, no a los formularios de Ajustes.
- Un botón `?` abre ayuda contextual con propósito, acciones, riesgos y consejos de revisión.
- Las áreas tienen botones propios de actualización o guardado. No hay un único botón global que guarde todas las pestañas.

## IA

### Enrutamiento de modelos

- **IA habilitada** — casilla.
- **Proveedor** — selector: `Google / Gemini`, `NVIDIA NIM`, `OpenAI`, `Claude / Anthropic`, `Hermes Agent`, `Groq`, `Mistral`, `OpenRouter`, `Kimi / Moonshot AI`.
- **Fallback por modelo habilitado** — casilla.
- **Fallback del modelo principal** — selector con opción de no usar respaldo y modelos disponibles según proveedor/API.
- **System prompt** — área de texto para las instrucciones del agente.
- **Max tokens** y **Temperatura** — campos de texto en el DOM observado.
- **Proveedor de respaldo** — selector con la misma lista de proveedores.
- **Fallback del modelo de respaldo** — selector dinámico con opción de no usar segundo respaldo.

La ayuda indica que el fallback se intenta ante rate limit, timeout o error temporal. El orden de los modelos se define aquí; los modelos se configuran en **APIs**. La interfaz indica hasta dos intentos por proveedor y hasta cuatro opciones combinando proveedor principal/secundario.

### Ritmo humano para WhatsApp

- **Respuestas breves sin perder contexto** — casilla.
- **Fragmentar respuestas largas en mensajes naturales** — casilla.
- **Espera antes de responder (seg)** — número.
- **Typing antes del primer envio (ms)** — número.
- **Chars por mensaje** — número.
- **Delay entre fragmentos (ms)** — número.
- **Max tokens salida** — número.
- **Mensajes recientes** — número.
- **Chars por mensaje historico** — número.
- **Mostrar “escribiendo...” en WhatsApp cuando Meta lo permita** — casilla.

### Voz, audio, visión y búsqueda

- **Voz habilitada** y **Preferir nota de voz** — casillas.
- **Proveedor de voz** — selector: `ElevenLabs`, `Google Cloud TTS`, `Piper local`.
- **Analisis de audios** — selector observado con `Google / Gemini`.
- **Vision Intelligence** — selector: `Google / Gemini`, `OpenAI`, `Claude / Anthropic`, `Hermes Agent`, `OpenRouter`, `Kimi / Moonshot AI`.
- **Busqueda web/imagen** — selector: `Tavily Search`, `Brave Search API`, `SerpAPI`.
- **Voice ID manual opcional** y **Nombre visible de voz** — texto.
- **Prompt de voz** — área de texto.

La interfaz indica que se requieren credenciales del proveedor en **APIs** para habilitar varios servicios. También indica que los resultados de fuentes web quedan pendientes de aprobación humana antes de usarse con clientes.

### Base de conocimiento (Knowledge Base)

La página muestra métricas dinámicas de fuentes, fragmentos indexados, evaluaciones RAG aprobadas y fuentes con errores. Son indicadores, no campos editables.

Acciones visibles: **Mostrar: Todos** (filtro de fuentes), **Refrescar**, **Reindexar todo**, **Activar pack vertical**, **Agregar como pendientes**, **Aprender de conversaciones** y **Publicar activos seguros**. Por sus etiquetas y ayudas, sirven para refrescar/indexar fuentes, importar sugerencias como pendientes, proponer alias a partir de conversaciones y publicar activos marcados como seguros. La ayuda indica que las sugerencias se deben aprobar antes de usarse en búsqueda.

Campos de portada/metadatos de una fuente:

- **Título visible** — texto.
- **Descripción de uso** — área de texto.
- **Etiquetas** — texto.
- **Alias de búsqueda** — texto.
- **Archivo** — selector de archivo; la zona de carga acepta PDF, TXT y CSV.
- **Guardar portada** — guarda los metadatos de la fuente.
- **Reindexar** y **Eliminar** — acciones por fuente. **Eliminar** es destructiva y no se probó.

Campos para asociar expresiones del cliente con conceptos reales:

- **Cómo lo dice el cliente** y **Nombre real o intención** — texto.
- **Tipo** — selector: `Producto`, `Servicio`, `Documento`, `Promocion`, `Política`, `General`.
- **Fuente vinculada** — selector de fuente, incluida `Sin fuente especifica`.
- **Nota interna** — texto.
- **Guardar alias** — guarda la asociación.

Pruebas de recuperación/calidad:

- **Probar recuperación RAG** — consulta de búsqueda; acción **Buscar contexto**.
- **Pregunta de prueba** — texto.
- **Respuesta esperada opcional** y **Fuentes esperadas opcionales** — áreas de texto; la interfaz indica una fuente por línea o separada por comas.
- **Evaluar RAG** — evalúa la pregunta contra el contexto recuperado.

Fuentes web/PDF:

- **URL**, **Título opcional**, **Notas opcionales**, **Descripción de uso**, **Etiquetas** y **Alias** — texto.
- **Añadir web/PDF** — agrega la fuente descrita.

## Industria

### Estado del pack vertical

La interfaz explica que un pack adapta el pipeline CRM, campos comerciales, segmentos, plantillas, activadores, flujos, KPIs y agentes recomendados. También muestra el estado de industria, estado/versión del pack, automatizaciones, KPIs esperados e historial de aplicaciones.

### Controles

- **Refrescar** — vuelve a consultar el estado.
- Selector **Industria** — opciones: `General`, `Automotriz`, `Estetica y belleza`, `Ecommerce`, `Academias`, `Servicios financieros`, `Clinicas y salud`, `Scentra Stay`, `Seguros`, `Legal`, `Inmobiliarias`, `Restaurantes`, `Retail`, `Servicios`, `Soporte tecnico`.
- Casilla **Preparar y vincular agentes Stay usando el prompt general del tenant**.
- **Aplicar vertical** — acción principal para el pack seleccionado.
- **Ver agentes** — abre/revisa los agentes sugeridos.
- **Activar base Stay** y **Ver marketplace** — acciones de Scentra Stay. En el estado observado, **Activar base Stay** estaba deshabilitado; la ayuda indica que se requiere tener activo/habilitado el módulo en el plan.

La ayuda contextual advierte que aplicar un pack puede cambiar el pipeline y los campos visibles del CRM. Recomienda revisar qué elementos quedarán en borrador y validar el impacto antes de aplicar.

## Canales

Las integraciones están agrupadas en acordeones. Los campos de credenciales usan contraseña. La interfaz indica que ciertos tokens se cifran en backend y luego solo se muestra una pista protegida.

### Meta WhatsApp Cloud

- **Refrescar**.
- **Proveedor** — selector deshabilitado, opción `Meta`.
- **Canal** — selector deshabilitado, opción `WhatsApp`.
- **Estado** — selector: `Connected`, `Desconectado`, `Paused`.
- **Modo de envío** — texto.
- **Phone Number ID**, **WABA ID**, **Meta App ID**, **Graph API** — texto; el ejemplo de versión de Graph API es `v24.0`.
- **Meta App Secret** y **Token permanente de Meta** — contraseña.
- **Guardar integracion** — guarda la integración.

### Verificar número WhatsApp

- **Sincronizar números** — consulta los números conectados a WABA.
- Selector **Selecciona un número sincronizado...**.
- **PIN de 6 dígitos** — contraseña.
- **Registrar/verificar** — registra/verifica el número seleccionado con el PIN de verificación en dos pasos de Meta, según la ayuda.

### Instagram Business

La ruta principal utiliza OAuth: **Instagram App ID**, **Graph API**, **Instagram App Secret** y **Conectar Instagram**. La ayuda dice que se autoriza la cuenta profesional y Scentra genera/guarda el token cifrado. **Diagnóstico IG** revisa conexión, revisión de Meta, webhook y eventos. **Cargar cuenta** carga/descubre la cuenta; aparecía deshabilitado en el estado observado.

Controles de conexión manual/legacy:

- **Estado** — `Conectado`, `Pausado`, `Desconectado`.
- **Modo envío** — `Instagram Login`, `Flujo clásico con Facebook Page`, `Prueba local`.
- **Page ID**, **Instagram Business ID**, **Nombre página**, **Usuario Instagram**, **Business Portfolio ID** — texto.
- **Token manual** — contraseña.
- **Guardar conexión manual**.
- **Crear endpoint Instagram** — la ayuda lo destina a una app propia cuando soporte necesita Callback URL y Verify token.

### Facebook Messenger

La ruta principal usa **Facebook App ID**, **Graph API**, **Facebook App Secret** y **Conectar Facebook** para autorizar una página administrada. La interfaz indica que el Page token se guarda cifrado. **Diagnóstico FB** revisa estado, revisión de Meta, webhook y eventos; **Cargar páginas** carga las páginas autorizadas.

Controles manuales/legacy:

- **Estado** — `Conectado`, `Pausado`, `Desconectado`.
- **Modo envío** — `Facebook Graph real`, `Prueba local`.
- **Page ID**, **Nombre página**, **Business Portfolio ID** — texto.
- **Page Access Token manual** — contraseña.
- **Guardar conexión manual**.
- **Crear endpoint Facebook** — crea el endpoint para una app propia.

### TikTok

El panel agrupa OAuth, revisión de aplicación, recursos, eventos y controles de seguridad/activación.

- **Estado** — `Connected`, `Paused`, `Desconectado`.
- **Modo** — `TikTok OAuth real`, `Prueba local`.
- **Client Key**, **Open ID**, **Business / Shop ID**, **Advertiser ID**, **Scopes** — texto.
- **App Review** — `Sin registrar`, `Pendiente`, `Con cambios`, `Aprobado`.
- **Productos aprobados**, **Scopes aprobados** — texto.
- **Eventos reales validados** — casilla.
- **Modo de envíos** — `Desactivado`, `Observación sin enviar`, `Manual permitido`, `Real automatizable`, `Prueba local`.
- **Activación %**, **Cuota diaria de envios**, **Cuota IA diaria** — número.
- Casillas **Business Messaging**, **Responder comentarios**, **IA TikTok**, **Agentes TikTok**, **Activadores TikTok**, **Remarketing TikTok**.
- **Business API base**, **Business API version**, **Send message path**, **Comment reply path**, **Access token env opcional**, **Notas operativas** — texto.
- **Client Secret** y **Webhook Secret** — contraseña.
- Acciones **Diagnóstico TikTok**, **Descubrir recursos**, **Procesar eventos**, **Guardar TikTok**, **Crear endpoint TikTok**, **Conectar TikTok** y **Actualizar estado**.

La ayuda indica que se validan permisos, revisión de app, scopes, callback, firma y payloads; que los eventos se normalizan a Inbox/comentarios/leads; y que envíos, IA y automatizaciones dependen de revisión, producto aprobado, flags administrativos, rollout y cuotas. El callback mostrado es `https://api.scentra-ai.online/saas/v1/integrations/tiktok/oauth/callback`.

### Webhooks

- Selector de canal: `WhatsApp`, `Meta`, `Instagram`, `Facebook`, `TikTok`, `Stripe`.
- **Requerir firma HMAC** — casilla.
- **Refrescar** — actualiza el estado/listado.
- **Crear / actualizar endpoint** — crea o actualiza el endpoint del canal; la sección indica que proporciona Callback URL y Verify token.
- **Procesar eventos pendientes** — procesa/reintenta los eventos pendientes.

## APIs

### Catálogo de proveedores

La interfaz organiza los proveedores por tipo. Cada tarjeta ofrece **Añadir** cuando falta una credencial y **Actualizar** cuando ya existe. La ayuda indica que las llaves se guardan cifradas por empresa y que los modelos se cargan al expandir cada proveedor. También existe **Refrescar credenciales**.

Proveedores IA: `Google / Gemini`, `NVIDIA NIM`, `OpenAI`, `Claude / Anthropic`, `Hermes Agent`, `Groq`, `Mistral`, `OpenRouter`, `Kimi / Moonshot AI`.

Voz: `ElevenLabs`, `Google Cloud TTS`, `Piper local`.

Búsqueda web e imágenes: `Tavily Search`, `Brave Search API`, `SerpAPI`. La ayuda indica que los resultados externos requieren aprobación humana antes de usarse con clientes.

Canales de admisiones: `WhatsApp Cloud API`, `Instagram Business`, `TikTok`.

La sección **API SaaS interna** indica que los endpoints privados usan Bearer JWT y que los webhooks resuelven la empresa por endpoint key.

### Editor genérico de credenciales

La estructura del editor se verificó en el código estático público sin abrirlo ni modificar la configuración:

- Al seleccionar **Añadir** o **Actualizar** se prepara un diálogo local. El guardado es una acción separada.
- El diálogo muestra el nombre del proveedor y la clave de credencial.
- **Nuevo valor** — contraseña, placeholder `Pegar API key / token / secreto`.
- **Base URL** — texto condicional para proveedores que lo admiten; placeholder por defecto `https://host/v1`. El front-end incluye ayuda de URL OpenAI-compatible para Hermes.
- **Guardar cifrado** — guarda la credencial cifrada; durante el envío cambia a `Guardando...` y se deshabilita.
- **Cancelar** y **Cerrar** — cierran el diálogo sin guardar.
- Luego de guardar, la credencial se representa con una pista protegida, no con el valor completo.

Las tarjetas de proveedores con modelos añaden **Cargar modelos**, un selector dinámico, **Guardar modelo** y **Revisar estatus**. Guardar modelo queda deshabilitado hasta elegir uno; revisar estatus queda deshabilitado sin modelo o mientras la comprobación está en curso. El selector se alimenta con modelos devueltos por el proveedor o una lista de referencia. La comprobación puede mostrar modelo, estado, latencia, tokens, origen y última revisión. Según el proveedor también puede mostrar notas de facturación/uso recomendado y un enlace a documentación.

## Diagnóstico

Acciones visibles: **Refrescar diagnóstico**, **Procesar pendientes**, **Verificar WABA subscribed_apps**, **Simular entrada** y **Refrescar** en la sección de endpoints.

**Simular entrada** tiene los campos **Teléfono cliente**, **Nombre**, **Mensaje** y la acción de envío de prueba. La ayuda dice que no llama a Meta: inserta un webhook falso usando el WABA/Phone configurado y comprueba si se convierte en conversación y mensaje.

El panel reúne **Checklist de conexion**, **Endpoints webhook**, **Integraciones**, **Meta Social**, **Colas y errores**, **Pasarela IA** y **Últimos webhooks**. Muestra estados y errores recientes; son datos de diagnóstico, no campos editables. La ayuda advierte que **Procesar pendientes** puede mover colas reales.

## Usuarios

- **Refrescar** — actualiza el listado.
- **Nombre** — texto, placeholder `Nombre visible`.
- **Correo** — texto, placeholder `correo@empresa.com`.
- **Clave temporal** — contraseña; la ayuda indica mínimo 8 caracteres para usuarios nuevos.
- **Rol** — selector: `Propietario`, `Administrador`, `Supervisor`, `Agente`, `Lector`.
- **Enviar correo bonito de bienvenida** — casilla.
- **Crear o actualizar** — acción del formulario.

La ayuda contextual también describe invitar usuarios, cambiar roles y activar/desactivar miembros. No se mostró en la captura una matriz de permisos detallada por rol; los permisos exactos deben definirse a partir de la lógica de autorización y no inferirse solo por el nombre del rol.

## Perfil

- **URL foto de perfil**, **Nombre completo**, **Correo**, **Teléfono** y **Cargo / rol visible** — texto.
- **Zona horaria** — selector: `Colombia (America/Bogota)`, `Peru (America/Lima)`, `Mexico (America/Mexico_City)`, `Este USA (America/New_York)`, `Pacifico USA (America/Los_Angeles)`, `Espana (America/Madrid)`, `UTC (UTC)`.
- **Clave actual para cambiar correo** — contraseña; solo se requiere al cambiar el correo, según la ayuda.
- **Guardar perfil** — guarda los cambios.

La zona horaria determina cómo se muestran horarios de mensajes, diagnósticos, registros y alertas. La ayuda indica Colombia como zona predeterminada.

## Seguridad

### Clave y segundo factor

- **Clave actual**, **Nueva clave**, **Confirmar nueva clave** — contraseña.
- **Actualizar clave** — cambia la clave.
- **Exigir código al iniciar sesión** — casilla.
- **Método** — selector `Código por email` / `Google Authenticator`; aparecía deshabilitado en el estado observado.
- **Guardar 2FA** — guarda la configuración del segundo factor.

La ayuda indica que no se emiten tokens hasta validar el OTP por correo o Authenticator. También dice que en producción se requiere SMTP para enviar códigos por email y que el backend local devuelve un OTP de desarrollo.

### Políticas y privacidad

- Casillas **JWT requerido**, **RBAC por rol** y **Firma HMAC por defecto en nuevos webhooks**.
- El panel informa que las acciones críticas se auditan en `saas_audit_events`.
- **Exportar mi cuenta** — exporta datos de la cuenta.
- **Exportar cliente** — exporta el cliente seleccionado en Inbox.
- **Motivo interno** — área de texto.
- **Tu clave actual** — contraseña requerida por la acción de eliminación.
- **Eliminar cuenta del cliente** — botón de eliminación; aparecía deshabilitado. La ayuda dice que exige propietario o administrador, clave actual y confirmación final. Es destructiva y no se probó.

## Plan

- **Refrescar** — actualiza plan y módulos.
- Selector **Moneda** — `COP` / `USD`.
- La página presenta **Plan y consumo**, **Módulos activos** y **Planes disponibles**, con estados activo/inactivo.
- **Pagar / activar** — aparece en opciones de plan. La ayuda indica que abre checkout del proveedor y que el plan se activa solo cuando un webhook confirma el pago. No se inició checkout.
- **PDF** — descarga asociada a registros de facturación.

Los planes, módulos, estados y registros de facturación pueden depender de la cuenta. No se incluyen importes ni datos de factura observados.

## Validación y límites de esta especificación

- Los controles se identifican como texto, contraseña, número, casilla, selector, área de texto o archivo según la interfaz/DOM.
- En la mayoría de los campos no se observaron atributos HTML `required`, `min` o `max`. Eso no descarta validación personalizada en la aplicación o backend.
- No se ejecutaron guardados, OAuth, sincronización, procesamiento de webhooks, simulación, exportaciones, eliminación, cambios de clave ni pagos.
- Los formularios de credenciales se describen con el editor genérico del front-end; no se añadieron proveedores ni se usaron credenciales de la cuenta.
- Los cambios de permisos, canales, seguridad, perfil y plan deben implementar validación del servidor, autorización por rol, estados de carga/error y confirmación para operaciones destructivas. Esas respuestas transaccionales no se probaron.
