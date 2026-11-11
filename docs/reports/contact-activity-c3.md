# C3 — Actividad real y métricas por contacto

**2026-10-16 · aplicado y aceptado en SQL de lectura, frontend, preview privado y navegador escritorio/móvil.** Clientes y el mini CRM del Inbox comparten actividad paginada y métricas del contacto seleccionado. El corte reutiliza registros existentes: no modifica el esquema, no crea un nuevo historial artificial y no ejecuta IA ni envíos.

## Qué muestra

| Fuente | Interpretación permitida |
|---|---|
| `crm.Operation` | Creación de contacto, confirmación de ficha y operaciones de conversación. `edit_contact` incluye también el perfil C2; una confirmación puede ser equivalente al valor anterior. |
| `crm.Message` | Registro entrante/saliente local, fecha e ID; sin cuerpo del mensaje. Un registro saliente no acredita entrega externa. |
| `crm_inbox.Operation` | Creación/confirmación de tareas y confirmación de responsables vinculadas a esa conversación. No atribuir al pasado el título, estado o responsable actual. |
| Actor guardado | Etiqueta `local-operator`, no identidad autenticada del empleado que ejecutó la acción. Para mensajes no se inventa autor. |

La operación `add_message` se sustituye por el mensaje real solo si ese mensaje existe dentro del mismo corte de paginación. La confirmación de asignación registrada en dos esquemas se muestra una sola vez, priorizando R2 únicamente si su registro existe dentro del corte. Se conservan operaciones válidas cuando falta esa fuente primaria; no se aplica una supresión indiscriminada.

No se exponen cuerpos, títulos de tareas, hashes de payload, respuestas técnicas, tokens ni credenciales. Operaciones globales de configuración/equipo/agentes y referencias/preparaciones R3A quedan fuera del historial del contacto. `CapturedAt`/`PreparedAt` de R3A reflejan backfill/procesamiento técnico; no se usan como hora de interacción o latencia de respuesta.

Las fuentes anteriores no guardan valores previos/posteriores de etapa, perfil, estado o responsables. C3 muestra la acción registrada con esa limitación; no reconstruye diferencias. Tampoco incorpora seguimiento SIIE por coincidencia documental: C2 no creó un vínculo confirmado entre contacto y aspirante/estudiante.

## Consulta y navegación

`GET /api/local/crm/clients/{contactId}/activity` requiere el encabezado local y responde `no-store`. No hay endpoint de escritura ni migración C3. La lectura utiliza la transacción/bloqueo compartido y guard de copia local vigentes.

- Inicio con toda la actividad disponible del contacto. Filtros opcionales por clase y fechas; no se filtra el pasado por etapa, programa o responsable actuales.
- Fechas de filtro en Bogotá: inicio inclusivo a las 00:00, final inclusivo para el usuario y límite SQL exclusivo a las 00:00 del día siguiente, convertidos explícitamente a UTC. Rangos inválidos se rechazan.
- Página de 25, `hasMore` y cursor validado ligado al contacto/filtros. Orden estable descendente por fecha, luego fuente y UUID con comparación BIN2. El cursor conserva fecha SQL con siete decimales y límites superiores de revisiones/secuencia; las inserciones posteriores aparecen al actualizar el historial reciente.
- La serialización SQL conserva fracción cero y 100 ns sin pasar por el `datetime` de seis decimales de pyodbc. El cursor es opaco para la UI, no firmado y no constituye autorización; tipos, límites, alcance y formato se validan antes de SQL parametrizado.
- Búsqueda de filtros con espera de 300 ms, cancelación y descarte de respuestas obsoletas. Filtros RAM compartidos entre Clientes e Inbox, sin modificar borradores de ficha/mensajes.

En ambas vistas, abrir **Actividad y métricas del contacto**. **Actualizar actividad reciente** vuelve a la primera página y consulta SQL; **Limpiar filtros de actividad** recupera el alcance completo. La paginación permite **Actividad anterior** y **Actividad más reciente**. Fechas visibles en America/Bogota; API explícita en UTC.

## Métricas y denominadores

**Alcance fijo:** contacto seleccionado completo, todos sus mensajes disponibles y estado actual de sus tareas; independiente de clase, fechas o página del historial. `calculatedAt` procede del servidor SQL. La UI conserva la última medición válida del mismo contacto durante carga, error o fecha inválida, mostrando su hora; nunca conserva métricas de otro contacto.

| Dato | Fórmula/fuente y ausencia |
|---|---|
| Mensajes registrados | `COUNT_BIG` sobre todos los mensajes de su conversación. Entrantes/salientes según `Direction`; no entrega, lectura ni engagement inferidos. |
| Último mensaje | Máximo `CreatedAt` entre esos mensajes. Sin mensajes: ausencia explícita. |
| Tareas actuales | Conteo por `pending`, `completed`, `cancelled`, sin depender de la página de tareas. Vencidas = pendientes con `DueAt <=` hora UTC del servidor. Sin filas: cero tareas, no tasa de éxito. |
| SLA próxima respuesta local | Misma semántica R2: entrada pendiente posterior al último registro saliente, umbral explícito y tiempo corrido 24/7. No acredita respuesta externa ni calendario hábil. Política ausente: no configurado; sin entrada pendiente: sin medición. |
| Tiempo de respuesta | No medido en C3. Sin entradas se muestra no disponible, nunca 0 ms ni 0 % de salud. |

Si R2 no está instalado, sus tareas/SLA se informan como no disponibles y se conservan las fuentes CRM/mensajes. Un esquema existente alterado se rechaza mediante su guard. No hay probabilidades, riesgo de abandono, conversión ni predicciones fabricadas.

## Evidencia y preservación

