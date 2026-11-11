# Mapas de la adaptación educativa

Los flujos siguientes representan el destino planificado. La composición actual se consulta en `backend/app/main.py`, `frontend/src/App.tsx` y el grafo AST. Cada función parcial tiene evidencia en la matriz; los diagramas no certifican implementación o producción.

## Referencia y autoridad de datos

```mermaid
flowchart LR
  S["Scentra · referencia funcional"] -. "Comparación de contratos y comportamiento" .-> M["Matriz de paridad"]
  M -. "Unidades P1–P11" .-> UI["CRM CBN · estilo actual"]
  UI --> API["FastAPI · módulos institucionales"]
  API --> AUTH["Usuarios, roles y políticas institucionales"]
  API --> CRM["Esquemas CRM existentes y nuevos"]
  API --> SIIE["SIIE · autoridad académica"]
  CRM --> SQL["SQL Server 2019 existente"]
  SIIE --> SQL
  API --> Q["Trabajo y outbox durables"]
  Q --> W["Workers con recuperación"]
  W --> P["Canales y proveedores autorizados"]
```

Los esquemas aislados no son bases autoritativas duplicadas de estudiantes/precios/matrículas. La única cola de salida existente se conserva; cada portabilidad debe evitar escritores y colas paralelos que compitan por la misma acción.

## Mensajes, control humano y campañas

```mermaid
flowchart TD
  A["Webhook con firma válida"] --> B["Identidad externa y evento durable"]
  B --> C["Confirmar recepción tras commit"]
  B --> D["Conversación, contexto y propietario"]
  D --> H["Control humano"]
  D --> AI["Agente aprobado del ámbito correcto"]
  AI --> R["Acción tipada y validada"]
  K["Campaña o paso de remarketing"] --> R
  R --> G["Permisos, consentimiento, presupuesto y cadencia"]
  G --> O["Outbox única con idempotencia"]
  O --> V["Revalidar propietario, versión y baja"]
  V --> E["Proveedor"]
  E --> F["Recibo firmado y reconciliación"]
  H -. "Invalida trabajo IA pendiente" .-> V
```

No se puede convertir un resultado incierto en fallo seguro y reenviarlo sin reconciliar. La ventana/plantilla aplicable y permisos del proveedor se comprueban en el entorno de aceptación correspondiente.

## Memoria y aprendizaje

```mermaid
flowchart LR
  S["SIIE · información oficial"] --> C["Contexto autorizado"]
  D["Documentos publicados"] --> C
  I["ADN y memoria colectiva institucional"] --> C
  P["Memoria del aspirante y programa"] --> C
  C --> A["Agente educativo"]
  A --> E["Eventos y correcciones con evidencia"]
  E --> DS["Dataset revisado y versionado"]
  DS --> T["Entrenamiento fuera de línea"]
  T --> V["Evaluación contra baseline"]
  V --> SH["Modo sombra"]
  SH --> PR["Promoción aprobada o reversión"]
  PR --> A
```

La memoria contextual funciona antes de completar el entrenamiento. Cambiar instrucciones o guardar un score no entrena automáticamente un modelo. Una fuente de otro aspirante/programa no puede entrar por ser semánticamente parecida.

## Grafos para continuidad

| Mapa | Pregunta que resuelve | Archivo |
|---|---|---|
| Código CBN | Qué importa/llama el código seleccionado hoy | `../../graphify-out/graph.json` |
| Adaptación | Qué brecha se compara con qué archivo y en qué etapa | `../../graphify-out/adaptation/graph.json` |
| Scentra | Dependencias del comportamiento de referencia | `../../../saas-version/graphify-out/graph.json` |

Las relaciones `planned_for` y `planned_dependency` describen el plan, no funciones ejecutables. Los enlaces `semantically_similar_to` son inferencias para explorar y no prueba de paridad. Los imports/llamadas inferidos por AST también requieren inspección de fuente cuando haya resolución dinámica.
