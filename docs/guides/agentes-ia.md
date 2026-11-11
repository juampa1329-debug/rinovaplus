# Crear y utilizar agentes IA de admisiones

Una configuración válida queda disponible al pulsar **Guardar configuración**. No requiere aprobación adicional del perfil. Cada agente usa su proveedor, modelo, instrucciones y ámbito; las conexiones, la política automática del Inbox y el control humano conservan sus ajustes independientes.

## Conversar con Bety

Bety es la orientadora principal activa. Abra **Asistente**, seleccione **Bety** en **Asistente para conversar** y escriba el mensaje; **Enviar mensaje** se habilita con texto válido. Si conserva una lista anterior, pulse **Actualizar agentes guardados**. La misma conversación admite preguntas de seguimiento. Este modo usa texto, instrucciones del perfil, historial acotado y fuentes institucionales; voz y adjuntos siguen disponibles en el asistente general.

Un perfil archivado se restaura desde **Mis agentes → Restaurar agente**, se completa y se guarda. Sólo puede existir un orientador sin archivar; si ya existe otro, su sustitución debe preservar los agentes dependientes. El aviso de conflicto no debe resolverse borrando perfiles o desactivando controles. Guardar una configuración válida deja el perfil disponible sin otra aprobación.

## Inicio rápido

1. Abra **Agentes de admisiones → Mis agentes → Crear agente personalizado**.
2. Escriba el nombre. Elija **Orientador institucional**, **Agente de programa** o **Subagente de etapa**. Para un programa debe existir un orientador supervisor; para una etapa, su agente de programa. Los selectores usan la oferta vigente y permiten filtrar por escuela y jornada.
3. Revise las instrucciones propuestas o aplique una plantilla. El proveedor y el modelo iniciales proceden de los ajustes reales de la aplicación. Complete el modelo si aún no está configurado.
4. Revise canales, herramientas y presupuesto. Un perfil nuevo propone 250.000 tokens mensuales; no cambia el límite de un perfil ya existente. Se propone permiso de respuesta, sin activar conexiones ni envíos.
5. Pulse **Guardar configuración**. El perfil queda disponible; guardar un perfil ya pausado conserva la pausa. El diagnóstico es opcional.
6. Escriba una pregunta en **Probar respuesta** y pulse el botón. Esta acción autoriza una consulta al proveedor y su consumo. La respuesta aparece en la aplicación; no se envía al aspirante.

Para atender conversaciones del Inbox, configure el contexto y la asignación del programa. El programa se confirma mediante los controles del CRM: mencionar un nombre en el chat no cambia por sí solo la postulación ni la responsabilidad. La atención humana siempre tiene prioridad.

La prueba manual consulta las fuentes autorizadas y exige memoria vacía; no fabrica un UUID de mensaje entrante ni modifica hechos del aspirante. La memoria declarada se utiliza en conversaciones reales con evidencia. Tras responder, consulte **Ejecuciones**: modelo, finalización, latencia y tokens deben corresponder a la consulta. Una respuesta rechazada también puede haber consumido tokens; una reserva incierta no significa consumo cero. La cuota del supervisor incluye sus agentes, por lo que puede bloquear una prueba aunque el límite propio del hijo tenga saldo.

## Identidad, comportamiento e instrucciones

