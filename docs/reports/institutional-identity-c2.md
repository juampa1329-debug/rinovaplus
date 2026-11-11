# C2 — Ficha institucional y candidatos de lectura

**2026-10-16 · adaptación funcional autorizada a SQL Server local.** Clientes y el mini CRM del Inbox comparten una ficha declarada por el operador y comparación con contactos CRM, aspirantes y estudiantes reales. Una coincidencia es un candidato para revisión: no confirma identidad, no fusiona, no copia datos ni vincula automáticamente registros SIIE. Migración 007 aplicada; SQL, frontend, runtime privado y navegador escritorio/móvil aceptados.

## Campos y autoridad

| Información | Fuente y contrato |
|---|---|
| Nombre visible histórico | `crm.Contact.Name`, sin partición ni inferencia de nombres/apellidos. |
| Nombres/apellidos informados | `crm_identity.Profile`: nombres hasta 100 caracteres y cada apellido hasta 30, editables y opcionales. No se completan a partir del nombre visible. |
| Documento informado | Tipo real desde `GETipoIdentidad` y número de hasta 16 caracteres como pareja. Es texto: conserva ceros, puntuación y caracteres que no sean espacios ASCII exteriores. |
| Correo informado | Campo CRM opcional de hasta 160 caracteres; no se trunca a los 50 del core para comparar. |
| Período al que aspira | ID opcional de `GEPeriodo`; no se asigna automáticamente el activo ni 2026-B. Programa de interés y ciudad conservan sus contratos actuales. |
| Registros institucionales | Aspirante por `Id_Aspirante`; estudiante por `Id_Estudiante`. Tipo/documento no son sus claves primarias. Cada resultado mantiene origen e ID independiente. |
| Períodos originales | Aspirantes: período aspirado y período de oferta separados. Estudiantes: período de oferta. No se reinterpretan como matrícula o identidad confirmada. |
| Evaluación/contexto IA | Continúan como derivados de lectura. La ficha nueva no se incorpora al paquete saliente de R4; sus identificadores conocidos se usan únicamente para reforzar la redacción local, incluidas partes del nombre. |

El perfil tiene una FK exclusivamente hacia `crm.Contact`; no crea relaciones ni escrituras sobre estudiantes, aspirantes u otros catálogos core. Empieza vacío: los dos contactos existentes conservan `institutionalProfile: null` hasta que exista información confirmada por un operador.

## Consulta y guardado

- `GET /api/local/crm/identity/catalog`: tipos de documento y períodos reales; sin semillas ni escrituras.
- `POST /api/local/crm/identity/candidates`: consulta de lectura con criterios en el cuerpo para evitar nombres/documentos en URL. Respuesta `no-store`, errores saneados y límite de 25 resultados más `hasMore`.
- **Coincidencias de identidad:** documento con tipo exacto, correo con espacios ASCII exteriores y mayúsculas normalizados, o teléfono principal/alternativo exacto con espacios ASCII exteriores eliminados. No se agrega país ni se compara solo un sufijo. Se recorren todos los períodos y programas para no ocultar posibles duplicados históricos.
- **Exploración por nombre:** desde tres caracteres, con fuente y período/programa reales opcionales. El patrón escapa `%`, `_` y `[`; no interpreta comodines del usuario. El filtro de período respeta la fuente indicada en la tabla anterior.
- La paginación se aplica después de combinar las fuentes; orden estable por motivos, fuente e ID. No existe un corte previo por fuente que pierda resultados. El contacto propio se excluye mediante UUID; criterios vacíos o insuficientes no abren una consulta general.
- Perfil y ficha usan la misma mutación de contacto, revisión, bloqueo transaccional y `crm.Operation`. Revisiones obsoletas y reutilización de operación con contenido distinto devuelven 409; el reintento idéntico tiene un efecto.
- Payloads antiguos con perfil omitido o `null` conservan el perfil guardado y el hash idempotente anterior exacto. Solo se excluye ese campo nuevo cuando está ausente/nulo; se conservan los demás valores nulos del contrato anterior.

