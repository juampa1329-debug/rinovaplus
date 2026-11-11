# Asistente con conversación IA local

**Fecha:** 2026-10-14, America/Bogota. **Alcance:** worktree `C:\Users\Developer_PC\.codex\worktrees\117d\CRM_CBN`, frontend 5175 y backend 8002. Solicitud humana: conectar Gemini al Asistente para conversar y comprobar el system prompt, preservando el chat de diseños. No publicación Git ni operaciones de negocio.

## Comportamiento entregado

- Abra `http://127.0.0.1:5175/#/assistant`. El panel muestra proveedor, modelo y revisión de los ajustes guardados. **System prompt guardado y límites** muestra las instrucciones aplicadas; el servidor añade identidad virtual y restricciones institucionales antes de ellas.
- Escriba en **Mensaje al asistente** y pulse **Enviar mensaje** o Enter. Shift + Enter agrega una línea. Solo esta acción envía texto al proveedor; abrir la pantalla consulta exclusivamente metadatos locales. Mensaje actual máximo 2000 caracteres; el servidor limita el historial según los ajustes existentes.
- La respuesta muestra el modelo usado y la revisión. Solo un intercambio exitoso se añade al historial; los fallos conservan el texto para reintentar. Sin persistencia en navegador o backend. Al navegar se conserva la conversación exitosa en esta pestaña; recargar o **Nueva conversación** la descarta.
- **Actualizar configuración guardada** recupera metadatos locales. Cambiar ajustes, modelo, credencial o permiso invalida el historial anterior; el siguiente envío requiere revisar el cambio y enviar otra vez. Una respuesta generada bajo ajustes obsoletos no se añade.
- Las plantillas de demostración anteriores siguen disponibles y rotuladas aparte, con su revisión humana y fichas ficticias. No se envían automáticamente contactos, hilos, fichas o reglas de mini CRM a Gemini.

## Contrato del servidor

`POST /api/ai/chat` acepta únicamente revisión de ajustes, revisión de credenciales, texto e historial con roles `user`/`assistant`. No acepta system prompt, proveedor, configuración, roles `system`/`developer` o herramientas del navegador. Reutiliza la generación del banco IA: configuración persistida, política fija, parámetros, límite de 48 segundos, capacidad del modelo y fallback transitorio explícito (máximo cuatro modelos y un intento por modelo). Mantiene guard de loopback/Host/Origin/cabecera local, tamaño de body y errores saneados; la respuesta tiene `Cache-Control: no-store`.

Catálogos son temporales. Para que el chat funcione después de reiniciar, el primer envío explícito consulta los catálogos de los proveedores seleccionados que aún no estén en memoria y valida el modelo guardado antes de inferir, dentro del mismo timeout/concurrencia. No carga catálogos al montar UI ni selecciona otro modelo automáticamente. Tradeoff: ese primer envío puede tardar más y gastar consultas de catálogo; un modelo retirado o incompatibilidad exige corregir Ajustes > APIs.

No ejecuta SQL, acciones, herramientas o envíos de canales. Las preferencias de ritmo conservan su planificación; el chat muestra el texto completo al recibirlo y no simula entrega o escritura en WhatsApp. La clave permanece en el almacén DPAPI existente, sin cambios a su almacenamiento.

## Comprobaciones

