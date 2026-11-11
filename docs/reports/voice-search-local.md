# Voz, audio, visión y búsqueda — A-026 / P-039

Fecha: 2026-10-14, America/Bogota. Alcance autorizado únicamente en el worktree de IA `codex/proveedores-ia`, frontend 5175 y backend 8002. No se modifica el checkout/chat de diseños ni se conecta WhatsApp.

## Operación

1. En **Ajustes → APIs**, guarde las claves de ElevenLabs, Google Cloud TTS, Tavily Search, Brave Search API o SerpAPI. Reutilizan el almacén Windows DPAPI existente. Gemini sigue siendo independiente de Google Cloud TTS: este último requiere habilitar su API y facturación/permisos del proyecto correspondiente.
2. Cargue **voces y modelos** del proveedor elegido. ElevenLabs consulta voces guardadas de la cuenta con paginación y modelos habilitados para TTS. **Nombre visible de voz** selecciona el ID y nombre reales de ese catálogo; el ID manual también debe pertenecer al catálogo. Google TTS expone voces, no un catálogo de modelos inventado. Piper lista únicamente modelos ONNX locales con su archivo de configuración.
3. En **IA**, habilite voz, elija proveedor/voz/modelo y las reglas. Puede preferir notas de voz, responder con voz a una nota entrante y activar un máximo por conversación. Seleccione los modelos Gemini para análisis de audios y visión desde el catálogo cargado en APIs. Guarde los ajustes.
4. En **Asistente**, escriba o adjunte un audio/imagen de hasta 4 MB. Puede solicitar búsqueda web o imágenes para ese mensaje. Las fuentes se presentan como enlaces externos; el servidor no descarga esas URLs y el navegador no carga imágenes remotas automáticamente. El audio generado se reproduce manualmente mediante un blob obtenido por una ruta local protegida.

El prompt de voz orienta la redacción oral. El timbre/acento pertenecen a la voz seleccionada y su configuración del proveedor; no se atribuye soporte de un prompt acústico libre a ElevenLabs, Google TTS o Piper.

## Reglas y límites

- Voz deshabilitada: respuesta en texto. Límite agotado, incluido cero: texto. Después se aplican preferencia de voz y regla de nota entrante. Sin esas reglas, la IA devuelve una decisión JSON estructurada en la misma generación; Gemini utiliza el esquema JSON de la API y el servidor valida texto/booleano. Una decisión inválida no provoca otra inferencia ni un gasto TTS.
- La cuota pertenece al servidor y se conserva en `.local/ai-conversations.json`. El ID de conversación y su versión se conservan como metadata no secreta en sessionStorage; nunca se confía en un contador enviado por el navegador. Recargar y reiniciar backend conservan el cupo de la misma conversación durante 24 horas. **Nueva conversación** crea otro presupuesto. Cambiar configuración/credenciales invalida la conversación anterior y exige una nueva; no modifica su contador histórico.
- Se reserva un cupo antes de TTS y no se devuelve ante resultado incierto. Solo se realiza un intento TTS por turno; un ID de turno ya iniciado se rechaza para impedir duplicación de costes, sin afirmar que pueda recuperar una respuesta perdida. Los fallos de síntesis conservan el texto. Una cancelación mata el proceso Piper pendiente y elimina su WAV temporal.
- Un solo worker/operación simultánea. Máximo 500 conversaciones locales vigentes, 200 turnos por conversación, 20 audios temporales de hasta 6 MB, vencimiento de audio 10 minutos. No se conservan transcripciones ni respuestas en el ledger. El texto TTS se limita a 5000 bytes UTF-8. Las llamadas HTTPS usan hosts fijos, TLS, límites/timeout y no siguen redirects ni proxies del entorno.
- Gemini recibe archivos inline validados por tamaño, MIME y firma: WAV, MP3, OGG, FLAC, WebM, PNG, JPEG y WebP. Su transcripción/extracción y las fuentes externas son contexto no confiable. No autorizan herramientas, SQL, pagos, matrícula ni envíos. La obediencia absoluta del modelo a prompts sigue sin garantía; se conserva el límite documentado en el informe de Asistente.
- No existe entrega WhatsApp, conversión OGG/Opus ni prueba en teléfonos. La característica opera desde Asistente local y conserva los límites del resto de la aplicación.

## Piper local

Motor aislado en `.local/piper/.venv/Scripts/python.exe`, `piper-tts==1.8.0`; modelos en `.local/piper/voices/*.onnx` y `*.onnx.json`. El adapter ejecuta únicamente ese Python y `-m piper`, con rutas verificadas y texto por stdin, sin shell ni parámetros/ejecutables recibidos del modelo o navegador. No descarga modelos automáticamente al abrir la pantalla.