En **Ficha institucional informada**, editar datos declarados y guardar con la acción existente de ficha local. En **Posibles duplicados y registros institucionales**, expandir la comparación, elegir modo/fuente y usar **Comparar datos**. La comparación muestra también teléfono alternativo y período original de oferta; sus datos no son editables. **Abrir conversación existente** está disponible únicamente para candidatos CRM y usa la navegación vigente. No hay acción de «usar estudiante», copiar o fusionar.

La búsqueda espera 300 ms, cancela solicitudes anteriores y descarta respuestas obsoletas. Los campos y criterios permanecen en los borradores RAM de la pestaña al navegar entre Clientes e Inbox; recargar los descarta. Los errores de catálogo/consulta conservan el borrador y ofrecen reintentar, sin fallback demo.

## Evidencia por capa

Resultados saneados en `.local/c2-identity-20261016/`; solo checks, recuentos, tiempos y hashes, sin nombres, documentos, correos ni mensajes.

- Respaldo nuevo COPY_ONLY/CHECKSUM, restauración independiente y CHECKDB aprobados antes de aplicar 007. Fallo anterior a COMMIT revirtió el esquema; repetición fue idempotente y drift deliberado se rechazó en la restauración.
- Una tabla `crm_identity.Profile` vacía creada explícitamente. Metadata core y filas previas de CRM, configuración, Admisiones, R2, R3A y R4 intactas; cuatro auditorías automáticas del trigger DDL conservadas. No hubo escrituras de negocio core.
- **20 comprobaciones SQL de repositorio:** seis tipos de documento reales; períodos SIIE; ceros/puntuación; exclusión propia; dos páginas reales de 25 con `hasMore=true` sin solapamiento; filtro real 2026-B; ausencia de escrituras en todas las lecturas.
- Persistencia de valores nuevos, lectura mediante conexión nueva, replay, 409, omisión heredada y rollback completo ante catálogo inválido demostrados **solo en la restauración independiente**. El adaptador de prueba fija y verifica ese destino; la API productiva local conserva su guard de destino DBSIIE. Las dos fichas reales permanecen vacías, sin identidad de estudiante ajeno asignada.
- Tiempos del último arnés: 1422–1578 ms por comparación, incluyendo apertura y verificación Windows de la conexión; no son latencias SQL puras. Primeras dos páginas por nombre devolvieron 25 registros y `hasMore=true`; documento con ceros y documento con puntuación devolvieron un candidato cada uno.
- Frontend: formato, lint, tipos, **190 pruebas en 29 archivos** y build aprobados. Cuatro pruebas focales verifican nombres independientes, período no inferido, guardado por mutación existente, borradores compartidos, cancelación y respuestas obsoletas, comparación de lectura y teléfono alternativo. Detector mecánico de interfaz sin hallazgos; no sustituye aceptación visual.
- Backend: lint, formato y exportación canónica de contratos comprobados. Corrida amplia desde `backend`: **1690 aprobadas y un fallo del nuevo arnés HTTP**; después de corregir ese arnés, **23/23 del módulo C2 aprobadas**. No se suman ambos recuentos como pruebas distintas ni se afirma una segunda corrida completa. Dos warnings preexistentes del test de filtros corresponden a workers contra el doble SQL bloqueado; no hubo IO externo.
- Preview privado `127.0.0.1:4173`: imagen `b73858456ded1d5269bb4e69a071e69b4bc2e9f1413c030cef52530ef97a98d8`, saludable; **siete comprobaciones de recreación y 19 HTTP** aprobadas. Snapshot CRM compatible conservado (campo nuevo nulo), volumen IA idéntico, configuración C1 revisión 3, miembros reales y R3A/R4 intactos. Consulta HTTP real de documento con ceros: **219 ms**, un candidato y `hasMore=false`. Ninguna llamada a proveedores.

