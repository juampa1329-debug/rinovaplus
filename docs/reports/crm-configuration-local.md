# Configuración CRM persistente y mini CRM compartido

**2026-10-16 · primer corte de adaptación funcional autorizado.** Etapas, etiquetas y definiciones de campos tienen una fuente SQL compartida por Clientes y el mini CRM del Inbox. La migración local está aplicada; el runtime privado reconstruido está saludable y la aceptación de navegador en escritorio y móvil está comprobada. No se montó el router SaaS importado ni se implementaron sus 35 rutas.

## Qué se adaptó

La carpeta `backend/app/crm` contiene cinco archivos de otro sistema: router de 35 operaciones, 12 esquemas de entrada, compactador de notas y documentación. Sus imports `app_saas`, SQL PostgreSQL, dependencias de facturación/usuarios/workers y despacho externo no existen en esta aplicación. Se conserva como referencia sin editarla ni ejecutarla. Cambiar imports o añadir SQLAlchemy no resolvería la diferencia de contratos.

El corte reutiliza `CrmConfiguration`, `ClientFields` e `InboxContactEditor`. La configuración deja de depender de `seedCrmConfig` y de la memoria de una pestaña. Los borradores humanos continúan en memoria; las confirmaciones se guardan en SQL.

| Elemento | Contrato aplicado |
|---|---|
| Persistencia | Migración explícita `006_crm_configuration.sql`, esquema aditivo `crm_config`, tablas `Configuration` y `Operation`. Ninguna creación al arrancar o consultar. |
| API | `GET /api/local/crm/configuration` sin efectos y `PUT` con `operationId`/`expectedRevision`. Hash excluye la revisión de transporte, como el repositorio de contactos. Replay no duplica efectos; UUID reutilizado con otro documento y revisión obsoleta devuelven 409. |
| Identidades | Clave estable de etapa/campo; identidad exacta de etiqueta por su texto guardado. No renombrar o borrar etapas/etiquetas existentes en este corte. Desactivar conserva historia y permite reactivar. |
| Adopción | Solo `Stage`, `Tags` y claves `CustomValues` realmente guardados. Sin probabilidades inventadas, etiquetas comerciales, etapas institucionales prefijadas ni fixtures. Etiquetas de campos heredados iguales a su clave técnica, tipo texto y sin obligación inferida. |
| Tipos | Texto, número decimal, lista, fecha ISO válida, booleano, correo, teléfono y URL HTTP/HTTPS; opciones únicas y obligación explícita. Validación coherente en servidor y formulario. |
| Historia | Etapas/etiquetas inactivas o ajenas al catálogo pueden conservarse únicamente donde ya estaban. Campos inactivos o sin definición conservan valores sin permitir modificación. Cambiar tipo/opciones de un campo usado se rechaza. |
| Ficha | Clientes e Inbox comparten datos, validación, definiciones y borradores. La creación exige elegir una etapa activa real; no presupone «Nuevo». La etiqueta se elige del catálogo, sin CSV libre. |
| Mini CRM | Teléfono/canal visibles, ficha y campos agrupados, selector de etapas activas con historia identificada, etiquetas reales y acceso a administrar el catálogo desde Clientes. Conserva scroll propio, responsables, tareas, SLA y contexto R4. |
| IA | Evaluación/contexto siguen derivados de lectura. No se mezclan con notas compactadas; no se usa score heurístico, probabilidad de conversión ni horario/frecuencia comercial del origen. |

El catálogo permite probabilidad manual de etapa ausente. Un valor elegido por el operador se identifica como configuración, nunca como evaluación o conversión prevista por IA. Campos nuevos reservados para derivados IA se rechazan; este editor administra campos humanos. La UI permite crear campos con tipo/opciones/obligación y activar/desactivar definiciones existentes; no expone aún renombrado avanzado, reordenación ni edición de obligación/opciones de un campo ya creado. La API conserva el orden de las listas.

## Preservación y evidencia

