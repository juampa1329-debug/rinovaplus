# P4: comentarios, canales y webhooks en SQL Server 2019

Se publica la aplicación integrada en **http://127.0.0.1:4178/**, con la misma cuenta humana. La copia española P4 es `CBN_P4ES_TRIAL_20261026_a8ef717a`; conserva los 8 contactos, 8 conversaciones, 26 mensajes, 8 notas y 8 tareas ficticios anteriores. Añade tres comentarios ficticios y una cuenta de ejemplo pausada, marcada `synthetic_no_provider`. No contiene tokens de proveedor ni envíos demo pendientes. La versión anterior P3 conserva su base, perfil, imagen y contenedor detenido `crm-cbn-preview-p3-demo-preserved`.

## Alcance comprobado

- Comentarios: filtros y paginación SQL, estados, archivo/reapertura, conversión idempotente a CRM, vínculo a conversación, respuesta pública, Me gusta, vista de publicación y borrador IA solicitado por una persona. El autor de un comentario no se convierte en destinatario privado verificado. Los ejemplos se identifican como ficticios y bloquean efectos externos.
- Canales: se agrega y selecciona cada cuenta por separado, conservando el catálogo C10/P2 de 115 contextos de campos/salidas. Configuración, credenciales, diagnóstico, verificación, números WhatsApp, registro con PIN de seis dígitos, renovación, OAuth provisional, selección de activos, conexión/pausa y retiro/restauración tienen acciones propias. Los borradores de formulario sobreviven al guardado de credenciales y a la recarga de metadatos.
- Webhooks: la aplicación genera EndpointKey, ruta callback y verify token de una entrega. La URL completa se deriva de la base pública HTTPS configurada; sin dominio muestra la ruta y el requisito pendiente. El verify token no sustituye el App Secret real usado en HMAC Meta. Firmas sobre bytes originales, límites, JSON estricto, recibo cifrado, ACK después del commit, deduplicación y cuenta exacta preceden a la proyección.
- Transporte: una sola outbox C10 para conversación y respuesta pública. Actor/sesión/permisos/módulos/cuenta/identidad/ventana/cuotas se revisan antes de actuar. `accepted`, `sent`, `delivered`, `read` e `uncertain` son estados distintos. Un rechazo confirmado puede originar un nuevo intento explícito; un POST incierto no se reenvía. Las colas restauradas requieren una autorización humana vigente.
- Adjuntos: carga local y recepción vinculadas a cuenta, identidad, conversación y mensaje; inspección, tamaño máximo 5 MB, hash, descarga autenticada y volumen privado. El adaptador remoto conserva las restricciones TLS, DNS/IP fijadas y hosts aprobados. No hay referencia de descarga TikTok habilitada sin el contrato del producto correspondiente.
- IA de comentarios: requiere modelo/clave configurados, tarifa máxima declarada vigente y presupuesto. Reserva tokens/coste de manera conservadora, permite recuperar el resultado de una operación y nunca envía el borrador automáticamente. La calificación utilizó un gateway controlado sin gasto real.

## Capacidades por canal

| Canal/producto | Comentario público | Reacción | Mensaje privado | OAuth/configuración |
|---|---|---|---|---|
| WhatsApp Cloud | No aplica | No aplica | Sólo identidad de mensajería verificada y ventana vigente | Descubrimiento de WABA/números, validación de App ID/token, registro PIN, suscripción y OAuth preparados |
| Facebook Page | Respuesta pública | Me gusta/quitar Me gusta | Requiere cuenta Messenger, no la identidad del autor de comentario | Facebook Login y selección explícita de página |
| Instagram | Respuesta pública | Me gusta/quitar Me gusta cuando la API lo permite | Sólo identidad de mensajería y permisos reales | Facebook Login o Instagram Login, sin mezclar tokens/productos |
| Messenger | No es fuente de comentarios en esta UI | No aplica | Identidad de mensajería verificada | Página seleccionada de Facebook Login |
| TikTok Business | Condicionada a producto, permisos observados, revisión, rollout y cuota | No soportada | Condicionada a Business Messaging aprobado | Credenciales manuales y controles cerrados; OAuth/renovación del producto Business quedan pendientes |
| TikTok Login Kit | No habilita comentarios Business | No aplica | No habilita Business Messaging | Autenticación de identidad/renovación Login Kit; no implica permiso comercial |

La referencia Social inspeccionada no tiene una ruta de respuesta privada a comentarios. Las reacciones no se representan como ocho emojis arbitrarios. La conversión del módulo Ads tiene otros identificadores; P4 realiza una correspondencia explícita y no reutiliza sus IDs como si fueran comentarios C10. Estos límites son deliberados y comprobables en `artifacts/p4-es/reference-review.json`; 83 instancias de acciones no significan 83 operaciones únicas aceptadas.

