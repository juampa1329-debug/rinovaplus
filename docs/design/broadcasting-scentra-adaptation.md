# Broadcasting: editor Meta con campos del CRM de RinovaPlus

Fecha: 17 de noviembre de 2026. Ampliación de P7; no añade peso al roadmap.

## Referencia revisada

Scentra: `C:/verane-whatsapp-ai/saas-version/frontend/src/BroadcastPanel.jsx`, funciones `PhonePreview`, `createMetaTemplate` y editor `message_template`; backend `backend/app_saas/broadcasts/router.py`, `_build_meta_components` y POST de plantillas Meta. Se adaptan el editor de cabecera/cuerpo/pie/botones, ejemplos, catálogo y vista previa. RinovaPlus conserva sus cuentas institucionales y no incorpora billing ni tenants.

Meta documenta creación mediante POST `/{WABA_ID}/message_templates`, componentes con ejemplos y un estado de respuesta que decide el proveedor: https://developers.facebook.com/docs/graph-api/reference/whats-app-business-account/message_templates/ . Guardar un borrador no solicita aprobación ni envía mensajes.

## Comportamiento implementado

- Selector de campos reales: nombre completo/primer nombre, teléfono, correo, ciudad, programa, etapa, jornada, campaña y campos personalizados activos del CRM.
- El editor conserva los nombres de campos; el backend normaliza a `{{1}}`, `{{2}}`, etc., y conserva el mapa explícito por componente. Los ejemplos son ficticios y editables; no se consulta una persona para preparar los ejemplos de Meta.
- La campaña toma ese mapa por defecto. Los valores se resuelven para cada contacto al preparar y comprobar el envío; un campo inactivo o un dato ausente excluye el envío, sin inventar sustituciones. Se conservan cero y booleanos.
- La sincronización conserva el mapa sólo si el contenido no cambió. Estados y calidad se muestran en español; `NONE` no genera un aviso de rechazo y no se imprime un diccionario interno como calidad.
- Vista previa WhatsApp con cabecera, cuerpo, pie y botones; límites, etiquetas, foco y diseño adaptable con tokens RinovaPlus. Revisión explícita por plantilla y protección del borrador al navegar.
- Crear borrador, enviar a revisión de Meta y sincronizar aprobación son pasos separados. La aprobación procede de Meta. Los envíos siguen pasando por consentimiento, control humano, cadencia, cuenta y cola única existentes.

Cabeceras multimedia mantienen el contrato de la referencia: requieren el handle de un archivo de ejemplo de Meta. La subida directa de ese archivo desde este editor todavía no está implementada. El constructor cubre marketing y utilidad; las plantillas OTP se consultan en el catálogo, pero no se genera un formato OTP con el formulario genérico.

## Validación

124 pruebas backend en Canales, broadcasting y constructor; diez frontend del módulo; TypeScript, lint de archivos afectados y build aprobados. Los primeros intentos del arnés detectaron referencias ausentes de emojis/fixture y un formulario de prueba incompleto; se corrigió el arnés sin debilitar validaciones. No se crearon contenedores, no se ejecutaron migraciones ni se modificaron bases para estas pruebas. El build conserva su aviso previo de bundle superior a 500 kB.

El webhook de test fue verificado en Meta y RinovaPlus; la respuesta real «Prueba de broadcasting rinovaplus» entró en el canal gratuito y Gemini respondió con el chat en IA. Esto no acredita por sí solo la publicación de una plantilla nueva ni los recibos de una campaña masiva. Ambos recorridos deben registrarse por separado tras el despliegue.

## Resultado en producción

Coolify desplegó `fcf5f28` en backend y frontend. Desde el editor publicado se guardó `cbn_informacion_programas_20261117`, con primer nombre y programa, ejemplos ficticios, cabecera, pie y respuesta rápida. Meta recibió la solicitud: primero devolvió **PENDING / En revisión de Meta** y en una sincronización posterior **APPROVED / Aprobada por Meta**. La aprobación procede del catálogo real; no se envió esa plantilla nueva.

La campaña separada `Prueba P7 gratuita · hello_world · 44` envió desde RinovaPlus al único destinatario autorizado del número gratuito. Se observaron aceptado, enviado, entregado y leído con un intento. Al terminar se revocó el consentimiento temporal y se desactivó la cadencia de esa cuenta. [Evidencia y límites](../../artifacts/live/p7-broadcasting-20261117.json). Falta la respuesta citada atribuida y un fallo real controlado; no cierra P7 completo.
