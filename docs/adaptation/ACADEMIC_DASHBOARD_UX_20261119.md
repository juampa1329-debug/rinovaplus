# Académico, Admisiones y Dashboard · 19-11-2026

## Decisión de diseño

Se aplican frontend-design, ui-ux-pro-max, responsive-design y principios de motion-design/KPI dashboard. La búsqueda local de diseño recomendaba una página de demostración azul; se descartó por no corresponder a un CRM operativo ni a la marca del propietario. Se conservan petróleo #12343B, lima #C4F04D, Manrope y Source Sans 3. Tipografía numérica tabular, controles con etiquetas, estados vacíos y movimiento de gráficas de 450ms desactivable por prefers-reduced-motion.

Estructura revisada antes de implementar: Dashboard = bienvenida/período → cuatro indicadores → actividad diaria y canales → agenda/modos. Académico = contexto de biblioteca → conexión SIIE → programas por escuela a la izquierda/ficha a la derecha → procedencia/finanzas/guardado. Admisiones = período/filtros → listado/ficha/historial. En móvil las columnas se apilan, sin encoger las fichas hasta hacerlas ilegibles. No se agregan dependencias de animación para transiciones CSS/SVG simples.

## Datos y alcance

- Inicio de sesión explícito, incluida verificación 2FA: abre Dashboard. Restaurar una sesión al recargar conserva la ruta de trabajo; activación/recuperación siguen separadas.
- Dashboard GET `/api/institution/dashboard?days=7|30`, sólo despliegue PostgreSQL. Consulta local de lectura, sin proveedores, nuevas tablas, semillas ni datos personales en la respuesta. Cada bloque requiere permiso y módulo habilitado.
- Ventana: días calendario de Bogotá, desde medianoche del primer día hasta el instante de consulta. Mensajes se agrupan por su fecha de creación. Enviados = tienen identificador externo y trabajo en sent/delivered/read; en cola/fallidos/inciertos no cuentan. Recibidas = chats con entrada en el período; atendidas = tienen una respuesta confirmada posterior a una entrada del mismo período. IA = ruta bot confirmada. Los recibos/trabajos duplicados no multiplican mensajes.
- Tareas pendientes/vencidas y modos IA/Humano son una fotografía actual de todas las conversaciones. Completadas = estado completed actual y actualización dentro del período, no un historial de cada transición. Comentarios excluyen ecos/respuestas propias. No se presentan estos contadores como matrículas, ventas ni atribución financiera.
- Admisiones usa las consultas ASPX ya integradas, bajo agents.manage y módulo de origen, sin habilitar escrituras de seguimiento ni decidir matrícula.
- Cada ficha local ofrece Sincronizar con SIIE: prepara una revisión y conserva datos manuales; Guardar aplica. Una ficha sin vínculo abre el explorador para seleccionar el ID correcto. Un catálogo base no confirma datos financieros de ofertas no consultadas.
- El informe de faltantes compara datos locales con la última copia recibida y puede copiarse para revisión del equipo SIIE. No transmite datos ni correos automáticamente.
- Los errores SIIE dejan de mostrar la referencia de una consulta anterior: se limpia al consultar y sólo se conserva un identificador seguro del intento fallido.

## Voz: corrección adicional durante esta revisión

El titular reportó dos audios entrantes sin respuesta. La proyección del webhook registraba el archivo pero sólo programaba Gemini para texto. Ahora programa también audio WhatsApp con ID válido, después de registrar el medio. El worker espera la descarga inspeccionada y conserva deduplicación, IA/Humano y cuotas. No se reenvían eventos antiguos automáticamente.

En IA general se sustituyen los controles multimedia heredados por un enlace a la configuración real de Voces y audios. Gemini interpreta la nota; ElevenLabs sólo sintetiza cuando la política lo permite. El piloto de voz continúa limitado al 44 institucional: no se habilita gasto de voz global por esta corrección. El último audio del chat nuevo se observó en modo IA, sin respuesta antes de este arreglo; un chat fuera del piloto debe seguir teniendo respuesta por texto.

## Evidencia y límites

Copiado real de una página de 25 programas por la UI sobre 5bc9b60; bbaf756 saludable en Coolify, run 0kuhplq4mp1zbbot2eigpqyw terminado 20:09:18Z. Software143 tiene ofertas actuales1204-n1…n4 del período129. Su detalle financiero aún mostró indisponibilidad del proveedor, sin inventar precios. Esto no acredita aceptación integral P16.

Pruebas de UI/contrato/voz y revisión publicada se registran en el artefacto de esta entrega. Los dobles locales no sustituyen SQL nativo; Docker Desktop no estaba activo. No se abrió terminal privilegiada ni SSH tras la revisión automática. Bundle grande previo conservado. P0–P11/P12 auxiliar y P15 mantienen su aceptación; P13/P16 y P19 conservan las unidades realmente aceptadas.