Evidencia saneada: `.local/crm-config-20261016/`. No contiene valores de contactos, conversaciones o credenciales en sus resultados JSON.

- Inventario previo: dos contactos, una etapa distinta, una etiqueta y un valor personalizado de tipo JSON string; no se reinterpretaron números, booleanos, listas u objetos.
- Respaldo nuevo COPY_ONLY/CHECKSUM, restauración independiente y CHECKDB aprobados antes de aplicar. Ensayo de fallo previo a COMMIT revirtió el esquema; repetición pasó y una alteración de estructura se rechazó en la restauración.
- Migración aplicada/repetida: metadata core y filas previas de CRM, Admisiones, R2, R3A y R4 conservadas. El trigger DDL agregó **cinco** auditorías automáticas, preservadas. No hubo escrituras de negocio core ni limpieza.
- **25 comprobaciones SQL** de repositorio aprobadas: lecturas sin escrituras, revisión/replay, obligatoriedad/tipos, cambio de forma usado, inactivación, etapas históricas, validación en el escritor real de contactos y rollback de toda información de prueba.
- Se confirmó el **mismo documento real**, sin agregar ni modificar definiciones, y se releyó mediante conexión nueva. Los reintentos conservaron un solo efecto por operación. La segunda confirmación posterior al ajuste de compatibilidad dejó revisión 3; ambas operaciones son confirmaciones técnicas legítimas, no datos demo.
- Los escritores activos de contacto convergen en `SqlWorkspace.mutate` (Clientes e Inbox), con validación dentro de su transacción. Admisiones guarda seguimiento propio y no crea/modifica `crm.Contact`; no se incorporó una vía adicional de alta académica.
- Backend: **1668 pruebas aprobadas** desde el directorio correcto, lint y exportación de contratos comprobados. Dos warnings del test preexistente de filtros corresponden a workers que intentaron usar el doble SQL bloqueado por el guard de pruebas; no hubo conexión externa.
- Frontend: formato, lint, tipos, **185 pruebas**, build y detector visual mecánico aprobados. Tras la única corrección de navegación se repitieron formato/lint/tipos, **16 pruebas focales** y build, aprobados; no se suma ese recuento como pruebas distintas.
- Runtime privado 4173: reconstruido y saludable; siete comprobaciones de recreación/preservación y **16 HTTP** aprobadas (carga real, no-store, 409/422 sin cambios, R2/R3A/R4 conservados). Imagen `23cef494ffc349a62a91ba9ac5e00f2357e14095c119d9b4c306cde418e79845`; snapshot CRM y volumen IA idénticos. R4 sigue sin política, sin llamadas y con outbound bloqueado; la disponibilidad de credenciales se conserva sin inspeccionar sus valores. Navegador escritorio/móvil aceptado sobre esa misma imagen.

Las pruebas iniciales detectaron una colisión de nombres OpenAPI, dobles SQL sin catálogo y una prueba de creación que suponía una etapa hardcodeada: se corrigieron y se verificaron los casos afectados. Un intento amplio backend desde la raíz falló por rutas relativas `app/...`; su ejecución correcta corresponde a `backend`. No se confunden esos fallos de harness con operación SQL. La primera pasada de navegador detectó que el acceso desde el mini CRM dejaba cerrado el panel de configuración: se corrigió apertura, foco y desplazamiento con intención consumida una sola vez, preservando borradores. La segunda pasada comprobó la imagen final; no se hicieron más cambios de fuente ni rondas de refinamiento.

## Aceptación de navegador

Evidencia del coordinador leída: `.local/crm-config-20261016/cua-result.json`, estado `passed`, y captura `catalog-sql.png`. La imagen final se probó en escritorio 1440×1000 y móvil 390×844:

