# Fase 3 — Atención y asistente LOCAL

**Fecha:** 2026-10-14, America/Bogota. **Autorización:** [ADR-004](../decisions/ADR-004-local-phase-three-workflows.md). **Estado: fase 3 completada al 100% de su alcance LOCAL aceptado**, con 60 pruebas/checks y navegador escritorio/móvil emulado comprobados. No acredita modelo IA, datos/API reales, operación, paridad completa o aprobación visual humana definitiva. Fases 0/2 conservan sus cierres históricos; esta unidad no los duplica.

## Qué se hizo

| Superficie | Entrega local |
|---|---|
| Inbox | Estado Abierta/En espera/Cerrada, responsable Sin asignar/Operador Demo/Asesor Demo B, prioridad Baja/Normal/Alta/Urgente. Vistas Míos/Sin asignar y filtro de estado junto a búsqueda/canal/control. Asignación ficticia no concede permisos. |
| Control humano | Cerrar bloquea añadir mensajes y preparar/usar plantilla hasta reapertura. Tomar/devolver control no ejecuta IA. Cambios de control, estado, contexto y configuración invalidan ejemplos derivados. |
| Seguimiento | Tareas por hilo, título 1–120 caracteres y fecha/hora opcional validada. Completar/cancelar conserva tarea e historial. Fecha en hora local del navegador, no SLA, alarma, timer, job o recontacto. |
| Timeline | Registro append-only de acciones explícitas locales: responsable, estado, prioridad, control, leído, tareas y mensaje añadido. Hora real y orden de inserción; presentación America/Bogota. Fixtures iniciales diferenciados; no auditoría persistida ni recibos sociales. |
| Asistente / IA Ajustes | Una configuración compartida en App, incluido borrador sin guardar entre rutas. Guardar/descartar/revisar para demo; revisión invalidada al editar/guardar. Proveedor/modelo siguen no seleccionados. Sin campos de secretos. |
| Plantillas | Ejemplo determinista según estilo y programa ficticio, aviso **Plantilla local de demostración · No es un modelo de IA**. Instrucciones visibles como texto de referencia, no ejecutadas. Sin precios, catálogo o disponibilidad real. |
| Uso humano | Generar → editar → marcar revisada → copiar al compositor → añadir explícitamente al hilo local. Copiar no añade mensaje. Cada edición requiere nueva revisión; ejemplo/borrador derivado vinculado a contacto, mensajes, ficha, control y revisiones. No envío automático. |
| Ajustes | Canales WhatsApp/Facebook/Instagram/TikTok confirmados, todos no conectados y sin promesas API. Diagnóstico muestra hilos, tareas pendientes, eventos y versión de config de memoria, sin consultas health/SQL/modelo o procesamiento de colas. Orden IA/Canales/APIs/Diagnóstico/Usuarios/Perfil/Seguridad preservado. |
| Regresión | Clientes/etapas/etiquetas/campos, mini CRM explicable y Comentarios de fase 2 se conservan. No nueva IA autónoma en comentarios. Restablecer/recargar descarta todo; tema/idioma visual siguen provisionales. |

Datos exclusivamente sintéticos. No introducir contactos, secretos o instrucciones de negocio reales. Tareas, eventos y configuración guardada viven solo en App; borradores humanos de Inbox viven en esa superficie y se descartan al salir. Cambio de selección/modo conserva borradores humanos por hilo/comentario, pero ejemplos asistidos se invalidan al cambiar target/contexto/revisiones. Una recarga elimina todo; no localStorage/sessionStorage.

## Ruta de revisión

1. En Inbox, tomar control, asignar operador ficticio, cambiar prioridad/estado y probar cierre/reapertura.
2. En Contexto CRM abrir **Seguimiento humano · Tareas** y **Timeline local · Eventos**; crear/completar/cancelar y comparar otro hilo.
3. En Asistente guardar/revisar configuración; elegir hilo bajo control humano y generar ejemplo. Proveedor/modelo sigue **No seleccionado**.
4. En Inbox abrir **Plantilla de respuesta · Revisión humana**, generar/editar/revisar/copiar. Confirmar que copiar no añade mensaje; añadir es una acción separada sin envío.
5. Cambiar control/cerrar/editar configuración: ejemplo anterior no se reutiliza. Revisar Canales/Diagnóstico y restablecer demo.

## Evidencia de checks

- Línea base ejecutada antes de cambios: `npm test`, **40/40 tests**, cuatro archivos. Tests históricos sin cambios.
- Normalización: `npm run format` antes del pase final.
- Pase final: `npm run check` → formato, ESLint, `tsc --noEmit`, **60/60 tests en seis archivos**, build `tsc --noEmit && vite build`; salida 0. Node **24.20.0**, npm **11.19.0**, dependencias/locks existentes sin cambios.
- Tests nuevos: validación/estado de tareas y aislamiento; operaciones/filtros/timeline; cierre/reapertura/control; config compartida/guardar/descartar/revisar; plantillas deterministas/no interpretación de instrucciones, vinculación e invalidación; copia sin append; reset y cero fetch/storage.
- Primer pase: 59/60; un fallo en test nuevo usaba `toHaveValue(expect.stringContaining(...))`, matcher no admitido por jest-dom. La respuesta real era correcta; se corrigió comprobando `.value` con `toContain`. Un comando de corrección se ejecutó desde cwd equivocado y no modificó source; el pase siguiente repitió ese mismo fallo. Corrección aplicada en raíz y normalizada antes del pase final completo. Sin ocultar/eliminar prueba.
- Source congelado en `.local/phase-3-source-hashes.json`: **36 archivos**, incluidos manifiestos/config de baseline y seis fuentes/tests nuevos. Los cinco source existentes modificados son App, Inbox, Settings, demo y styles; los otros **25/30** hashes de baseline se conservan. Nuevas fuentes: workflow/assistant, ThreadWorkflow/AssistantPreview y dos archivos de tests. No backend, lock/manifiesto, mini análisis, Comentarios, Clientes, tokens o tests históricos modificados.
- Helper Vite nuevo y propio iniciado oculto tras comprobar puerto libre: **PID 27052**, `node local vite.js --host 127.0.0.1 --port 5173 --strictPort`. HTTP raíz **200** y listener **127.0.0.1:5173** con PID coincidente; logs `.local/phase-3-frontend*.log`, PID en `.local/runtime.json`. No proceso ajeno detenido. Lectura CIM default fue denegada; inicio/comprobación loopback usaron escalación estándar. HTTP no sustituye prueba de UI.
- Git no ejecutado en esta unidad. La actualización ajena A-015/P-009 se conserva; fase 3 se registra como A-016.