| Control | Efecto y uso |
|---|---|
| Nombre del agente | Identifica el perfil en la lista y en las asignaciones. No cambia la identidad escrita dentro de instrucciones anteriores. |
| Descripción operativa | Describe su función y se incorpora al comportamiento efectivo. |
| Responsabilidad | Orientador general, agente de programa o subagente de etapa. El ámbito guardado se conserva; para otro programa se crea otro perfil. |
| Supervisor | Mantiene la jerarquía institucional. Un hijo no amplía permisos, canales o presupuesto superiores. |
| Escuela y jornada | Filtran opciones reales del período vigente; no crean nuevas ofertas. |
| Programa y etapa | Delimitan información y atención. Una etapa mantiene sus condiciones y aprobación académica propias. |
| Tono y personalidad | Ajusta la forma de responder. No sustituye datos oficiales. |
| Postura de riesgo | Orientación automática con evidencia o postura cautelosa que solicita aclaraciones ante ambigüedad. |
| Estilo operativo | Añade una pauta de trabajo, por ejemplo explicar primero las opciones y después los siguientes pasos. |
| Política de derivación humana | Agrega motivos de derivación. No elimina la solicitud de una persona ni los límites de pagos/matrículas. |
| Objetivos y reglas | Un elemento por línea. Se heredan del supervisor; instrucciones extensas no se truncan al guardar. |
| Agente personalizado | Activado usa sus instrucciones; desactivado utiliza la guía institucional estándar. |
| Plantilla base | Selecciona orientación institucional o especialidad de programa. Elegirla no reemplaza el texto automáticamente. |
| Reemplazar instrucciones por plantilla | Sustituye el texto del borrador por la plantilla elegida. Revíselo antes de guardar. |
| Instrucciones operativas | Texto principal del agente. El ensamblador agrega fuentes, memoria, historial permitido y límites institucionales. |
| Variables JSON | Objeto de valores de texto que rellena marcadores. JSON inválido o valores numéricos muestran un error e impiden guardar. |

Ejemplo válido sin credenciales ni datos personales:

```json
{
  "business_name": "Instituto técnico",
  "attention_style": "Explicar con claridad y ofrecer el siguiente paso"
}
```

Puede usar `{business_name}` y `{attention_style}` en sus instrucciones. Los marcadores automáticos `{agent_name}`, `{agent_description}`, `{agent_specialty}` y `{program_id}` se toman del perfil y están reservados. La sustitución es literal y de una sola pasada; no ejecuta expresiones ni código. Las variables del hijo no reescriben las del supervisor. Un perfil histórico sin configuración de plantilla conserva sus llaves literalmente hasta que el operador adopte las plantillas al guardar.

## Canales, proveedores y respaldo

| Control | Efecto y uso |
|---|---|
| Global | Permite preparar análisis y documentos internos sin seleccionar conversación. No equivale a un canal público. |
| Web · aplicación | Permite usar este agente en la aplicación actual. No acredita un widget publicado en otro sitio. |
| WhatsApp, Instagram, Facebook y TikTok | Delimitan dónde puede atender. Las conexiones se administran en Ajustes → Canales y conservan su estado real. |
| Ruta operativa | Admisiones por programa, orientación institucional, seguimiento o analítica agregada. Cambia la orientación del contexto, sin conceder herramientas adicionales. |
| Proveedor de IA | Usa una conexión ya configurada en Ajustes → APIs. Las credenciales no se copian al perfil. |
| Modelo principal | Selección de los modelos conocidos de ese proveedor o del modelo previamente guardado. |
| Proveedor de respaldo | Puede ser el mismo principal u otro proveedor conectado. |
| Modelo alternativo | Modelo del proveedor de respaldo. Se intenta únicamente ante un error recuperable conocido. Un resultado incierto después de enviar la petición no se repite en otro modelo. |
| Máximo de tokens de salida | Limita la extensión de cada generación. |
| Configurar APIs y modelos | Abre la sección APIs existente, también cuando el agente está archivado. No guarda cambios del agente. |

Los nuevos perfiles toman proveedor/modelo de la configuración real. Si no existe una selección, complete la conexión y consulte sus modelos en APIs. Cambiar de proveedor limpia los modelos incompatibles del borrador; ninguna selección histórica se cambia silenciosamente.

## Presupuesto y A/B

