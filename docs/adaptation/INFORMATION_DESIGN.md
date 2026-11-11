# Organización de CRM, mini CRM y Ajustes

Precisión del propietario del 2026-10-24: la copia debe recuperar las funciones y la organización útil de Scentra conservando el estilo visual de CRM CBN. Hay demasiado texto en las fichas, datos repetidos entre lectura y edición, análisis de abandono poco integrado y ajustes incompletos. Son requisitos de paridad, no un encargo para cambiar colores o tipografías.

Este contrato guía P2/P3 y la integración P10. Es revisión de fuente y planificación; no se ha inspeccionado la aplicación CRM viva en esta sesión ni se ha implementado el cambio visual.

## Una ficha compartida

- La misma identidad, etapa, etiquetas, notas, programa y campos personalizados alimentan Clientes e Inbox. No introducir otro estado global, ficha o tabla para resolver su presentación.
- Cada grupo de datos aparece una sola vez en la ficha. Abrir edición transforma esa zona o utiliza el editor de ese grupo; no añade un formulario completo debajo de otra copia de los datos.
- La autoridad determina edición: un dato CRM humano puede editarse según permisos; un dato académico oficial SIIE se identifica y consulta en su contexto, sin un falso control editable.
- Guardar, cancelar, cambios sin guardar y conflicto se muestran junto a la zona afectada. Un error conserva el borrador y explica cómo recuperarse.
- El encabezado identifica al contacto y el estado operativo. Repetir su nombre como título no es el problema; duplicar grupos completos de datos sí lo es.

Los componentes actuales `MiniCrm`, `InboxContactEditor`, `ClientFields`, `AnalysisConversation` y `ConversationStrategy` deben coordinarse. No se debe resolver el problema escondiendo un editor sin comprobar que las acciones siguen disponibles.

## Resumen primero y detalle a demanda

| Información | Presentación y comportamiento esperado |
|---|---|
| Contacto y oportunidad | Identidad, programa de interés, etapa, responsable y estado de atención, con acceso a edición contextual. |
| Diagnóstico | Resumen breve de temperatura, prioridad/score y riesgo de abandono; sólo indicadores con datos y significado comprobables. |
| Siguiente acción | Una recomendación principal con motivo y fecha; distinguir recomendación de tarea creada y de acción ejecutada. |
| Actividad | Historial cronológico consultable y paginado, sin repetir todo el análisis en cada evento. |
| Fuente académica | Datos oficiales y vigencia accesibles, sin hacer de la ficha una copia del catálogo completo. |
| Ayuda | Etiqueta y ayuda contextual breve; explicaciones extensas colapsadas. El operador no debe atravesar párrafos para llegar a los campos. |
| Diagnóstico técnico | Detalle de soporte colapsado; los códigos y nombres de tablas no son las etiquetas normales del CRM. |

El diseño concreto se revisará con las acciones existentes y el sistema Glass. No se presume una distribución final de pestañas o componentes antes de comprobar el recorrido. La mejora funcional autorizada incluye ordenar y reducir redundancia, manteniendo accesibilidad, foco, borradores y scroll interno.

## Riesgo de abandono conectado a la ficha

El backend actual ya contiene evaluación de riesgo en campañas y estrategias conversacionales. MiniCrm también incluye ConversationStrategy, que presenta «riesgo de abandono · estimación cualitativa». Eso no demuestra que el indicador esté integrado coherentemente en todas las fichas ni que sea un modelo entrenado. La brecha es unificar su lectura y significado, no crear otro indicador desconectado.

1. **P3:** definir un contrato de lectura compartido por CRM/mini CRM para el diagnóstico disponible. Mostrar riesgo/estado, razones breves, momento de evaluación y siguiente paso. Evitar un segundo cálculo en el navegador.
2. **P3/P8:** distinguir evaluación por reglas de campañas, señales conversacionales, score manual del asesor y predicción estadística. Una rúbrica 0–100 no es una probabilidad calibrada de abandonar.
3. **P10:** integrar el modelo entrenado cuando tenga dataset y evaluación aceptados. Mantener la versión/frescura y la posibilidad de volver al baseline.
4. Sin evidencia suficiente mostrar **«Sin evaluación»** o el estado específico acordado; no cero, «sin riesgo» ni un porcentaje de ejemplo.
5. Cambiar de contacto/programa no reutiliza una predicción ajena. La ficha debe conservar el mismo significado desde Inbox y Clientes y reflejar correcciones humanas sin reescribir la historia.

## Ajustes por función real

La referencia Scentra declara IA, Industria, Canales, APIs, Diagnóstico, Usuarios, Perfil, Seguridad y Plan en `frontend/src/App.jsx:530`. El destino declara siete secciones en `frontend/src/features/Settings.tsx:9`; Usuarios/Perfil/Seguridad todavía muestran identidad pendiente. Comparar contenido y contratos, no sólo contar pestañas.

| Área | Tratamiento de la copia educativa |
|---|---|
| IA y modelos | Conservar configuración existente y completar modelo principal/respaldo, capacidades, presupuestos y políticas según la referencia aplicable. Un modelo listado no implica que pueda ejecutarse. |
| Módulos | Disponibilidad institucional y permisos por capacidad. Sin selector de plan ni alta comercial de add-ons. |
| Institución y educación | ADN/perfil institucional, programas y comportamiento educativo; no portar todas las industrias ni convertir el catálogo oficial en campos manuales. |
| Canales | Cuenta, capacidades, estado, credenciales de sólo escritura y diagnóstico; reutilizar los adaptadores existentes. |
| Webhooks | Ya hay rutas y configuración dentro de Canales. Revisar visibilidad de callback, verificación, suscripciones, eventos y errores; una ausencia de pestaña no implica ausencia de backend. |
| Usuarios y seguridad | Administración y sesiones reales, permisos por acción y revocación; reemplazar estados futuros por capacidades verificadas en P2. |
| Perfil | Datos del usuario y preferencias, separados del perfil institucional y del aspirante. |
| Diagnóstico | Distinguir proceso vivo, SQL, migraciones, workers y proveedor. La salud del proceso no acredita preparación completa. |
| Plan | Se excluye por instrucción del propietario. Las cuotas técnicas y límites del proveedor se conservan en su área correspondiente. |

## Aceptación observable

- Un operador localiza y cambia una etapa/etiqueta/nota sin buscar entre dos copias de la ficha; Clientes e Inbox muestran el mismo resultado tras guardar y recargar.
- El panel inicial muestra datos y acciones principales con una jerarquía breve; lectura de ayuda ampliada es opcional y no ocupa permanentemente el espacio de trabajo.
- Un riesgo sin datos nunca parece evaluado; un riesgo por reglas nunca se presenta como modelo entrenado o probabilidad cierta.
- No hay controles de ajuste sin efecto/persistencia real ni rutas stubs presentadas como funciones disponibles.
- Navegación, teclado, foco, borradores y claridad/oscuro se verifican en el tamaño de pantalla acordado. La aprobación del estilo previo no cuenta como aceptación de una distribución nueva.
