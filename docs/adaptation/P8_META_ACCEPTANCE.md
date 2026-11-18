# P8: aceptación operativa Meta

Estado: 100%, 4/4 criterios; corte 18 de noviembre de 2026. General 97,14%, 272/279 hitos y 52/56 criterios. Se conserva el peso original; sólo P8.close.m5 y P8.close pasan a realizados/aceptados. P9 se revisará por separado.

## Recorrido comprobado

- Campañas → Campañas CRM: borrador de prueba con cuenta gratuita, audiencia de una sola identidad del propietario, zona America/Bogota, espera de diez minutos, una hello_world oficial y salida por respuesta.
- Preflight rechazó inicialmente consentimiento revocado/cadencia apagada. Tras autorización expresa del propietario se habilitaron temporalmente y el cupo pasó de dos a tres porque los dos anteriores seguían reservados por P7.
- La misma inscripción se pausó y reanudó manteniendo su hora límite exacta. El backend cambió de contenedor por redeploy saludable y conservó ID de inscripción, ID de paso, versión y plazo.
- La salida real utilizó el dispatcher P7/C10, con una sola inscripción y un solo intento; entrega/lectura se acreditan únicamente mediante los recibos observados en la evidencia.
- En una copia independiente, editar creó v2 y restaurar v1 creó v3 en borrador; historial conservado y original activo intacto. Esa copia se convirtió después en una espera sin mensajes para comprobar cancelación por Humano con cero envíos.
- Plantilla CRM de simulación guardada con variable de primer nombre, texto neutro y aviso explícito de que no equivale a una aprobación Meta. No se envió.
- Al terminar se conservaron ejecuciones/versiones, se pausaron los ensayos, se revocó el consentimiento temporal y se dejó cupo 2 con campañas desactivadas.

## Evidencia y límites

[Registro completo](../../artifacts/live/p8-meta-acceptance-20261118.json). Nuevas pruebas: 53 backend y nueve de interfaz; catorce casos de guardas runtime usan SQL controlado y prohíben llamadas al proveedor. Cubren cambios de contexto/autoridad/consentimiento, plazo de reanudación y efectos inciertos/aceptados sin reenvío. No se presentan como casos externos adicionales.

Producción actual es PostgreSQL. Los criterios funcionales P8.1/P8.2/P8.3 ya aceptados en el ledger se conservan; la revisión actual cierra su dependencia real P4/P7 y añade evidencia operativa nueva. El recibo SQL2019 histórico no está presente en este checkout y no se reconstruye ni se declara reejecutado. No se ejecutaron preparadores, seeds ni calificadores históricos sobre bases pobladas.

No se hicieron campañas comerciales, inscripción académica, pruebas TikTok, revocación de secretos compartidos ni pérdida artificial de un POST aceptado. La prueba de A/B no demuestra eficacia comercial. TikTok sigue en P16; SIIE en P15. P11/P12 de puesta institucional conservan sus pendientes.

## Uso del módulo

Las plantillas CRM son mensajes de la ventana de atención; el catálogo oficial de WhatsApp y su aprobación pertenecen a Mensajería masiva. Activar un flujo no autoriza cualquier destinatario: preflight, consentimiento, control IA/Humano, versión y contexto se vuelven a comprobar. Para revertir, pausar y revisar las ejecuciones; restaurar una versión crea un borrador y exige nueva revisión antes de activar. Un efecto incierto conserva su historial y no se reenvía automáticamente.
