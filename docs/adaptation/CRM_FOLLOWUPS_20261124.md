# Seguimiento CRM y solicitudes comerciales · 24 de noviembre de 2026

El titular solicita seguimiento de personas que ya conversaron, no un nuevo envío masivo a importados. Se revisaron los playbooks locales `Playbook_Reactivacion_Leads_Septiembre_Octubre_CBN.pdf` y `Playbook_Plantillas_Ventas_WhatsApp_CBN.pdf`. Son referencia de cadencia y tono; sus precios, escasez y ejemplos no sustituyen las fichas vigentes.

## Recorrido preparado

- Opción de flujo **Sólo seguimiento de personas que ya conversaron**: exige entrada autenticada de la misma identidad/cuenta anterior al mensaje enviado; no convierte un importado o una salida de marketing sin respuesta en conversación iniciada.
- Requiere horario de silencio activo y salida al recibir respuesta. Se revalidan modo IA, etapa, programa, identidad, época de control, baja, consentimiento y horario antes de enviar. El cambio a Humano detiene el seguimiento.
- Cuatro momentos orientativos del PDF: 4–12 horas, 24–48 horas, 48–72 horas y 15–30 días. Valores propuestos: 8 horas, 36 horas, 60 horas y 21 días desde la salida de referencia; no sumar esas duraciones como esperas consecutivas. Configuración y activación reales pendientes en este corte.
- Plantilla CRM permite texto, imagen, vídeo, audio, documento y botones según capacidades del canal. Un adjunto debe corresponder a la formación y estar revisado. No inventar que hubo una llamada, reserva, pago, cambio de tarifa o liberación de cupo.
- WhatsApp fuera de la ventana de respuesta conserva el requisito de plantilla Meta aprobada. Instagram/Messenger no reciben excepciones para enviar fuera de su ventana. Una plantilla CRM no elimina las reglas del proveedor.
- Estado **No contactar** visible en la ficha, derivado de solicitudes autenticadas y revisiones existentes, aplicado al contacto canónico y alias fusionados. No se inventa una nueva etapa comercial ni se borra la baja. El consentimiento sigue verificándose por separado; una nueva autorización explícita posterior es la que puede sustituir una baja previa.

## Solicitud «Hablar con Juan Pablo»

Un caso real produjo `gemini_handoff` aunque el contexto de campaña sí estaba incluido; no fue ausencia de saldo ni fallo del transporte. Había reglas contrapuestas: «si solicita una persona, usa revisar» y la excepción comercial del botón.

El turno exclusivamente compuesto por el botón verificado usa contrato `decision=responder` en el principal y los respaldos. Se retira esa regla de derivación sólo de ese turno. Un mensaje de persona real, un turno mixto o un origen no acreditado conserva revisión y modo Humano. Si el proveedor viola el contrato, se registra fallo; no se inventa una respuesta ni una entrega.

Recuperación administrativa explícita de handoffs vacíos: sólo últimas 24 horas, campaña aceptada de misma cuenta/identidad/hilo, sin mensajes/operaciones posteriores y época exacta de la derivación automática. Conserva operación anterior y crea otra nueva; no reproduce envíos inciertos. La revisión informa que los chats elegidos volverán a IA. Recuperación real todavía pendiente en este corte.

## Verificación

244 pruebas backend seleccionadas pasan, más 27 de resiliencia con el contrato nuevo (selecciones solapadas, no sumar). Cinco frontend, tipos, ESLint, Ruff y compilación institucional pasan; aviso histórico de tamaño de bundle conservado. Sin DDL, seeds, servicios nuevos ni escrituras SIIE. No hay nuevos mensajes ni flujos activos acreditados todavía. P23 queda planificada 0/7; aceptaciones anteriores y P22 no cambian.
