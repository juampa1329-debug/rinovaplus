# Guardado de fichas por campos y solicitud de No contactar — 27Nov2026

El titular pidió resolver el conflicto al cerrar una ficha y confirmó expresamente que esa persona no quiere recibir más mensajes. Se cerró la conversación y se registraron la baja y la etapa Cerrado sin matrícula mediante los controles de RinovaPlus, sin enviarle una nueva respuesta. Este informe público omite nombres, teléfonos e identificadores de la persona.

## Causa y corrección

backend/app/institutional/workspace.py comparaba la revisión global del espacio de trabajo para guardar cualquier ficha. Un recibo, lectura o cambio en otro chat incrementaba esa revisión y podía rechazar una edición independiente. La captura original no conserva el HTTP de aquel intento; el contrato y el mensaje del conflicto sí permiten reproducir este fallo de concurrencia. También se conservaba el borrador completo del editor mientras las lecturas periódicas podían avanzar la revisión: quitar únicamente el bloqueo global habría expuesto otros campos a sobrescritura.

backend/app/institutional/contact_changes.py compara tres versiones bajo la transacción escritora existente: base consultada, edición del asesor y ficha actual. Sólo aplica campos modificados por el asesor, con mezcla por clave en customValues. Cambios ajenos en otros campos se conservan; si ambos modificaron el mismo campo a valores diferentes devuelve contact_fields_changed. Un valor ya aplicado se acepta de forma idempotente. Identidad canónica, permisos crm.write, validación vigente, identidad académica y registro de operación/auditoría siguen siendo obligatorios. Clientes antiguos sin baseClient conservan el contrato global; altas nuevas y otras mutaciones no cambian.

frontend/src/institution/Workspace.tsx conserva la base del primer cambio junto al borrador, incluso al navegar o refrescar datos. frontend/src/institution/contactEditing.ts presenta los valores en conflicto y permite conservar la edición sólo después de revisarlos; esa decisión actualiza la base, no guarda automáticamente. El usuario pulsa Guardar ficha de nuevo. No hay reintento automático de escrituras inciertas ni se repiten mensajes.

## Baja solicitada por el titular

La preferencia existente sólo permitía consulta. backend/app/institutional/contact_preference.py incorpora una acción explícita, autorizada por crm.write, con motivo y confirmación verdadera obligatorios. Se registra opt_out como operator_confirmed_request, con actor y operación estable; no se inventa un mensaje entrante autenticado. Abarca las identidades existentes de la persona canónica y sus alias, revoca consentimientos vigentes, cancela sólo salidas queued y destinatarios prepared, y cierra sus conversaciones. No altera envíos sending/inciertos ni envía confirmaciones. Una ficha sin identidad de canal se rechaza antes de escribir.

frontend/src/institution/ContactPreference.tsx muestra Registrar solicitud de No contactar en la ficha, exige motivo y casilla explícita y conserva el identificador de operación si la respuesta se pierde. Enter en el motivo no guarda accidentalmente la ficha exterior. La lista CRM → No contactar y las exclusiones de campañas/seguimientos siguen utilizando las solicitudes persistidas. Cierre por silencio, etapa comercial y revocación administrativa no se convierten por sí solos en una baja.

## Comprobación nativa y publicación

Código 8f875d8; integración de producción 7f21c6b conserva los cambios de seguimiento del otro colaborador; baja explícita 8475666; interfaz 3c73831. Publicación en deploy/coolify-rinovaplus, sin force ni cambios a main. Segundo merge b7d690e integra bc2dade y sus correcciones concurrentes de cierres/solicitudes de pago; el diff de backend/app y frontend/src entre bc2dade y b7d690e es vacío. No se ejecutaron sus nuevos controles de campaña como parte de esta petición.

Backend 8475666: despliegue knqm8q2c9n2xjst7cejzxev8, healthy 17:52:11 UTC, rollout completo 17:52:21 UTC del 27Nov. Frontend 3c73831: despliegue 41sgo6ufiknrcbfvtkt7vqys, Success 47 segundos.

Se cerró el hilo correcto, se guardó la solicitud de No contactar y se cambió Seguimiento → Cerrado sin matrícula. Tras recarga completa y búsqueda nueva, la tarjeta muestra Cerrada/Cerrado sin matrícula; la ficha consultada muestra No contactar. Sin aviso de conflicto en ese guardado y sin nuevos mensajes enviados. Otro contacto homónimo no fue modificado. No se ensayó enviando a una baja.

Una actualización manual del listado terminó con un aviso de consulta lenta; se conservó la tarjeta anterior. Una lectura nueva tras recarga corroboró el resultado guardado. Este arreglo resuelve concurrencia de fichas, no acredita que la latencia general del Inbox o la contención de almacenamiento hayan desaparecido.

## Validación y límites

Primera selección: 75 pruebas backend focalizadas pasan: mezcla de cambios independientes, conflicto en mismo campo, borrador académico protegido, autoridad, compatibilidad, repetición idempotente, confirmación de baja, identidad canónica/alias, cancelación sólo de pendientes y traducción/parseo PostgreSQL de SQL nuevo. Tras integrar los cambios concurrentes, pasan 150 backend en selección ampliada (incluye las 75 anteriores y cuatro del grafo) y 16 frontend de campañas/preferencias/helpers (solapa nueve anteriores); tipos y build finales pasan, bundle 745,27/219,77 kB gzip. No se ejecutó motor PostgreSQL aislado; la baja y el guardado se verificaron además en producción nativamente.

Frontend: 63 pasan y dos fallos heredados en la selección de 65 (explicación de entrega con mock antiguo y texto de error de acceso). Son los mismos dos documentados antes; no se declara suite completa verde. Nueve pruebas de helpers/preferencia y dos nuevas integradas en editor están incluidas en esa selección. TypeScript, ESLint modificado, Ruff E9/F y build institucional pasan. Bundle 744,87 kB / 219,64 kB gzip conserva advertencia de tamaño; Node local 22.16 difiere del rango declarado 24.

Skills de CRM y recall consultadas; no hay herramienta de memoria externa disponible en esta sesión. Continuidad apoyada en código, informes, AGENTS y grafo local con procedencia. Sin datos nominales en el grafo, consumo de modelos, DDL, seeds, servicios nuevos, cambios de modelos o escrituras SIIE. P13/P19/P21 iniciales y aceptaciones P22 técnico3/5/comercial0/5, P23 0/9 y P24 0/6 permanecen intactos. No se repiten correos ni apagados históricos. Grafo de continuidad reconstruido offline: 44 fuentes documentales, 28 archivos AST, 707 nodos/1199 aristas; snapshot general histórico intacto. El constructor admite sólo variantes exactas LF/CRLF producidas por Git, sin refrescar hashes de contenido alterado; cuatro regresiones específicas pasan. El grafo no es memoria privada CRM ni acredita por sí solo producción.
