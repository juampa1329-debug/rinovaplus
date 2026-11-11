# Documento de Arquitectura y Especificaciones Técnicas - CRM SIIEWEBPLUS

> **Aclaración de línea base — 2026-10-13 (America/Bogota):** el propietario confirmó una plataforma nueva con FastAPI, React y Celery/Redis integrada con la base **SQL Server existente del SIIE**, sin una DB de negocio aislada. Este documento conserva los requisitos de origen, pero no autoriza escrituras, despliegues ni proveedores. Las [reglas](docs/development-rules.md), [arquitectura propuesta](docs/architecture.md), [fases](docs/roadmap.md) y [pendientes](docs/pending.md) precisan su diseño seguro. Capacidades/tiempos de Meta, precios/free tiers, audio y versión/esquema SQL Server necesitan evidencia antes de implementación.

## 1. Contexto y Objetivo
Desarrollo de un CRM avanzado para una entidad de formación para el trabajo. El sistema gestionará el ciclo de vida del estudiante (captación, retención, relacionamiento corporativo). El enfoque inicial es la automatización asistida del área de admisiones mediante un bot de WhatsApp impulsado por IA, con control humano efectivo. Se conserva la intención de comunicación natural del concepto original “Asesor Fantasma”, pero la IA se identificará transparentemente como asistente virtual; no se implementará suplantación oculta de un humano.

## 2. Stack Tecnológico
*   **Backend:** Python (FastAPI).
*   **Frontend:** React.
*   **Base de Datos:** SQL Server existente del SIIE como SSOT transaccional. La propuesta original de PostgreSQL/`pgvector` queda sustituida: `pgvector` es una extensión PostgreSQL, no aplicable directamente a SQL Server; memoria semántica diferida a decisión técnica verificada.
*   **Asincronismo y Colas:** Celery + Redis; recepción durable y respuesta rápida. Los límites de tiempo/reintentos de Meta se verificarán contra el contrato vigente, sin asumir aquí una regla probada de 3 segundos.
*   **IA (Desarrollo):** OpenRouter y ElevenLabs son candidatos del documento original; modelos, capacidades, condiciones, coste y tratamiento de datos pendientes de aprobación. No se garantiza un free tier.
*   **Infraestructura:** Integración directa por Webhooks de Meta (WhatsApp Cloud API - Sandbox).

## 3. Arquitectura de Base de Datos (SSOT - Single Source of Truth)
*   **Regla de Oro:** NO se creará una base de datos aislada para el CRM. El backend de Python se conectará a la base de datos transaccional actual del SIIE.
*   **Nuevas Tablas Propuestas (Prefijo CRM_):** `CRM_Prospectos`, `CRM_Sesiones_WA`, `CRM_Mensajes`, `CRM_Parametros_Globales`, `CRM_Notas_Transicion`, `CRM_Formularios`. Son nombres conceptuales, no esquema existente comprobado ni DDL autorizado; diseño/migraciones requieren revisión DBA y prueba no productiva.
*   **Integración:** La intención de registrar cierres en el core SIIE requiere contratos controlados y probados, revisión DBA y autorización explícita de escritura. Los ejemplos Estudiantes/Matrículas no son esquema comprobado. No ejecutar `INSERT`/`UPDATE`, DDL ni migraciones productivas por la existencia de este requisito.

## 4. Núcleo del Bot de WhatsApp (Motor de Admisiones)

### 4.1. Recepción y Asincronismo (FastAPI + Celery)
*   FastAPI valida firma/payload y persiste una inbox durable idempotente antes de confirmar recepción; Celery/Redis ejecuta tareas sin convertirse en SSOT. Contrato de respuesta/reintento de Meta pendiente de validación.
*   Un *worker* de Celery procesa el mensaje, llama a los LLMs, ejecuta la lógica y envía la respuesta.

### 4.2. Algoritmo de Humanización (Demora Dinámica)
Las demoras siguientes son propuestas de origen pendientes de aprobación de servicio/UX y validación Meta. Se implementarán como trabajos programados persistidos y cancelables, nunca `sleep` bloqueando workers; calendario, zona y baja se validan antes del envío.
*   **Primer mensaje (Horario laboral):** Demora aleatoria entre 2 y 10 minutos (120 - 600 seg).
*   **Primer mensaje (Fuera de horario):** Se encola para el siguiente día hábil a las 8:05 AM.
*   **Interacciones continuas:** 
    *   Si el cliente responde en < 30s: Demora de 5 a 15s.
    *   Si el cliente tarda > 5m: Demora de 60 a 90s.
*   **Indicador de escritura:** Intención de origen pendiente de comprobar capacidades, endpoint y restricciones actuales de WhatsApp. No asumir `typing_on` o un intervalo de 3 segundos como API comprobada.

### 4.3. Reglas de Negocio Estrictas (System Prompt)
*   **Horarios Académicos:** PROHIBIDO dar horarios exactos de clases. Solo se deben ofrecer las *Jornadas* (ej. Diurna, Nocturna, Sabatina) obtenidas de la DB.
*   **Horarios Administrativos:** La IA debe leer la tabla `CRM_Parametros_Globales` para informar sobre horarios de atención en sede.
*   **Voz y Audio:** La IA puede generar notas de voz (máx. 10 segundos). Debe encerrar el texto en etiquetas `<audio>texto</audio>`.