| Control o indicador | Interpretación |
|---|---|
| Límite mensual de tokens | Cuota por agente y sus ancestros. Cero impide consumo. Los perfiles históricos con cero conservan ese valor. |
| Presupuesto USD/mes | Cero significa que no se aplica un límite monetario. No elimina la cuota de tokens. |
| Alerta de uso % | Umbral de alerta visible según consumo/reserva de la cuota configurada. |
| Detener al superar el presupuesto | Aplica corte por la cuota y el límite USD. Una cuota cero sigue bloqueando llamadas. |
| Tarifas de entrada/salida y respaldo | Valores informados por el operador en USD por millón de tokens. Use la tarifa de cada modelo correspondiente; no se inventa un precio del proveedor. |
| Reserva | Cubre el máximo de intentos previsto. Al completarse con uso informado se usa el consumo real para la cuota; si es incierto, se conserva la reserva. |
| Costo estimado | Uso informado multiplicado por las tarifas declaradas. No es una factura ni una conciliación del proveedor. |
| Costo desconocido o parcial | Faltan tarifas o consumo. El total parcial no debe interpretarse como costo completo. Un corte USD configurado bloquea cuando no puede reservarse un máximo conocido. |
| Activar experimento A/B | Compara la versión actual con otra versión guardada del mismo agente y ámbito. |
| Variante actual | Nombre para identificar sus ejecuciones. |
| Comparar contra versión | Elija una versión anterior guardada. Después guarde la configuración del experimento como una versión nueva. |
| Tráfico para la variante actual % | Distribución determinista por conversación automática. Las asignaciones manuales conservan lo seleccionado. |

En la comparación se intersectan permisos y canales con la configuración actual y se mantiene el presupuesto actual. No cambia de programa ni usa otro agente por sorpresa. El simulador permite elegir explícitamente versión actual o comparativa. Sin versiones anteriores, primero guarde una configuración y luego prepare la comparación en otra versión.

## Políticas y herramientas

Las políticas **Academia**, **Privacidad**, **Orientación sobre pagos** y **Atención a menores** agregan instrucciones específicas. Las reglas institucionales fundamentales se mantienen aunque no se seleccione una política complementaria.

| Grupo | Herramientas y resultados |
|---|---|
| Orientación e Inbox | Oferta institucional, fuentes aprobadas, respuesta sustentada y derivación al asesor. |
| Asesor y CRM | Borradores de acciones, resúmenes, notas y tareas internas. Los cambios con efectos requieren sus permisos y conversación del mismo ámbito. |
| Analítica y seguimiento | Indicadores agregados del programa, reportes, borradores y sugerencias de campaña, revisión de límites institucionales. No expone destinatarios de otras conversaciones ni publica campañas. |

Seleccionar herramientas no concede acceso a pagos, matrículas, ejecución de SQL ni decisiones académicas. No se incorporan comercio electrónico ni herramientas ajenas a admisiones.

## Las once opciones de memoria

| Opción | Fuente y alcance |
|---|---|
| Memoria corta | Historial reciente de la conversación, posterior al inicio de su contexto vigente. |
| Memoria semántica | Recuperación de fragmentos relevantes mediante el índice léxico actual. No implica embeddings o aprendizaje automático nuevo. |
| Resumen institucional | Ámbito de admisiones y programa confirmado, sustentados por la oferta vigente. |
| Perfil del aspirante | Preferencias declaradas y datos operativos de su ficha. Una inscripción declarada no se considera verificada. Desactivarlo omite lectura y escritura de esa memoria. |
| Basado en conocimiento | Documentos publicados, vigentes y aprobados para el programa/etapa. |
| Historial de campañas | Estado y fechas de campañas cuyo segmento incluye el programa; no destinatarios personales. |
| Historial de incidentes | Tareas de la misma conversación. |
| Historial de flujos | Eventos operativos del agente seleccionado. |
| Contexto del programa | Oferta, tarifas, asignaturas y requisitos suministrados por SQL institucional. |
| Contexto regulado | Recordatorios adicionales de privacidad, pagos y límites de decisión. |
| Memoria colectiva | Políticas y conocimiento público autorizado. No incluye memorias de otros aspirantes. |

Sin conversación seleccionada, el perfil del aspirante y sus incidentes se muestran sin datos. Sin registros de campañas o flujos, el contexto correspondiente está vacío: no se crean ejemplos. Los cambios relevantes de configuración, fuentes, contexto o control humano invalidan una respuesta en curso antes de confirmarla o despacharla.

## Los cuatro permisos

| Permiso | Efecto |
|---|---|
| Requiere aprobación humana para acciones | Mantiene los borradores de acción sujetos a aprobación. No agrega una aprobación del perfil. |
| Puede ejecutar acciones seguras | Permite registrar tareas/notas internas; sin aprobación sólo cuando impacto y riesgo son bajos y no se exige aprobación de acciones. |
| Puede responder mensajes | Permite respuesta del agente bajo las conexiones, fuentes, canales y control humano vigentes. |
| Puede actualizar CRM | Permite notas/tareas de seguimiento por las operaciones existentes del Inbox. No modifica matrícula, pagos o información institucional central. |