- Catálogo SQL revisión 3 con una etapa, una etiqueta y un campo real; recarga en frío conserva el catálogo y las probabilidades permanecen vacías.
- Selector de etapa y etiquetas de catálogo, contexto IA de lectura y definiciones compartidas en el mini CRM comprobados. Los borradores de ciudad, mensaje y alta administrativa sobreviven navegación; una definición sin guardar no se publica. Los borradores de prueba quedaron descartados.
- El acceso a administrar abre el catálogo y lleva foco al resumen en ambos tamaños. La intención se consume; una visita normal posterior no reabre el panel.
- Scroll CRM de escritorio de 0 a 350 con log de mensajes y página en 0; altura 716,515625 px. En móvil, panel de 358 px con scroll propio y configuración de 343 px sin desbordamiento horizontal.
- Cero mutaciones de negocio desde navegador y cero llamadas a proveedores. Pestaña del propietario intacta, viewport restaurado y una sola corrección UX.

## Operación y reversión

En **Clientes y prospectos → Configurar CRM local**, consultar la revisión SQL, añadir definiciones reales o activar/desactivar las existentes. Probabilidad vacía significa sin definir. Recargar configuración vuelve a consultar SQL; un conflicto actualiza el catálogo y conserva los textos del formulario para revisión explícita.

En el Inbox, abrir **Ficha compartida y campos del contacto**. Los cambios de ficha siguen siendo explícitos y compartidos con Clientes. **Administrar etapas, etiquetas y campos** lleva a Clientes conservando los borradores de la pestaña. Los datos derivados IA mantienen su sección y sus correcciones independientes.

Un fallo de carga muestra error sin catálogo demo ni reemplazar fichas. No se habilita guardar ficha hasta que el catálogo esté disponible. No hay borrado de definiciones ni borrado automático del esquema. Para revertir el runtime se conserva la imagen anterior y el respaldo; volver a una imagen previa conserva las tablas/datos nuevos. Una escritura de versión anterior puede dejar valores fuera del catálogo: el nuevo escritor permite retenerlos en su ficha, sin publicarlos automáticamente como definiciones.

## Fases de implementación

Esta secuencia complementa R0–R9; no renumera ni reabre R1.1/R2/R3A. Cada corte combina backend y frontend y cierra con preservación y aceptación por capa.

| Corte | Backend y datos | Frontend y aceptación | Estado |
|---|---|---|---|
| C1 · Configuración y mini CRM | Catálogo SQL real, revisión, idempotencia, tipos, inactivación y migración 006. | Editor existente y ficha compartida; recarga, conflictos y scroll. | Aplicado y aceptado en SQL, runtime privado y navegador escritorio/móvil. |
| C2 · Ficha institucional y duplicados de lectura | Perfil declarado aislado, claves canónicas y candidatos paginados explicables; sin copiar, vincular ni fusionar estudiantes. | Campos compartidos y comparación de lectura en Clientes/Inbox. | [Aplicado y aceptado en SQL/frontend/runtime privado/navegador](institutional-identity-c2.md). |
| C3 · Timeline y métricas | Registros existentes deduplicados, cursor estable y métricas del contacto completo; sin DDL ni diffs inventados. | Actividad compartida y métricas independientes de filtros. | [SQL/frontend/runtime privado/navegador aceptados](contact-activity-c3.md). |
| C4 · Fusión reversible | Preflight, elección de campos, alias/origen conservado, auditoría e impacto R2/R3A/R4; pruebas de reversión. | Comparación y confirmación humana explícita. | Pendiente; no portar DELETE del origen. |
| C5 · Canales, agentes y predicción | R3B: outbox/entrega/media y permiso de envío; R4: activación real aparte; R5: banco ejecutable; R6/R7: evaluación y calibración. | Estados comprobados, responsables reales y evidencia; sin habilitar envío por mostrar un botón. | Capacidades independientes pendientes. |

Este corte no reanuda la transferencia de credencial previa ni modifica `.env`, permisos, proveedor, modelo, presupuesto ni activación. Autenticación/RBAC, acceso compartido, producción, publicación Git y nuevas escrituras SIIE siguen fuera de este alcance.