## Evidencia de navegador — coordinador

Pase CUA agrupado de escritorio y móvil, sin corrección de producto necesaria. DOM de escritorio **1440 × 1024** y móvil emulado **390 × 844**; ancho de contenido **1425** y **375** respectivamente, sin overflow horizontal en superficies revisadas. Claro/oscuro y foco de teclado de 3 px visibles; consola sin errores/advertencias.

- Responsable Operador Demo, prioridad Urgente, vistas Míos y filtros de estado; cierre bloqueó compositor/plantilla, reapertura no recuperó revisión anterior. Tareas creadas/completadas/canceladas y aisladas de otro hilo; timeline con operaciones/hora local sin recibos de proveedor.
- Fecha opcional `2026-10-22T15:30` aplicada por cambio nativo de teclado, conservada tras editar título y presentada en la tarea. La automatización CUA `fill` sola cambió la propiedad DOM sin actualizar el estado controlado React; ArrowUp emitió el cambio real. Se comprobó el control nativo sin parche de source: es un límite de automatización, no defecto de la aplicación.
- Configuración Asistente/IA compartida entre rutas, guardar/revisar y ejemplo editable. Edición exigió otra revisión. Copiar no añadió mensaje; añadir explícitamente dejó **No enviada**. Target/control/cierre y editar+descartar config (revisión 3→5) invalidaron revisión/borrador; generar permaneció bloqueado hasta revisión explícita.
- Diagnóstico reflejó los **4 hilos / 9 eventos** del escenario local comprobado; no métricas de operación. Cuatro canales no conectados, regresión de Comentarios **No publicada**. Navegación móvil y tareas por Enter; reset/recarga descartaron las operaciones. Preview restaurado al viewport de escritorio.

Tres capturas nativas guardadas por el coordinador y validadas aquí como JPEG SOI/EOI con dimensiones propias. Las dimensiones del archivo no se confunden con el viewport DOM:

| Captura | Dimensiones JPEG |
|---|---|
| [Asistente escritorio claro](evidence/phase-3/assistant-desktop-light.jpg) | 1425 × 1013 |
| [Asistente móvil oscuro](evidence/phase-3/assistant-mobile-dark.jpg) | 375 × 812 |
| [Tareas móvil oscuro](evidence/phase-3/tasks-mobile-dark.jpg) | 375 × 812 |

Readback final: **36/36 hashes source intactos** después del navegador; **5/5 archivos backend** coinciden con baseline fase 0 y **2/2 manifiesto/lock frontend** con baseline fase 2. Backend no se modificó ni se reejecutaron sus siete pruebas previas. Evidencias históricas y actualización independiente Git A-015 preservadas; no comandos Git en esta fase.

## Checklist de navegador — completado

- [x] Escritorio claro/oscuro: Inbox, operación, seguimiento/timeline, Asistente/IA y Canales/Diagnóstico.
- [x] Móvil emulado: superficies apiladas sin overflow ni controles ocultos por geometría.
- [x] Teclado: foco, disclosures y controles; validación visible y acciones bloqueadas con razón.
- [x] Hilo cerrado, control humano, tareas y filtros; aislamiento de otro hilo.
- [x] Guardar/revisar plantilla, editar/revisar/copiar sin append, añadir local; invalidación por cambio de control/config/target; reset.
- [x] Regresión representativa de Clientes y Comentarios, mensajes sin envío/publicación, proveedores bloqueados.
- [x] Capturas/evidencia enlazadas y hashes source intactos tras browser. No dispositivo físico o aprobación visual humana definitiva.

## Límites y reversión

No DB/API/modelo IA/social/cola/Redis/Celery/media/voz/RAG, autenticación/roles/seguridad operativa, persistencia, notificaciones, matriz de paridad completa Scentra, pagos o matrícula. Sin evaluación de inferencia, durabilidad, concurrencia/handoff real, identidad omnicanal, capacidad TikTok/API, SLA o pruebas de proveedor. P-001…P-030 conectados siguen abiertos/diferidos; P-031 cierra únicamente este checklist local.

Una unidad cohesiva reversible: retirar los módulos/componentes/tests nuevos y restaurar App/Inbox/Settings/demo/styles y documentación actual al corte fase 2. No migraciones, registros durables, backend o dependencias que revertir; no ejecutar reversión o Git. Evidencia histórica ADR-001/002/003, informes 0/2 y referencias/diseños originales preservados.

## Qué prosigue

Fase 3 local cerrada; sigue **fase 4 LOCAL — formulario de aspirante**, con aceptación específica antes de implementar. No comienza automáticamente. Fase 1 se mantiene al final del desarrollo funcional local, obligatoria antes de conectar DB/API/modelos, datos reales, entorno compartido, despliegue o piloto. La integración futura exige sus contratos y autorización propios.