### 4.4. Procesamiento de Notas de Voz
*   El backend detecta la etiqueta `<audio>`, extrae el texto, llama a la API de ElevenLabs.
*   **Requisito Técnico:** Obtener `.ogg` con códec `opus` para nota de voz nativa; verificar formatos reales del proveedor/API y reproducir en dispositivo antes de declararlo funcional. `pydub`/`FFmpeg` son herramientas candidatas, no dependencias aprobadas o instaladas.

## 5. Módulo de Cierre (Formularios e Integración)
*   **Flujo de Cierre:** La IA NO pide datos campo por campo. Cuando detecta intención de compra, Python genera un token único.
*   **Enlace:** La IA envía un link parametrizado (ej. `https://crm.../formulario/token-abc-123`).
*   **Frontend (React):** Muestra el formulario al aspirante. Backend valida token criptográfico de un uso, vencimiento y datos; registra prospecto bajo contrato autorizado. Envío de formulario no equivale a aceptación o matrícula, que requieren revisión/contrato core.
*   **Recordatorios:** Intención original a las 2 horas y para chats inactivos de 24h/48h. Se mantiene diferida hasta verificar consentimiento, opt-out y ventana/plantillas de recontacto vigentes de Meta; no ejecutar por defecto.

## 6. Handoff y Asistencia Humana
*   **Detonantes:** Usuario pide un humano, o la IA detecta sentimiento negativo/frustración. El estado pasa a `Requires_Human`.
*   **Resumen IA:** Python genera un resumen de 3 líneas del chat y lo guarda en `CRM_Notas_Transicion`.
*   **Dashboard React:** El asesor ve el resumen de la IA + la data del SIIE en una sola pantalla. Tiene botones para "Forzar Control" (bloquea IA) y "Regresar a IA" (le inyecta contexto del humano).

## 7. Motor de Ventas y Perfilamiento (IA Avanzada)
*   **Identidad IA (React):** Panel para configurar el System Prompt dinámicamente con sliders (Formalidad, Empatía, Emojis, Jerga) y directrices de venta (ej. Método SPIN).
*   **Memoria de argumentos exitosos (vectorización pendiente):** Propuesta avanzada diferida; no usar `pgvector` directamente sobre SQL Server. Requiere decisión de capacidades, minimización, consentimiento y retención antes de perfilar o guardar transcripciones.
    1. La IA perfila la personalidad del usuario en tiempo real (ej. Analítico, Impulsivo).
    2. Al cerrar una venta, la transcripción completa se vectoriza y se etiqueta.
    3. Para nuevos usuarios, la IA hace RAG buscando cierres exitosos previos con perfiles similares para reutilizar argumentos de venta.
*   **RAG de Conocimiento:** Propuesta de índice derivado de pénsums/precios/programas con lecturas controladas SIIE; frecuencia, necesidad, versión/capacidades y solución pendientes. SIIE sigue siendo la autoridad; no asumir un script/vector store ya implementado.

## 8. Infraestructura de Producción (Failover System)
*   **Gestor en React:** UI propuesta para priorizar proveedores; secretos en almacén seguro o cifrado controlado con llaves separadas. DB solo conserva referencias/ciphertext autorizado, nunca llaves en texto plano.
*   **Fallback en Python:** Política propuesta de timeout/reintento/backoff y proveedor alterno por la misma capacidad (LLM a LLM, TTS a TTS); verificar capacidades y coste. No asumir Anthropic como TTS ni 5s como umbral aprobado.
*   **Alerta:** Se envía notificación de fallo al Dashboard de React, sin que el cliente final lo perciba.

## 9. Fases de Desarrollo Sugeridas para el Agente (Codex)
La secuencia siguiente es el planteamiento histórico, no autorización de ejecución. La [hoja de ruta vigente propuesta](docs/roadmap.md) añade evidencia/diseño antes del scaffold, un corte vertical sandbox, validación de seguridad y puertas separadas de escritura/piloto.
1.  **Fase 1: Configuración Core DB y Backend.** Levantar FastAPI, configurar SQLAlchemy para conectar a la DB existente del SIIE y estructurar modelos para tablas `CRM_`.
2.  **Fase 2: Arquitectura Asíncrona Webhook.** Integrar Redis + Celery, inbox/outbox durable y endpoint GET/POST verificado para Meta; demoras mediante scheduling persistido, sin `sleep` de workers.
3.  **Fase 3: Motor IA Textual y RAG.** Conectar OpenRouter, programar el System Prompt dinámico según jornada y configurar RAG sobre las tablas del SIIE.
4.  **Fase 4: Pipeline de Audio y Failover.** Integrar ElevenLabs, implementar conversión OGG/Opus y codificar el sistema de Fallback en cascada.
5.  **Fase 5: Formularios y Dashboard React.** Crear el UI del bot, visor de resumen de handoff y los formularios de cierre parametrizados por token.
6.  **Fase 6: Memoria Vectorial de Ventas.** Propuesta diferida: resolver alternativa compatible con SQL Server y gobernanza de datos antes de perfilamiento/búsqueda de similitud; no integrar `pgvector` como si fuera extensión SQL Server.
