# Reglas rigurosas y cambio controlado

**Estado:** invariantes de seguridad obligatorias desde esta línea base; estándares de implementación propuestos hasta aprobarlos. Objetivo: una sola forma de construir, comprobar y operar, sin rigidez que impida corregir una decisión con evidencia.

## 1. Invariantes no negociables

| ID | Regla | Evidencia exigida |
|---|---|---|
| INV-01 | SQL Server SIIE es la fuente transaccional única; CRM no duplica estudiantes, matrículas ni precios como autoridad independiente. | Contratos y mapeo de lectura/escritura aprobados. |
| INV-02 | Proteger el core y la continuidad del SIIE; ningún cambio productivo implícito. | Autorización específica, pruebas fuera de producción, revisión DBA y plan de reversión. |
| INV-03 | Secretos y datos personales no se publican ni se usan como fixtures/prompts sin control. | Revisión del diff, escaneo y pruebas de redacción. |
| INV-04 | Autorización y validación en servidor; LLM, navegador y webhook son entradas no confiables. | Pruebas negativas de permisos, payloads, tokens e inyección. |
| INV-05 | Control humano prevalece; IA se identifica como asistente virtual. | Prueba de handoff concurrente y mensajes aprobados. |
| INV-06 | Un resultado se declara verificado solo en la capa comprobada. | Comando/entorno/evidencia/limitaciones; build no equivale a navegador, Meta o DB real. |

Ninguna excepción unilateral. Si una solicitud contradice una invariante, detener su parte insegura y escalar al propietario. La aprobación no elimina obligaciones de protección o privacidad.

## 2. Estándares propuestos para aprobación

- Monolito modular, límites por capacidad de negocio; no microservicios, bus adicional ni framework nuevo sin necesidad medible y ADR.
- React por funcionalidades; tokens y componentes compartidos; no estilos duplicados por pantalla. Accesibilidad y estados de error son parte de aceptación, no un ajuste final.
- Python y TypeScript con contratos tipados; versiones/runtime/lockfiles fijados al aprobar el scaffold. SQLAlchemy/ODBC y herramientas de formato, lint, pruebas y CI son propuestas, no instalaciones presentes.
- Configuración por ambiente validada al arrancar; secretos por referencia a almacén seguro; sin defaults productivos peligrosos ni credenciales en ejemplos.
- Errores con códigos estables y correlación, sin detalles sensibles; UTC en persistencia y zona de negocio explícita para horarios. Formato humano de informes: fecha America/Bogota.
- Contratos API versionados cuando cambie su compatibilidad, validación server-side, paginación y límites de tamaño desde la primera lista/webhook.
- Migraciones explícitas, numeradas y revisables para objetos `CRM_`, separadas de cualquier contrato core. Nunca generación automática aplicada sobre el esquema SIIE.

## 3. Trabajo y responsabilidad

Cada unidad tiene ID, responsable, aceptación, dependencias y evidencia. El propietario aprueba producto, arquitectura, estilo y cambios de reglas; el responsable técnico implementa; quien revisa comprueba evidencia; DBA autoriza diseño/acceso de datos. Roles pueden ser la misma persona en desarrollo individual, pero las aprobaciones deben quedar explícitas. Roles y personas se asignan en **P-002**.

Toda contribución: pendiente/issue → cambio pequeño → pruebas aplicables → revisión → informe → entrega autorizada. GitHub pendiente no impide documentar este rastro localmente.

## 4. Definition of Ready / Done

**Ready:** alcance y no objetivos definidos; dependencia resuelta; contratos y diseño necesarios aprobados; ambiente seguro; aceptación observable; coste/riesgo conocido.

**Done:** aceptación satisfecha; pruebas relevantes positivas y negativas; revisión del diff; sin secretos; documentación/backlog actualizados; reversión si cambia datos/configuración; limitaciones visibles. En tareas pasivas de documentación basta readback/enlaces/consistencia; no simular pruebas de runtime inexistente.

No se exige un porcentaje de cobertura arbitrario: la matriz debe cubrir riesgos de permisos, transacciones, duplicados, concurrencia, recuperación y reglas de negocio. Para la fase 0 aislada, [ADR-002](decisions/ADR-002-local-functional-skeleton.md) delega la selección de herramientas y checks locales mínimos de **P-004**. Driver, contratos, permisos y aceptación de controles conectados siguen pendientes antes de fase 1.

## 5. Cambio de estándares

**Secuencia local aceptada:** [ADR-003](decisions/ADR-003-local-phase-two-sequence.md) autoriza fase 2 funcional sin auth/permisos/seguridad operativa y difiere fase 1 al final del corte local. INV-01…06 siguen vigentes; loopback, banners, fixtures sintéticos y bloqueo de operaciones reales se mantienen. Una prueba local de campos o reglas conversacionales no prueba validación servidor, inferencia IA, SQL Server, permisos ni capacidad del canal. Antes de datos reales/conexiones/entorno compartido se exige fase 1 y la aceptación conectada correspondiente. La documentación y los checks separan ambos cortes.

Proponer ADR con problema, opciones reales, tradeoff, impacto, migración y prueba; el propietario acepta/rechaza; actualizar documento y fecha. No cambiar reglas para que un test pase ni borrar evidencia de un fallo. Consultar [plantillas](templates/report-and-decision.md).