## Comprobación publicada y ampliación — 2026-11-19

Backend 4c64841 saludable en Coolify (n14uz61jfplinxnkr9ecaplp), finalización 20:44:03 UTC. Dashboard 7/30 días y totales comprobados contra PostgreSQL publicado por UI. Software revisión 2, 25 programas conservados. Admisiones: período 129, filtros y primera página de 25 aspirantes. Sin DDL ni escrituras SIIE. El alias SQL reservado falló 42601 y se corrigió a AS bucket_date; parser local no sustituye replay histórico ni SQL nativo local (Docker inactivo).

El titular confirmó dos respuestas de voz personalizadas completas. P19.3 aceptada: P19 3/5 (60%), pendientes asignación múltiple y operación/consumo. Configuración versión 11 global guardada del lado del propietario, no activada por este agente: 3 audios por hilo, 60s, Tranquila, estabilidad 40%, similitud 91%. Tema claro/oscuro comprobado y Sistema restaurado. Override IAB 375 no cambió el ancho: no acreditar revisión visual móvil 375.

La ficha ampliada agrupa contenido académico revisable: presentación, niveles/materias, título, acreditaciones, prácticas y campo ocupacional. Enlace oficial prepara borrador, exige Guardar; no presume alta calidad, prácticas garantizadas ni empleo. Modalidad contado/financiación/ambas, abono, cuotas con fechas opcionales, vigencia hasta fecha o hasta nueva indicación confirmada. Null sin esa confirmación sigue por confirmar. Refresco SIIE preserva correcciones manuales. Catálogos con scroll y filtros de escuela; copia SIIE sigue siendo la página completa de 25.

El cupo 120 solicitudes/minuto/usuario queda intacto. GET concurrentes iguales comparten solicitud; cliente estable; polling sin foco detenido; Retry-After coordinado entre Inbox/notificaciones/agentes y pestañas mediante un timestamp sin datos ni credenciales. Perfil social sólo al abrir hilo, sin ráfaga de toda la lista. Ninguna escritura se reintenta automáticamente.

Nginx devuelve 404 para assets inexistentes en vez de HTML. Identificador de compilación público y aviso con recarga manual/guardia de borradores; entrada detecta fallos antes de React. No conserva assets antiguos entre imágenes: pestañas anteriores al arreglo requieren recarga manual.

Validación: 320 backend/42 frontend seleccionadas, tipos, ESLint modificado y build workspace pasan; advertencia previa de bundle grande conservada. Pendientes al corte: despliegue, extracción real de Software y observación del Inbox después del arreglo.

## Resultado real de la ampliación

ccb8928 publicado: backend cju9eqzkkcfdzxsusysaz4ho saludable, rolling update completado 21:19:59 UTC según Coolify. Frontend build público 1795122956165, controles y estilos visibles; ruta de asset inexistente muestra 404, no HTML del CRM.

Firecrawl extrajo del enlace oficial de Software los cuatro semestres/materias, presentación y campo ocupacional. Revisión humana operativa conservó identidad/escuela/jornada DIURNA nativas y corrigió una mezcla de duración/jornada en la propuesta. No había título/acreditación de programa explícitos ni precios/fechas: no se inventaron. Prácticas institucionales guardadas como información condicionada a confirmación, sin plaza garantizada. Guardado revisión3, recarga, sincronización base SIIE y guardado revisión4 conservan todo el contenido y los25programas. La fuente financiera no queda validada por esta extracción web.

Biblioteca completa: clientHeight966, scrollHeight2747, scroll propio verificado; escuela TIC filtra3registros. Inbox abrió listado y chat del44; sin errores en la consola observada. No se forzó un429 en producción ni se acredita benchmark de carga: coalescencia, pausa compartida, foco y Retry-After se verifican con pruebas controladas. Las pestañas previas al arreglo requieren recarga manual.

Ajuste final: informe de faltantes incluye los nuevos campos académicos; Retry-After numérico y HTTP-date, incluso600s, sin reintentar escrituras.320backend/43frontend seleccionadas, tipos/lint modificado/build pasan. Esta nota no acepta nuevas unidades deP13/P16; P19sigue3/5.

Frontend25f2f18 verificado Success/Running en Coolify, runzbisachc81zspamnv7swph7u. El aviso real de actualización apareció sin forzar recarga; Recargar conservó la sesión. Software revisión4 muestra cuatro datos locales ausentes en la copia base (presentación, materias, prácticas, campo ocupacional) y permite copiar el informe. No se envió el informe a SIIE.