Evidencia saneada en `.local/c3-activity-20261016/`: solo comprobaciones, recuentos, tiempos y hashes; sin datos personales. El conjunto vivo conservó dos contactos, dos conversaciones, dos mensajes salientes y 13 operaciones CRM. No hay entradas, tareas, asignaciones ni política SLA que justifiquen llenar métricas por apariencia.

- **24 comprobaciones SQL** aprobadas: 13 actividades únicas reales —seis y siete por contacto—, filtrado sin cambiar métricas, aislamiento y ausencia de payloads privados. Lecturas reales de 203/141 ms en el último arnés.
- Empates, fila 25 con fracción cero, orden a 100 ns, 50 registros sin pérdida/duplicación tras inserción posterior, límites de día Bogotá, deduplicación/fallback, tareas/SLA y cursor ajeno se comprobaron **solo mediante rollback en la restauración independiente C2**. Ningún fixture se insertó en la copia viva. Hashes de todas las filas CRM/C1/C2/Admisiones/R2/R3A/R4 intactos; cero escrituras vivas.
- Un SELECT literal confirmó que estilo126 omite la fracción cuando es cero; se corrigió mediante serialización SQL determinista con siete decimales. El primer ensayo encontró una aserción del arnés que buscaba una asignación en una página ocupada por 50 mensajes posteriores; se corrigió su filtro y se confirmó rollback/preservación. No fue un defecto de datos o del lector.
- Backend: **82 pruebas focales** de C3/Inbox/R2/C2/transacciones, lint, formato y exportación canónica aprobados. No se repitió la suite completa anterior sin cambios aplicables.
- Frontend: formato, lint, tipos, **194 pruebas en 30 archivos** y build aprobados. Cuatro pruebas C3 cubren métricas conservadas durante filtros/errores/fechas inválidas, aislamiento por contacto, AJAX obsoleto, cursor, N/A y borrador compartido. Detector mecánico sin hallazgos. El primer gate de formato se detuvo en el JSON recién exportado; normalizado antes de la corrida final.
- Build con aviso informativo por chunk principal de aproximadamente 508 kB. No se alteró la carga de rutas ni el estilo global como parte de este corte.
- Preview privado saludable `127.0.0.1:4173`, imagen `44cd1cf6d6b817299d85c5ada4e1e6e6a43634a727352ae7e5b413e7b95f2f67`: **siete comprobaciones de recreación y 31 HTTP** aprobadas. GET de actividad real: 234/219 ms. Snapshot, volumen IA, C1 revisión 3, perfiles C2 vacíos, equipo de Admisiones y R3A/R4 conservados. R4 sin política, sin llamadas y outbound bloqueado; configuración privada intacta.

No se ejecutaron DDL, nueva migración, backup innecesario, core writes, transferencia de credencial, proveedor, commit/push ni publicación. Para revertir la UI/API, reutilizar la imagen C2 anterior; no hay datos/esquema C3 que contraer. El corte no ejecuta ni modifica el CRM SaaS importado.

## Aceptación de navegador

Evidencia del coordinador leída: `.local/c3-activity-20261016/cua-result.json`, estado `passed`; capturas `activity-desktop.png` y `activity-mobile.png` inspeccionadas por el coordinador sin datos personales. La misma imagen final se comprobó en escritorio 1440×1000 y móvil 390×844, sin defecto de producto ni corrección adicional de fuente:

- Inbox y Clientes muestran seis/siete registros reales según el contacto. Filtrar mensajes reduce el historial a una entrada y mantiene las métricas completas.
- Fecha futura devuelve vacío explícito; rango inválido muestra aviso y conserva métricas y borradores. Durante el cambio de contacto no aparecen métricas del contacto anterior; después carga su historial de siete entradas.
- Un borrador temporal C2 se descarta sin guardar y el perfil continúa vacío. Contexto IA permanece de lectura.
- Scroll CRM de 1412 a 1062 con página, lista y mensajes en 0. Panel móvil de 358 px con scroll propio; sin desbordamiento horizontal en ambos tamaños.
- La paginación de más de 25 filas se acredita mediante el ensayo SQL en restauración; no se presenta como paginación visual de un conjunto real que solo contiene seis/siete entradas por contacto.

El arnés de navegador necesitó confirmar las fechas mediante eventos nativos porque el llenado inicial solo modificaba el DOM; la prueba final sí comprobó vacío y rango inválido. No se modificó el producto para resolverlo. Pestaña del propietario intacta, viewport restaurado y ninguna mutación de negocio guardada.

## Fases y siguiente entrega

| Corte | Estado y siguiente aceptación |
|---|---|
| C1 · Configuración y mini CRM | Aplicado y aceptado; edición avanzada/reordenación del catálogo mantiene su pendiente. |
| C2 · Ficha y candidatos de lectura | Aplicado y aceptado; ninguna fusión o vinculación académica automática. |
| C3 · Actividad y métricas | Aplicado y aceptado en SQL, pruebas, runtime privado y navegador escritorio/móvil. Historial de acciones, sin diffs de campos inventados. |
| C4 · Fusión conservadora reversible | Siguiente corte: contrato de preflight, comparación/elección humana de campos, alias/origen y auditoría con reversión probada; revisar impacto sobre tareas, análisis y contexto antes de escribir. |
| C5 · Canales, agentes y predicción | Pendiente con puertas independientes R3B/R4/R5/R6/R7. No se habilita ejecución ni envío desde C3. |

La secuencia complementa R0–R9. Historial detallado de campos desde una fecha de activación requerirá un contrato aditivo propio; no se genera retrospectivamente. Autenticación/RBAC compartidos, alta académica y producción mantienen sus alcances separados.