Los permisos del supervisor también se revisan al ejecutar una acción, incluso si el borrador conserva la misma versión del hijo. Una pausa del padre o una reducción de permisos impide registrar efectos anteriores incompatibles.

## Acciones, diagnóstico y mantenimiento

**Crear borrador seguro** guarda tipo, impacto, riesgo, título y contexto. Para una tarea o nota CRM, seleccione una conversación real del mismo ámbito. Las recomendaciones, resúmenes, reportes y propuestas de campaña son documentos internos; no publican ni envían. Si falta la herramienta correspondiente, actívela en la configuración y guarde antes de crear el borrador.

**Aprobar acción**, **Rechazar** y **Registrar acción** se aplican a ese documento. Los permisos y la cadena de supervisión se vuelven a comprobar. Registrar tarea/nota usa la operación idempotente existente del Inbox y conserva auditoría; repetir una operación confirmada no duplica la tarea.

**Ejecutar diagnóstico opcional** consulta condiciones de configuración sin consumo de IA. No aprueba perfiles ni es un paso obligatorio previo a guardar. Una configuración inválida sí devuelve un error de campo o de alcance al intentar guardarla.

**Pausar**, **Reanudar**, **Archivar** y **Restaurar agente** son controles directos. Archivar conserva datos e historial. Restaurar un registro histórico permite editarlo antes de guardar una configuración válida; no se activan de forma automática registros archivados por abrir la pantalla. Si existen hijos activos, primero gestione su disponibilidad antes de pausar o archivar el supervisor.

**Reindexar conocimiento** reconstruye los términos de los documentos publicados autorizados. Con cero documentos informa cero documentos/fragmentos; la oferta institucional se consulta directamente, sin crear una copia de programas o precios.

**Ejecuciones de la pasarela IA** muestra proveedor/modelo, versión/variante, estado, latencia y consumo disponibles. **Actividad y notas** permite conservar notas internas del agente sin consumir IA. La salud operativa es la proporción de ejecuciones completadas; no es una evaluación de exactitud académica.

## Problemas frecuentes

| Mensaje o situación | Qué revisar |
|---|---|
| Sin supervisor disponible | Cree o restaure el orientador institucional; después configure el agente del programa. |
| Modelo sin opciones | Complete su conexión y consulte el catálogo en Ajustes → APIs. |
| Variable pendiente o JSON inválido | Use valores textuales y complete el marcador indicado; los nombres automáticos están reservados. |
| Presupuesto agotado | Revise cuota, consumo informado y reservas inciertas. No reenvíe una solicitud incierta para evadir la reserva. |
| Formato de respuesta requerido | El modelo no devolvió el JSON de admisiones válido. Revise el modelo y el límite de respuesta; Actividad conserva el consumo reportado incluso si la respuesta fue rechazada. No se fabrica una respuesta para ocultar el error. |
| Límite de respuesta agotado | El proveedor indicó `MAX_TOKENS`; aumente el límite de respuesta guardado o acote instrucciones/pregunta. El JSON incompleto no se muestra como orientación válida y su consumo informado se conserva. |
| Referencia o memoria inválida | El modelo incumplió la evidencia exigida. La prueba manual solicita memoria vacía; una conversación real exige el UUID y la cita del mensaje de origen. No se guardan hechos inventados. |
| Tarifas requeridas | Complete entrada/salida del principal y respaldo para aplicar un corte USD. |
| Acción no permitida | Revise herramientas, permisos del agente y supervisor, versión, estado y conversación elegida. |
| Sin respuesta automática en Inbox | Revise política global, conexión, canal, fuentes, programa confirmado y control humano. Un perfil disponible no activa esas puertas por sí mismo. |

La guía también está disponible dentro de **Mis agentes → Guía completa**. La aceptación por navegador, proveedor, SQL y envío se registra por separado en el contrato y el avance del proyecto.