El executor preparó `es_MX-claude-high` desde la colección oficial: ONNX 63 122 309 bytes, SHA256 `3ef40a71ea63852cd8ab7e6fa7d2ecdcfa67a0b47c9c48e3f10e02ee02083ea0`; conserva MODEL_CARD y README de licencia. Motor GPL-3.0-or-later; dataset Apache-2.0 y repositorio de voz MIT. Síntesis independiente real comprobada: WAV mono PCM16, 22050 Hz, 3,541 segundos. Además, el coordinador comprobó en el navegador el circuito real: nota WAV entrante transcrita por Gemini, respuesta sintetizada con Piper, audio reproducible de 7,767075 segundos (readyState 4) y segundo turno con límite 1 que conservó texto sin generar otro audio.

## Evidencia de implementación

Backend: **143 pruebas completas aprobadas**, Ruff lint/formato. Incluye HTTP simulado para todos los nuevos proveedores, claves sintéticas, redacción de errores, catálogos/paginación, formatos, guardas, cuota cero/unlimited/reglas/nota entrante, persistencia/fallo/reenvío, singleflight y cancelación de subprocess. Frontend: formato, ESLint, tipos y build aprobados; pruebas focalizadas de catálogo, reglas, adjunto explícito, presupuesto recibido y descarga protegida/revocación del blob aprobadas. Suite frontend completa del snapshot inicial: **84 pruebas aprobadas en 10 archivos**, con un worker. Tras la comprobación real se corrigió únicamente la limpieza del input de archivo nativo al enviar/quitar/iniciar conversación: **15 pruebas focalizadas finales**, formato/lint/tipos/build aprobados. Se comprobó que un envío fallido conserva el archivo y que se puede seleccionar nuevamente el mismo archivo después del éxito. Backend sin cambios después de sus 143 pruebas; no se repitió su suite.

Las credenciales reales de ElevenLabs/Google TTS/Tavily/Brave/SerpAPI no se usaron en la implementación: la operación externa con esas cuentas requiere claves disponibles y prueba explícita. No se declaran conexión real o facturación comprobadas por mocks. Se conserva Gemini existente y su configuración; el coordinador comprobó el circuito real con datos sintéticos, incluyendo transcripción, reproducción Piper y cupo agotado. APIs mostró campos de los ocho proveedores. El coordinador comprobó IA móvil a 390 × 844, controles apilados/legibles y ausencia de overflow (clientWidth/scrollWidth 375), además de controles de escritorio. Estado final guardado: revisión 10, voz/preferencia/regla entrante desactivadas para activación deliberada; Piper y es_MX-claude-high seleccionados, límite habilitado en 1 y modelos Gemini de audio/visión conservados. El system prompt y modelo de texto del propietario se mantienen.

## Referencias primarias

- [ElevenLabs: voces guardadas](https://elevenlabs.io/docs/api-reference/voices/search), [modelos](https://elevenlabs.io/docs/api-reference/models/list), [síntesis](https://elevenlabs.io/docs/api-reference/text-to-speech/convert).
- [Google TTS: voces](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/voices/list), [síntesis](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize).
- [Piper mantenido](https://github.com/OHF-Voice/piper1-gpl), [voz y licencias](https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_MX/claude/high/MODEL_CARD).
- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Brave imágenes](https://api-dashboard.search.brave.com/api-reference/images/image_search), [SerpAPI imágenes](https://serpapi.com/google-images-api).
- [Gemini audio](https://ai.google.dev/gemini-api/docs/audio), [visión](https://ai.google.dev/gemini-api/docs/image-understanding).


### Visión real por HTTP y readback final

El coordinador realizó una única petición `/api/ai/media-chat` con PNG sintético propio de 160 × 100: rectángulo rojo sobre fondo blanco. HTTP 200, revisión 10, revisión de credenciales 3, Gemini 3.5 Flash-Lite, voz deshabilitada, 7,27 segundos. La extracción fue: «La imagen muestra una gran figura rectangular de color rojo intenso en el centro, situada sobre un fondo blanco y puro. No hay texto en la imagen.» La respuesta identificó al asistente virtual y reconoció el rectángulo. Artefactos ignorados `.local/piper/vision-proof.png` y `vision-proof.json`. Esta evidencia es HTTP, no una comprobación de subida de imagen en navegador; audio/reproducción/cupo y responsive sí se comprobaron en navegador.

Readback: las 12 fuentes/tests coinciden con `.local/voice-search-final-source.json` tras el ajuste de input. Las referencias locales de los cuatro documentos modificados se resolvieron y `git diff --check` pasó. La revisión final solo modifica documentación pasiva; no repite suite, normalizador, proveedor ni procesos. Los otros proveedores siguen con aceptación real pendiente de sus claves y WhatsApp sin entrega.