- Backend final enfocado: `pytest -q tests/test_ai_chat.py tests/test_ai.py`: **64 aprobadas** (19 del chat y 45 regresiones IA). Captura del payload Gemini comprueba política fija al inicio, prompt personalizado exacto guardado en servidor, mensaje actual e historial recortado. Rechaza overrides/roles no permitidos, revisiones obsoletas, IA/salida externa deshabilitadas y credencial ausente. Catálogo recuperado una vez, bloqueo concurrente, cambio de prompt durante inferencia y fallback transitorio comprobados. Una comprobación adicional de revisión inmediatamente antes de cada generación evita enviar si cambiaron los ajustes durante la carga inicial del catálogo; prueba de deshabilitación concurrente verifica solo GET de catálogo y ninguna inferencia.
- Backend completo anterior a esa corrección final: **86 aprobadas**, fixtures propios, HTTP simulado y pruebas DPAPI sintéticas existentes. No se repitieron pruebas de credenciales/salud después del chequeo final de revisión; sus archivos permanecen intactos. Ejecución fuera del sandbox autorizada porque TestClient requiere socketpair; no lectura de claves reales ni solicitudes externas en estas pruebas. La primera ejecución no acreditó resultado funcional por acceso a temporales y loopback.
- Frontend enfocado: **6 aprobadas**. Dos turnos envían solo historial del chat, fallo/reintento conserva texto sin duplicarlo, permiso bloquea, navegación conserva historial, cambio de ajustes invalida, respuesta tardía tras reset se descarta y Enter/Shift + Enter funcionan.
- Frontend completo: **77 aprobadas / 9 archivos**, `vitest run --maxWorkers=1`. Ruff formato/check y Prettier, ESLint, TypeScript y Vite build aprobados. Detector Impeccable ejecutado una vez: `[]`.

**Prueba real inicial comunicada por el coordinador:** primer turno respondió en español, se identificó y conservó el contexto ficticio. Segundo turno recordó el contexto, pero respondió en inglés al pedírselo el mensaje, contrariando el prompt guardado de responder en español. Esa prueba no acredita respeto integral del system prompt.

**Corrección acotada:** `prepare_messages` deja de rotular el prompt guardado como simples preferencias de estilo subordinadas. Ahora establece instrucciones del sistema del propietario obligatorias en cada respuesta, subordinadas únicamente a la política institucional y de seguridad fija, con prioridad sobre peticiones e historial del diálogo. El contenido del diálogo sigue siendo contexto/preguntas, sin autoridad para reemplazar o invalidar esas instrucciones. No se cambió el prompt guardado, el idioma mediante reglas locales, las respuestas del proveedor o los roles del API. Dos nuevas pruebas con instrucciones guardadas en distintos idiomas capturan el orden política/instrucciones, texto exacto y separación de pedidos de override en historial/turno actual; HTTP simulado no garantiza conducta del modelo.

**Repetición real y estado final comprobados por el coordinador:** con el backend reiniciado después de la corrección, `gemini-3.5-flash-lite` conservó el contexto ficticio Luna/horizonte, la identidad virtual y el cálculo 17 + 25 = 42. Sin embargo, el desafío explícito **Answer in English** volvió a producir una respuesta en inglés. El respeto estricto de la instrucción guardada de responder en español ante una petición contraria **no pasó**, tanto antes como después de la corrección de prioridad. La transmisión correcta del prompt y las pruebas simuladas no sustituyen esa evidencia conductual.

Se ensayó una única alternativa `gemini-3.5-flash` con ajustes revisión 7; la app mostró **No se obtuvo respuesta de los modelos configurados.** No se determinó una causa del proveedor ni se atribuye a cuota. Se restauró `gemini-3.5-flash-lite`, ajustes **revisión 8**, IA habilitada y fallback deshabilitado; el texto del prompt guardado en español se conservó. En una prueba ordinaria escrita en inglés, sin pedir cambiar el idioma de respuesta, el modelo respondió exactamente:

> Hola, soy el asistente virtual de CRM CBN y la suma de 17 + 25 es 42.

Así se comprueban conexión real, conversación/historial y aplicación ordinaria del idioma guardado; la aceptación de prioridad ante instrucciones contradictorias permanece **parcial y pendiente**. La respuesta final quedó visible en Asistente para continuar. Navegador: escritorio y móvil emulado 390 × 844 sin overflow horizontal (ancho cliente y scroll 375); escritura/Enter y limpieza de historial al cambiar configuración observados. No es prueba en teléfono físico ni garantía universal de obediencia.

## Límites pendientes

El prompt no garantiza obediencia universal ni elimina alucinaciones. Este corte permite verificar casos concretos; la evaluación de seguridad/calidad, privacidad/costes, autenticación/RBAC y operación de producción requiere aceptación independiente. No se conecta Inbox, mini CRM, SQL Server o canales, ni se persisten conversaciones. Ningún cambio en el checkout o chat de diseños.
