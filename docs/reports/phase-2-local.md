# Fase 2 — Clientes, mini CRM y comentarios LOCAL

**Fecha:** 2026-10-13, America/Bogota. **Alcance autorizado:** [ADR-003](../decisions/ADR-003-local-phase-two-sequence.md). **Estado: fase 2 completada al 100% del alcance funcional LOCAL acordado**, con checks y navegador escritorio/móvil emulado comprobados. Esto no cierra los requisitos conectados originales SQL/API/RBAC/IA, la paridad completa Scentra ni la aprobación visual definitiva del propietario.

## Qué se hizo

| Superficie | Entrega local |
|---|---|
| Clientes | Crear/editar/cancelar y buscar/filtrar. Tipo e intereses libres. Etapas añadibles con clave/nombre únicos y probabilidad configurada 0–100; no pronóstico por cliente. |
| Configuración CRM | Etiquetas compartidas, aplicación/conteo/filtro. Campos Texto, Número, Lista, Fecha, Sí/No, Correo, Teléfono y URL con validación por tipo, claves normalizadas únicas y desactivación sin pérdida de valores. Enums internos ingleses conservados. Campos vacíos son opcionales; tipo booleano admite sin definir. |
| Inbox mensajes | WhatsApp/Facebook/Instagram/TikTok ficticios con canal visible y filtro. Un hilo por cliente; no identidad omnicanal. Ficha/configuración/valores compartidos con Clientes en App. Control humano y compositor local conservados. |
| Mini CRM | Temperatura, posible abandono, solicitud humana, espera sintética o no evaluable, resumen/evidencia/sugerencia humana. Identificación permanente **Análisis local de demostración · No es un modelo de IA**. |
| Inbox comentarios | Subsección independiente Facebook/Instagram/TikTok, publicación textual de contexto, búsqueda/red/estado, respuesta 1–1500 caracteres y estado local. Cada respuesta dice **No publicada · Solo local**. Borradores separados por comentario y de los mensajes; sobreviven selección/cambio de modo en Inbox. |
| Cierre y secuencia | Roadmap 0→2→3→4→5 local, después fase 1 antes de conectar o tratar datos reales. Backend y dependencias sin cambios. No se reescriben históricos de fase 0. |

Todos los cambios viven en memoria de la pestaña. Cambiar de ruta descarta borradores de esa superficie; cambiar de modo/selección dentro de Inbox los conserva. Recargar/restablecer descarta todos los datos, configuración y borradores. No ingrese datos personales ni secretos.

## Reglas provisionales del mini CRM

Se analiza únicamente el **último mensaje recibido**. Los mensajes enviados por el asesor no aumentan interés. Intención explícita de inscripción → Caliente/Bajo; consulta/interés informativo → Tibio/Bajo; rechazo comercial explícito → Frío/Alto; dudas/aplazamiento → Sin evidencia/Medio; sin señal o sin mensajes recibidos → Sin evidencia/No evaluable. Bajo no significa ausencia garantizada de riesgo. Las etiquetas describen señales del texto, no probabilidades calibradas.

Negativas prevalecen sobre positivos anteriores; texto entre comillas se excluye y negación explícita impide calentar. Petición humana se marca para revisión, no equivale a compra. Espera solo existe cuando metadata sintética apunta al último mensaje recibido; añadir un saliente la invalida. No hay reloj de SLA ni inferencia de desinterés por esperar. No detecta sarcasmo, referencias indirectas ni toda negación: requiere criterio humano. No se entrena ni consume un LLM.

## Evidencia

- RED inicial: prueba de contratos falló al no existir los nuevos módulos; tras implementación 22 pruebas de dominio aprobaron en el pase funcional. Después se añadieron cuatro pruebas UI de configuración, propagación, desactivación, canales/comentarios/drafts/reset y cero fetch/storage.
- Entorno verificado: Node 24.20.0, npm 11.19.0; lockfiles y runtime existentes, ninguna instalación/dependencia nueva.
- Pase intermedio: tipos y 35 tests frontend aprobados; cuatro tests UI adicionales aprobados. **Comando final:** `npm run format` antes de `npm run check`; formato/lint/tipos, **40 tests frontend** y build aprobados. Los 13 tests anteriores se preservan y 27 nuevos cubren este corte.
- Navegador: coordinador comprobó escritorio/móvil emulado, claro/oscuro, teclado, filtros, estados y geometría en un primer pase agrupado; una sola corrección acotada tradujo labels/metadata de campos y añadió explicación/count accesible del límite de comentarios. Segundo/final pase confirmó ambas correcciones y flujos locales sin errores/advertencias en la consola consultada. Preview recargado limpio, override de viewport restablecido. No teléfono físico ni aceptación visual final humana.
- Backend sin cambios: sus 7 tests/HTTP pertenecen al cierre histórico de fase 0; **no se ejecutaron nuevamente** ni se suman como prueba nueva de fase 2. Dependencias, configuración de conexión y seguridad existente no se modificaron.
- Incidencias acotadas conservadas: primer RED por módulos inexistentes; parche rechazado por contexto y comando de pruebas lanzado en raíz sin package.json, corregidos usando rutas exactas y cwd frontend. Primer check final detectó opción `exact` no admitida por tipos de Testing Library; se retiró (comparación de nombre string ya exacta por defecto), normalizó y check completo posterior aprobó. Sin cambio de tooling o datos. Una comprobación CIM y HTTP no disponibles en sandbox no acreditan estado del servidor; revalidar loopback en navegador antes de usarlo. Logs existentes muestran HMR del source actual, sin lanzar servidor duplicado ni detener procesos ajenos.

