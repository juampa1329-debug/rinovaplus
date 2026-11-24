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


## Corte operativo posterior

- Masterclasses: 139 contactos actualizados inicialmente y 78 después de revisar Pasta Artesanal/Sabores de Latinoamérica; total217. Reconsulta: cero planes listos/cero por revisar. Una ficha dejó de ser candidata durante el intervalo y se respetó su elección posterior.
- Se guardaron cuatro plantillas CRM; la primera está activa. Meta aceptó y aprobó `cbn_crm_seguimiento_duda_v1`, `cbn_crm_seguimiento_pausa_v1` y `cbn_crm_reactivacion_formacion_v1`, con primer nombre y botones de atención/baja. No se enviaron estas plantillas a personas en este corte.
- Primer handoff recuperado: generación confirmada y partes leídas, orientación a Escuela de Salud. Lote posterior23 puesto en preparación tras revisión/reautenticación. No acreditar23entregas por el mero encolado. Una entrada nueva siempre invalida el turno antiguo.
- Se habilitaron flujo y activador de8horas. La consulta de inactividad provocó degradación del proceso y contención de otras colas; la regla nueva se pausó y la siguiente consulta mostró todos los procesos al día. No se atribuye un SQLSTATE sin evidencia. Se sustituye el agregado correlacionado por unión a recibos autenticados y agrupación; sólo se toma la última salida, sin adelantarse a colas pendientes o inciertas. Diagnóstico de procesos guarda sólo clase/SQLSTATE, nunca cuerpos/SQL/credenciales.
- Base de seguimiento explícita: marketing sigue siendo el valor histórico predeterminado. `customer_request` sólo con `followup_only`, entrada real y últimas24horas, modoIA, sinNoContact y conguardas. Permite la plantillaCRM de atención solicitada sin exigir un consentimiento de campaña masiva. Fuera de esa ventana siguen consentimiento y plantillaMeta; no se crean autorizaciones ni se extiende su vigencia. Envíos conservan límite/cadencia, vínculo de cuenta y versión de consentimiento si existe.
- Continuidad de recuperación: las operaciones nuevas se vinculan a su entrada original para el manifiesto de preguntas atendidas; no se borra ni sustituye la derivación anterior. Se reconoce también la solicitud explícita de pausa, sin confundir «no quiero pausar» con una baja.
-125pruebas backend del ajuste pasan, incluyendo consentimiento/ventana/Humano/baja, preparación CRM sin permiso de marketing y diagnóstico privado. Selección solapada con las244previas. Publicación del ajuste optimizado y secuencia completa aún pendientes en este corte.

Fuente primaria revisada para la ventana de respuesta: [Política de mensajes de WhatsApp Business](https://business.whatsapp.com/policy/preview?lang=es_LA). Se conserva la separación entre respuesta solicitada dentro de24horas y plantilla aprobada fuera de esa ventana; no se deducen tarifas ni autorizaciones del contacto a partir de la aprobación.

## Ajuste de observación y despliegue adicional

897391e se publicó con backend Success4m41 y frontend Success43s. La secuencia completa quedó Activa v2; el activador v2 se guardó en borrador con cadencia1440min, pero su activación devolvió503 y no se considera aplicada. Logs nativos acotados muestran55P03, sin leer SQL ni parámetros. Se evita el recorrido de observación global cuando no existen activadores de entrada/cambio; un activador sólo de inactividad conserva su detección sin ese recorrido innecesario.73pruebas focalizadas yRuff pasan. No se modifica el bloqueo de seguridad institucional ni sus tiempos.

Se observó una restauración de control transitoria durante una acción rechazada por revisión automática; se comprobó y devolvió el chat a su modo IA original. No se usó ese cambio para enviar. La revisión no bloqueó la activación del flujo por separado.

## Verificación de la configuración y corrección de tema

dbbf867 backend Success4m18; activador y flujo Activo v2 tras reautenticación. Operación17:35:46Bogotá muestra los nueve procesos Al día; doce ejecuciones del nuevo flujo observadas después y un primer paso Completado, sin acreditar lectura por ese estado. Se conservan bajas, consentimiento, ventana, Humano y cadencia compartida con la cola.

En los historiales recuperados se identificó una falsa coincidencia: el nombre institucional CBN del texto saliente podía puntuar el programa PRE-ICFES CBN aunque el interés fuera una masterclass genérica. Se excluyen las palabras de la identidad institucional del emparejamiento léxico; PRE-ICFES explícito y Cocina explícita siguen identificándose. No se cambian contextos académicos ni asignaciones manuales. Se concreta la presentación breve del botón como Juan Pablo, de CBN, manteniendo transparencia si preguntan por la naturaleza del agente o piden atención humana.84pruebas focalizadas yRuff pasan; publicación de esta última corrección pendiente en este corte.
