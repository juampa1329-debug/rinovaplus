# ADR-004 — Fase 3: atención y asistente exclusivamente locales

**Estado:** alcance local aceptado por instrucción explícita del propietario. **Fecha:** 2026-10-14, America/Bogota.

## Autorización y límites

Solicitud: «Vamos con la fase 3 en local, déjala al 100%. Seguimos sin conectar base de datos ni APIs; al terminar indícame qué se hizo y qué prosigue.» Continúa ADR-003; fase 1 sigue diferida hasta el final del diseño funcional local, obligatoria antes de datos reales, conexiones o entorno compartido.

No cambia arquitectura, stack, fuente SIIE ni controles obligatorios. Se reutiliza estado compartido en App, sin almacenamiento del navegador, dependencias nuevas, backend, cuentas, modelo, llamadas, workers, media, notificaciones o publicación. Asignación es presentación ficticia, no identidad o permisos. Configuración e idioma visual siguen provisionales; guardar/revisar no activa IA.

## Aceptación del corte local

| Capacidad | Evidencia necesaria |
|---|---|
| Atención | Estado Abierta/En espera/Cerrada, responsable ficticio, prioridad y filtros; aislamiento por hilo. Cierre impide añadir mensaje o usar plantilla hasta reapertura. |
| Seguimiento | Título validado, fecha/hora opcional validada, completar/cancelar sin borrar historial; no recordatorio ni recontacto. |
| Timeline | Acciones explícitas de estado, asignación, prioridad, control, tareas y mensaje local; orden de inserción/hora real, sin recibos de proveedor. |
| Asistente/IA Ajustes | Una configuración temporal compartida con guardar/descartar/revisión demo. Plantillas deterministas transparentes, sin interpretar instrucciones como herramientas o autoridad. Proveedor/modelo sin configurar. |
| Borrador de respuesta | Generar/editar/revisar/copiar al compositor humano; añadir requiere acción explícita separada. Vinculación a contacto/contexto/control/configuración; cambios invalidan revisión y borrador derivado. |
| Ajustes y regresión | Cuatro canales confirmados sin conexión; diagnóstico solo contadores temporales reales. Se conserva Clientes, mini CRM explicable y Comentarios, siete secciones sin Industria/Plan. Reset descarta todo. |
| Comprobación | Normalización antes de formato/lint/tipos/tests/build; navegador escritorio/móvil/claro/oscuro y teclado, con límites documentados. |

## Tradeoff y reversión

Las reglas locales y plantillas permiten revisar atención humana sin proveedor o almacenamiento; no prueban inferencia, concurrencia, permisos, durabilidad ni paridad completa de Scentra. Sin modelo no hay respuesta automática, scoring nuevo o promesas de conversión.

Unidad cohesiva: comportamiento, tests y documentación de fase 3. Reversión: retirar workflow/assistant y componentes nuevos, restaurar integración previa de App/Inbox/Settings/demo/styles y documentos actuales al corte fase 2; no tocar evidencias históricas, backend o manifiestos. No se ejecuta reversión ni Git.

## Continuación

Después del cierre comprobado local sigue **fase 4 local — formulario de aspirante**, solo por nueva autorización. P-001…P-030 conectados conservan su estado; no se cierran con este corte.