## Evidencia y preservación

La extensión aditiva P4 tiene tres tablas, 147 totales y 117 mapeos, perfil/principal propios y diario independiente. Release SHA `fd247602e95f7756deb77c7a71dfd53bf4b18f56eb555c499c1cc69a8d438e5b`. Las 14 entradas congeladas P2 y las tres P3 permanecen inmutables. No hay DDL de arranque. TLS SQL sigue validado, sin `TrustServerCertificate`.

Los resultados ejecutados se guardan en `artifacts/p4-es/`: API26, comentarios/medios/IA23, recuperación de colas9, almacenamiento7, drift2 y límites Unicode3; la ampliación de eventos/medios conserva su propio resultado. Hay 170 pruebas backend focalizadas (incluidas 10 HTTP loopback del adaptador) y cuatro pruebas nuevas de UI. El navegador verificó 15 escenarios de la aplicación integrada. Los números son tamaños de suites/checks, no porcentajes de paridad ni acreditación del proveedor. La nota de conversión respeta las 2000 unidades UTF-16 del contrato P3, sin truncar el comentario original; el límite se comprobó con4002 emojis y replay.

La suite frontend completa obtuvo 299/306 aprobadas. Los siete fallos de agentes se reprodujeron con las fuentes exactas anteriores a P4: 8/15 aprobadas y los mismos siete fallos en tres archivos. Se documentan para P5; no se corrigieron cambiando las pruebas ni se atribuyen a la integración P4.

Se ensayaron tres fallos durables de migración, concurrencia COMMITTED/NOOP, drift aditivo rechazado, cuatro denegaciones SQL efectivas, restauración poblada, autenticación del vault restaurado, retiro de sesiones y copia de blobs comprobada por hash. El reinicio conserva las 142 tablas de negocio observadas; cinco tablas de sesión/rate/auditoría/operación se excluyen explícitamente por ser volátiles.

La fuente P3 conserva 107 tablas de negocio comparadas con el respaldo nativo fresco. Las 30 tablas académicas de esta copia española están vacías y coinciden entre respaldo, fuente y P4. Esto no afirma haber comparado de nuevo todas las filas de HORARIOSSIIE Windows ni todas las copias históricas: no se escribieron ni se redirigieron. Los grafos anteriores se preservan. La cadena PREVIEW→P3→P2→P1 se reproduce offline desde 1128 preimágenes públicas, con sus verificadores originales; se usa Linux para evitar el límite de rutas anidadas de Windows.

## Pendientes que impiden el 100%

No hay dominio ni aplicaciones Meta/TikTok. Falta registrar una URL pública HTTPS real, preparar el acceso humano bajo ese mismo origen con cookie Secure, configurar el proxy/allowlist del dominio, registrar los callbacks, obtener permisos/productos y verificar OAuth, números, adjuntos, entrega, recuperación e incertidumbre por canal con cuentas autorizadas reales. La receta local sólo publica 127.0.0.1 y no se declara un despliegue institucional de Internet. No basta exponer el puerto ni usar un túnel con la sesión de otro origen.

P4.3.m6/m7, P4.4.m4/m5 y P4.close.m5 conservan su pendiente. Los porcentajes se calculan con los 279 hitos y 56 criterios fijos, sin reescribir sus textos/pesos. P4.1 y P4.2 se aceptan en el alcance local descrito, con efectos de proveedor controlados; no aceptan cuentas externas.

## Operación y reversión

Arranque vigente: `docker compose -p crm-cbn-current-p4 -f compose.channels.yaml up -d --pull never`. Perfil privado en `.local/p4-es/final-runtime`, acceso en `.local/p4-es/ACCESS.txt`, volumen propio `crm-cbn-p4-media`. No ejecutar preparadores ni calificadores al arrancar o consultar memoria.

Antes de cualquier recuperación, pausar entradas/salidas desde Ajustes → Webhooks. Conservar recibos, eventos, cuotas, outbox, diario y volumen. Una restauración nativa usa otro destino/principal y mantiene el diario original; las sesiones copiadas se retiran. Revisar la incertidumbre antes de autorizar trabajo pendiente. Para volver a la UI P3: detener P4 y conservarla, iniciar `crm-cbn-preview-p3-demo-preserved` en 4178. No borrar la base P4, no cambiar tickets ni copiar sus filas/secretos sobre P3. La UI P3 no muestra los nuevos comentarios P4; restaurar posteriormente P4 conserva esos registros en su propia base.
