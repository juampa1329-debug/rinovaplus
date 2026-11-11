# Ajustes IA y proveedores — implementación local

**Fecha:** 2026-10-14, America/Bogota. **Autorización:** solicitud expresa del propietario de implementar las funciones de las dos capturas dentro de frontend/backend existentes. Sustituye el límite anterior de solo propuesta para esta unidad; no autoriza producción, SQL, canales, Git ni despliegue.

## Resultado

- IA: habilitación para pruebas, Gemini/xAI Grok/OpenRouter, principal/respaldo y hasta dos modelos por proveedor, fallback explícito, system prompt con contador, tokens/temperatura, brevedad, fragmentación, espera/escritura, caracteres por fragmento, límite de salida e historial reciente/truncado, guardar/descartar/recargar y prueba sintética.
- APIs: presencia de credencial por variable de entorno sin exponerla, descubrimiento real bajo opt-in, selección y guardado de modelos. Grok corresponde a xAI; Groq de la captura es otra empresa y no se incorporó por inferencia.
- FastAPI: DTOs estrictos, JSON atómico exclusivamente en `.local/ai-settings.json`, revisión optimista contra sobreescritura entre pestañas, errores saneados y rechazo de archivo corrupto sin sobrescribirlo.
- Adaptadores HTTPS de hosts fijos, TLS, sin redirecciones/proxy de entorno/herramientas. Petición entrante 64 KB; respuesta proveedor 2 MB y texto 32.000 caracteres; timeout por llamada 12 s y prueba total 48 s; una operación externa concurrente por proceso. Fallback solo para 408/429/500/502/503/504 o error de red/timeout; máximo cuatro intentos, uno por modelo. Errores de credencial/parámetros no disparan fallback.
- Catálogo Gemini paginado hasta tres páginas y 3.000 entradas; exceso falla sin catálogo parcial. Filtra `generateContent` y comprueba límites publicados. OpenRouter filtra texto/parámetros y desactiva fallback interno; xAI usa Responses con `store:false`. Parámetros no admitidos/rechazados se informan sin ocultarlos.
- Se conserva la configuración temporal y las revisiones de plantillas Asistente/Inbox. La nueva IA no toma control de conversaciones. Reset demo conserva configuración IA guardada; borradores tienen descarte explícito y aviso al salir por navegación de app o recargar.

## Comprobación

- Backend: Ruff formato/check y pip check aprobados; **52 tests pytest** (7 anteriores + 45 nuevos), temporales dentro de `.local/` y transports HTTP simulados. Cubren persistencia/relectura/revisión, almacenamiento fallido, límites/tipos, Host/Origin/cliente/cabecera, body y error sin eco, opt-in, contratos de tres proveedores, respuesta malformada, catálogo/capacidades, timeout, fallback/transitorios, prompt/historial/fragmentación y exclusión de pensamientos Gemini.
- Frontend: **69 tests** (64 anteriores + 5 nuevos), formato/lint/tipos/build aprobados. Nuevos casos cubren controles, guardar/reabrir, borrador IA/APIs, catálogo/modelo/prueba guardada, invalidación, descarte/recarga, conflicto y disponibilidad. Aserciones antiguas de ausencia de llamadas se acotan: Ajustes consulta su backend; no llama datos de negocio.
- Navegador coordinador: guardado real con xAI/texto sintético, recarga conservando valores, temperatura fuera de rango bloqueada, habilitación sin modelo rechazada con error saneado, restauración de valores iniciales/revisión 2. Escritorio y móvil 390 × 844, IA/APIs sin desborde horizontal. Capturas finales a cargo del coordinador.
- Runtime final reiniciado por coordinador sobre los archivos Python finales: live 200, ready 503 esperado, ajustes directos y mediante proxy 200/revisión 2/valores iniciales/IA y outbound deshabilitados; sin cabecera local 403 y Origin externo 403. Detector Impeccable sobre UI modificada: `[]`; `git diff --check` sin errores de whitespace (avisos normales CRLF).
- Primeros comandos desde raíz no localizaron configuración npm/pytest; corregidos al cwd correspondiente. Sandbox Windows impidió temporales/socketpair; pytest se ejecutó con escalación aprobada y temporales aislados, sin llamadas reales. No se atribuyeron esos fallos de entorno al negocio.

## Límites y operación

Banco de pruebas de **un solo usuario/proceso en loopback**, no identidad/RBAC de producción. No se probaron credenciales reales ni calidad, disponibilidad o coste de modelos. `/health/ready` sigue 503 por integraciones pendientes. Sin SQL/Redis/Meta, outbox, trabajos durables, envío/typing real, datos de contactos ni cambios de permisos. El prompt fijo no sustituye controles del canal: aquí no existen herramientas ni acciones de negocio.

No almacenar datos personales ni claves en el prompt persistido. Variables backend: `GEMINI_API_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`; salida deshabilitada por defecto, opt-in `CRM_AI_OUTBOUND_ENABLED=true`. Reiniciar backend tras cambiar entorno, cargar catálogos y guardar modelos antes de probar. [Operación en README](../../README.md). P-016/017/026 y aceptación de canales mantienen requisitos conectados; fase 1 no se declara cerrada.

## Referencias oficiales

- [Gemini generación](https://ai.google.dev/api/generate-content) y [modelos](https://ai.google.dev/api/models).
- [xAI generación de texto](https://docs.x.ai/developers/model-capabilities/text/generate-text).
- [OpenRouter catálogo](https://openrouter.ai/api/v1/models) y [Chat Completions](https://openrouter.ai/docs/api-reference/chat-completion).

Estas referencias guiaron los adapters. Los tests simulan contratos; no acreditan sesiones reales con los servicios.
