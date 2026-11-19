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