## Checklist local

- [x] ADR-003 y alcance/secuencia/límites documentados.
- [x] Crear/editar/cancelar, configuración/validación, filtros y estado compartido.
- [x] Evidencia mini CRM con negaciones/comillas/último entrante, desconocidos y espera sintética.
- [x] Cuatro canales de mensajes y tres redes de comentarios rotulados sin conexión.
- [x] Respuestas/borradores independientes, límites, reset y cero business fetch/storage probados.
- [x] Normalización y formato/lint/tipos/tests/build final aprobados.
- [x] Navegador escritorio/móvil, claro/oscuro, teclado y overflow comprobados.
- [x] Cierre con evidencia y siguiente unidad registrado: 100% LOCAL; aceptación conectada diferida.

## Verificación de navegador y capturas

| Recorrido comprobado por coordinador | Resultado local |
|---|---|
| Configuración/ficha | Nueva etapa 35 aceptada, 120 rechazado; clave duplicada mayúscula rechazada. Etiqueta aplicada/filtro/conteo; campo numérico 42, tipo/intereses/etapa propagados a Inbox. Desactivar conserva 42. |
| Mini CRM | A Tibio/Bajo, solicitud humana y 18 min sintéticos; B Caliente/Bajo; C Frío/Alto con negativa/evidencia/sugerencia humana; D Sin evidencia/No evaluable. Añadir salida «quiero inscribirme» a D no calienta. Reset restaura fixtures. |
| Canales y comentarios | Cuatro canales de mensajes/filtro/vacío; solo Facebook/Instagram/TikTok en comentarios. Borradores A/B y modos separados; respuesta exclusivamente local cambia estado demo con “No publicada”. Filtros combinados/vacío honestos. |
| Límite y localización | Selector visible en español con valores internos ingleses intactos. 1501 caracteres muestra límite/acción correctiva y bloquea añadir; vacío bloqueado; respuesta válida local funciona. |
| Geometría y teclado | Sin overflow horizontal en las superficies revisadas, incluida configuración expandida, mensajes y comentarios móviles. Navegación y Enter funcionan, foco visible de 3 px comprobado. Claro y oscuro legibles en revisión. |

Viewport solicitado/DOM revisado: **1440×1024 escritorio y 390×844 móvil emulado**. Las dimensiones físicas de los JPEG devueltos por el proveedor son distintas; no inferir viewport DOM desde sus píxeles. Firmas JPEG/EOI y dimensiones físicas verificadas por lectura binaria:

| Captura real de viewport | Dimensión JPEG comprobada | Tamaño |
|---|---|---|
| [Mini CRM escritorio claro](evidence/phase-2/mini-crm-desktop-light.jpg) | 1425×1013 | 78 431 bytes |
| [Comentarios escritorio oscuro](evidence/phase-2/comments-desktop-dark.jpg) | 1425×1013 | 81 701 bytes |
| [Comentarios móvil oscuro](evidence/phase-2/comments-mobile-dark.jpg) | 375×812 | 30 421 bytes |

No son mockups ni composiciones full-page; son capturas entregadas por el navegador. Tras confirmación, **30 archivos frontend** de `.local/phase-2-source-hashes.json` coinciden 30/30 con el source comprobado, incluidos manifiestos/locks/configuración/tests. SHA256 del inventario: `3ED6E5BBE1BCE3DBE4F2F6F873981DC7FF17935AEDEFB406EBF708BD53AFEF8F`. El cierre posterior modifica solo documentación; no normaliza ni cambia source.

Readback de cierre: **8 Markdown legibles/no vacíos, 123 referencias locales resueltas sin faltantes y 30 pendientes únicos**, conservando P-001…P-028 y P-029/030. Checklist local **8/8** completo. Los **5 archivos backend** presentes en el inventario histórico de fase 0 conservan 5/5 hashes; esto acredita ausencia de cambio, no una nueva prueba runtime.

## Límites y qué prosigue

No DB/API de negocio, persistencia, modelo IA, red social conectada, publicación/envíos, OAuth, media, auth/roles/seguridad operativa, scoring validado, SLA, duplicados/fusión/baja ni pagos/matrículas. No Git/commit/push/PR/despliegue. No afirmar paridad exacta Scentra: campos de identidad/dirección/pagos/presets y operaciones conectadas se excluyen de este corte; el local adapta Tipo libre y conserva etiquetas/valores. P-027/029/030 permanecen abiertos. Se mantiene loopback, banners y bloqueo de operaciones reales; no se retiró seguridad existente.

Después de la revisión local: **fase 3 LOCAL**, profundización de Inbox/asistente con alcance aceptado. Fase 1 al final del diseño funcional local, obligatoria antes de conexiones, datos reales o entorno compartido; después aceptación conectada independiente.

El mini CRM y Comentarios locales se incorporaron anticipadamente al alcance de fase 2 por ADR-003; esto **no declara fase 3 completa** ni duplica su cierre. El siguiente trabajo requiere concretar/revisar su alcance local restante. Decisiones y evidencia quedan en documentos del proyecto; Engram no pudo guardar por registro de sesión nativa no disponible, sin inventar identidad ni reconfigurar el entorno.

**Reversión:** retirar unidad CRM local (`shared/crm.ts`, `conversationAnalysis.ts`, `comments.ts`, componentes/tests nuevos) y restaurar App/Clientes/Inbox/demo/styles/documentación anteriores. Backend y locks no afectados; no hay migraciones ni datos remotos que revertir. Esta entrega no crea commit ni autoridad de despliegue.