Los primeros fallos frontend correspondieron a invocaciones del arnés (etiqueta de botón, evento `toggle` y matcher HTML incompleto); se corrigieron y la ejecución final pasó. El arnés backend suponía host `testserver` y que `create_app` recibía Settings; el guard rechazó primero el host y luego el modo. Se ajustaron URL loopback y `app.state.settings` al patrón vigente de pruebas Inbox. Lint detectó ausencia de `cause` en un error capturado; se conservó la causa sin cambiar el mensaje saneado. No se atribuyen esos fallos a una pérdida de datos o al repositorio SQL.

## Operación y reversión

007 no se ejecuta al iniciar ni desde un GET. Si el esquema no existe, la lectura anterior de Clientes/Inbox continúa disponible y un nuevo guardado con perfil explícito o búsqueda institucional devuelve indisponibilidad acotada. Si hay un esquema reconocido con drift se rechaza su uso. Un catálogo inexistente se rechaza en el mismo commit de contacto: ninguna edición parcial queda confirmada.

Para revertir el runtime, conservar la imagen anterior y el esquema nuevo con sus datos; una versión previa omite el perfil y no lo borra. No hay DROP ni limpieza automática. Recuperación completa mediante el respaldo/restauración ensayados, con decisión operativa explícita. No se transfiere credencial Gemini, activa proveedor, cambia outbound, publica Git ni habilita producción.

## Aceptación de navegador

Evidencia leída del coordinador: `.local/c2-identity-20261016/cua-result.json`, estado `passed`; capturas `institutional-profile.png` y `mobile-profile.png` verificadas por el coordinador sin datos personales. Comprobó la misma imagen final en escritorio 1440×1000 y móvil 390×844. No encontró defectos funcionales ni se necesitó una corrección de fuente o reconstrucción adicional; el único ajuste fue usar viewport completo porque el arnés de captura no respetaba el origen del recorte:

- Clientes y mini CRM cargan seis tipos de documento, 32 períodos y 228 programas reales. No se infiere el período ni el nombre estructurado.
- AJAX por nombre devuelve páginas de 25 estudiantes y 25 aspirantes reales; el filtro 2026-B responde. La comparación conserva origen/ID, teléfono alternativo y período de oferta, sin inputs editables.
- Un borrador institucional permanece compartido entre Clientes e Inbox y se descarta explícitamente; no se guardó una identidad ajena ni se publicó información fabricada.
- Scroll derecho de 2065 a 2415 sin desplazar página, lista ni mensajes, que quedaron en 0. En móvil, panel de 358 px con scroll propio y sin desbordamiento horizontal. Contexto IA conserva lectura independiente.
- Cero mutaciones de negocio en navegador y cero llamadas a proveedores. La aceptación visual no se presenta como prueba de persistencia de una identidad real: esa escritura se comprobó únicamente en restauración independiente.

## Fases siguientes

La secuencia C1–C5 complementa R0–R9, sin renumerarlos:

| Corte | Resultado y aceptación | Estado |
|---|---|---|
| C1 | Configuración SQL, campos compartidos y mini CRM; preservación y navegador escritorio/móvil. | Aplicado y aceptado previamente. |
| C2 | Ficha declarada y candidatos de lectura en Clientes/Inbox; persistencia aislada, compatibilidad y aceptación real. | Aplicado y aceptado en SQL, frontend, runtime privado y navegador escritorio/móvil. |
| C3 | Actividad deduplicada con cursor estable y métricas del contacto completo; sin DDL ni historial de campos inventado. | [SQL/frontend/runtime privado/navegador aceptados](contact-activity-c3.md). |
| C4 | Fusión conservadora y reversible con preflight, elección humana de campos, alias/origen y reversión probada. No fusionar estudiantes automáticamente. | Pendiente de contrato específico. |
| C5 | Canales/outbox R3B, activación R4, banco de agentes R5 y predicción/aprendizaje R6/R7 con puertas independientes. | Pendiente; este corte no activa ejecución ni envíos. |

Edición avanzada/reordenación del catálogo C1, autenticación/RBAC compartidos, alta académica y escrituras SIIE mantienen sus pendientes independientes. No se presentan como implementadas las 35 rutas del CRM de referencia.
