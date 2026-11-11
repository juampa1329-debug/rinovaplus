import { memoryChoices } from "./api";

export function AgentGuide() {
  return <section className="agents-guide" aria-labelledby="agents-guide-heading">
    <h3 id="agents-guide-heading">Guía completa de Mis agentes</h3>
    <p>Un agente válido queda disponible al guardar. No hay una aprobación adicional del perfil. Las conexiones, el control humano y la política automática del Inbox conservan sus ajustes propios.</p>
    <h4>Crear y usar</h4>
    <ol><li>Pulse Crear agente personalizado. Seleccione nombre y responsabilidad. Para un programa, elija su orientador supervisor y filtre la oferta vigente por escuela y jornada.</li><li>Use una plantilla de admisiones o escriba instrucciones. Complete variables JSON sólo con texto. El proveedor y el modelo iniciales se toman de sus ajustes reales.</li><li>Revise canales, herramientas y permisos. El límite inicial de nuevos agentes es 250.000 tokens mensuales; no cambia los perfiles existentes.</li><li>Pulse Guardar configuración. El perfil queda disponible inmediatamente. Puede ejecutar un diagnóstico opcional sin consumir IA.</li><li>Escriba una pregunta en Probar respuesta. Pulsar el botón autoriza esa consulta y su consumo, sin enviar nada al aspirante. En Inbox, el contexto confirmado del programa y la asignación determinan el responsable.</li></ol>
    <h4>Campos de configuración</h4>
    <div className="agents-guide-table"><table><thead><tr><th>Campo</th><th>Para qué sirve</th></tr></thead><tbody>
      <tr><td>Nombre, descripción y responsabilidad</td><td>Identifican al orientador, agente de programa o subagente de etapa. El ámbito guardado no se cambia a otro programa.</td></tr>
      <tr><td>Supervisor, programa, escuela, jornada y etapa</td><td>Usan la oferta y la jerarquía existentes. Una etapa mantiene su condición académica y evidencia propias.</td></tr>
      <tr><td>Tono, riesgo, estilo, derivación, objetivos y reglas</td><td>Personalizan el comportamiento sin sustituir las fuentes oficiales ni el control humano.</td></tr>
      <tr><td>Agente personalizado</td><td>Activado usa sus instrucciones; desactivado usa la guía institucional estándar.</td></tr>
      <tr><td>Plantilla e instrucciones</td><td>Elegir una plantilla no modifica el texto hasta pulsar Reemplazar instrucciones por plantilla.</td></tr>
      <tr><td>Variables JSON</td><td>Objeto de valores textuales, por ejemplo {"{"}"business_name":"Instituto técnico"{"}"}. Marcadores automáticos: {"{agent_name}"}, {"{agent_description}"}, {"{agent_specialty}"}, {"{program_id}"}. No ejecute código ni introduzca credenciales.</td></tr>
      <tr><td>Canales y Global</td><td>Canales limita atención conversacional. Global permite análisis y documentos internos sin conversación; Web corresponde a esta aplicación.</td></tr>
      <tr><td>Ruta, proveedor y respaldo</td><td>La ruta orienta el contexto. Proveedor/modelo y respaldo pueden usar conexiones diferentes ya configuradas. Un envío incierto al proveedor no se repite en otro modelo.</td></tr>
      <tr><td>Tokens, presupuesto USD y alerta</td><td>Controlan reserva mensual y alerta visible. Cero tokens impide consumo. Cero USD no aplica un límite monetario.</td></tr>
      <tr><td>Tarifas y corte de presupuesto</td><td>Informe USD por millón de tokens de entrada/salida y del respaldo. Son estimaciones del operador, no facturación. Un corte USD requiere tarifas completas; costos desconocidos se muestran como tales.</td></tr>
      <tr><td>A/B</td><td>Compara una versión anterior del mismo agente con la actual. El tráfico se distribuye estable por conversación automática; las selecciones manuales usan lo elegido. El simulador permite comparar explícitamente.</td></tr>
      <tr><td>Políticas, herramientas, memoria y permisos</td><td>Se aplican al contexto y a las operaciones disponibles. Los hijos no amplían permisos del supervisor. Ningún permiso concede acceso a pagos o matrículas.</td></tr>
    </tbody></table></div>
    <h4>Memorias</h4><dl>{memoryChoices.map(([id, label, detail]) => <div key={id}><dt><strong>{label}</strong></dt><dd>{detail}</dd></div>)}</dl>
    <p>La recuperación relevante actual utiliza índice léxico. Sin conversación, ficha del aspirante e incidentes aparecen sin datos. Campañas son resúmenes del programa; memoria colectiva comparte sólo políticas y fuentes públicas, nunca conversaciones ajenas.</p>
    <h4>Acciones, actividad y disponibilidad</h4>
    <p>Crear borrador seguro conserva tipo, impacto, riesgo, título y contexto. Aprobar una acción sólo aprueba ese documento. Registrar una tarea o nota requiere conversación del mismo ámbito y permisos actuales; se guarda por las operaciones existentes del Inbox. No se publican campañas ni se envían mensajes desde esta sección.</p>
    <p>Pausar detiene disponibilidad; guardar un perfil pausado conserva la pausa. Reanudar lo vuelve a poner disponible. Archivar conserva los datos e historial; Restaurar permite editar nuevamente. No se restaura un perfil por entrar a la pantalla.</p>
    <p>Reindexar conocimiento reconstruye los términos de documentos publicados autorizados. Con cero documentos informa cero; la oferta institucional sigue consultándose directamente. Actividad y notas son persistentes y no consumen IA.</p>
    <h4>Cómo leer los resultados</h4><p>Tokens reportados proceden del proveedor. Reserva incluye intentos posibles y se conserva si el resultado es incierto. Latencia se mide en cada llamada real. Salud es proporción de ejecuciones completadas, no exactitud académica. Costos parciales o desconocidos no se presentan como facturación completa.</p>
    <h4>Resolver problemas</h4><ul><li>Sin supervisor: cree o restaure el orientador antes de un agente de programa.</li><li>Sin modelo: configure la conexión y consulte sus modelos en Ajustes → APIs.</li><li>Variable pendiente: complete su valor textual o retire el marcador de las instrucciones.</li><li>Presupuesto agotado: revise reserva, límite y tarifas; no se reintenta una operación incierta.</li><li>Acción bloqueada: revise versión, supervisor, herramientas, permisos y conversación elegida.</li><li>Sin respuesta automática en Inbox: compruebe política global, conexión, canal, fuentes, programa confirmado y control humano.</li></ul>
  </section>;
}
