# Fases adicionales pendientes

Corte: 20 de noviembre de 2026. El roadmap original P0–P11 está aceptado al 100% en sus alcances documentados; P12 auxiliar de puesta online está aceptada para PostgreSQL/Meta. Las fases siguientes tienen seguimiento propio y no aportan peso a los 56 criterios originales. P16 ya tiene despliegue y pruebas reales de clave única, aspirantes y estudiantes; la primera página de 25 programas ya se copió localmente; el detalle financiero sigue bloqueado por el productor. La evidencia del18-11 se conserva como historia.

| Fase | De qué trata | Estado |
|---|---|---|
| P13 · Académico y agentes de venta por programa | Fichas por escuela, 34 guías nativas de ventas, prompts, memoria/grafo y calificación con evidencia. | En validación, 0/4 aceptadas. Retoma real de Software pasó: especialista correcto, cuatro semestres, nombre, ciudad y objetivo de emprendimiento conservados. Ajuste de referencias genéricas publicado y comprobado en el grafo; 264 pruebas backend. Chat de prueba en Humano; falta una entrada nueva para certificar silencio. Pipeline de nueve etapas creado; traspasos de agentes/modelos por etapa diferidos a P22. Inglés sin tarifa confirmada; SLA sin umbral. Evidencia: artifacts/live/p13-close-review-20261120.json. |
| P14 · Entrenamiento y mejora del agente de ventas | Definir datos y evaluación para mejorar orientación comercial a partir del comportamiento de clientes; concretar un plan medible. | Plan pendiente; no se acredita una red neuronal nueva ni eficacia institucional. |
| P15 · Correos y notificaciones | Recuperación/invitaciones, destinatarios y preferencias por evento, alertas, informes y plantillas HTML con logos y firmas visuales. | Aceptada en alcance inicial, 7/7 (100%). Informes de auditoría y recibos manuales; monitor automático de respaldos sigue OPS-05. |
| P16 · Integración SIIE | Programas/ofertas y planes financieros; aspirantes, estudiantes y matrículas con contactos nativos. | Parcial, 0/5. Clave única, dos páginas de25aspirantes y8estudiantes comprobados. Alcance actualizado por el propietario: período no obligatorio para catálogo base y fechas financieras opcionales. Copia local de25programas verificada. Ajustes manuales, botón por ficha, reporte de faltantes y rediseño en validación; detalle financiero aún pendiente. Los503 de Offer sin datos parciales conservan su evidencia y deben volver a consultarse. |
| P17 · TikTok | Conexión y automatizaciones permitidas por la API, con cuenta y pruebas reales propias. | Diferida por el propietario, 0/5. |
| P18 · Seguridad y ciberseguridad | Tokens/sesiones, límites por IP y cuenta, 2FA, CAPTCHA, inyecciones, infraestructura y respuesta a incidentes. | Planificada, 0/8; controles previos conservados, auditoría integral pendiente. |
| [P19 · Voces y notas de audio](P19_VOICES_AUDIO.md) | ElevenLabs, voces por escuela/agente, generación contextual y notas compatibles con WhatsApp; ampliación de ambiente y tecleo. | Alcance técnico inicial aceptado, 5/5. Faders, ducking y generador de muestras aceptados. El propietario rechazó las pistas sintéticas y también las sustitutas CC0 grabadas por sonar artificiales. Propone aportar sus propias grabaciones; archivos y nueva escucha pendientes. Preview de Juampa de 12,2465 s con oficina 60%/tecleo 40%, sin guardar ni enviar; contador 6.761 sin incremento, política vigente 23 conservada. No declarar aceptada la ampliación sonora. |
| [P20 · Llamadas de WhatsApp y agentes de voz](P20_WHATSAPP_CALLS.md) | Número colombiano institucional, entrantes/salientes, seguimiento con contexto CRM, tomar/transferir y escuchar en vivo por un recorrido compatible. | Planificada, 0/8; implementación 0%. Cuenta/ruteo, audio en vivo, transferencia y coste pendientes de validar; sin exigir Twilio ni otro número. |
| [P21 · Catálogos y respaldo de modelos de lenguaje](P21_LANGUAGE_RESILIENCE.md) | Catálogo por empresa/familia, pruebas aisladas y alternativas compatibles cuando un proveedor rechaza la consulta. | Nuevamente diferida por el propietario hasta nueva confirmación, 0/4 aceptadas. Tras confirmar saldo se inició un ensayo: 503 privado simulado → GPT-4.1 mini real respondió, una consulta, 2739/173 tokens. Contexto conservado y recuperación GET sin otro POST. Gemini y configuración intactos; cero mensajes/CRM. Reserva USD0,006314, no factura. Falta ensayo público429; no ejecutarlo durante la pausa. Históricos402/429 conservados. |
| [P22 · Pruebas de modelos candidatos](P22_MODEL_CANDIDATES.md) | Comparar Gemini actual, Sonnet 4.6, Haiku 4.5 y GPT-4.1 mini con las mismas skills, fichas, memoria y casos de venta; decidir por función y etapa. | Planificada por el propietario, 0/5. Candidatos y rúbrica preparados. Sin ensayos pagados ni modelos activos cambiados; depende de la recarga de OpenRouter y de validar los traspasos del pipeline. |

Además siguen abiertas OPS-01–OPS-06: copia externa, custodia independiente de clave, RPO/RTO, retención/espacio, alertas entregadas y conciliación adicional DB/archivos. Se registran en `tasks/operations-hardening-backlog.json`; fueron aceptadas como límites del alcance actual y no se declaran implementadas.

### Revisión de audio y agentes del 20-11-2026

La muestra de pistas grabadas CC0 también fue rechazada por el propietario.
No se guardaron sus niveles; se esperan las grabaciones propias propuestas.
La carga de pistas personales desde el frontend no está implementada todavía.
P13 continúa con pruebas reales, sin aceptación por el mero despliegue.
El plazo institucional de SLA aparece sin configurar: no se inventó un umbral.

### OpenRouter — 20-11-2026

Clave guardada directamente por el propietario y catálogo autenticado cargado:
408 modelos de texto antes del filtro interactivo. Empresas y familias funcionan.
Se corrige la oferta de variantes batch/no-chat para evitar elecciones incompatibles.
Actualización: Gemma4 26B gratuito respondió en el simulador. Se guardó como selección de OpenRouter y respaldo institucional autorizado; Gemini permanece principal.
Conectar este proveedor no cierra la validación comercial de P13 ni las demás fases.
