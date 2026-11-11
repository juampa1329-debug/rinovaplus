# Plantillas de informe, pendiente y ADR

Copiar solo la sección necesaria y reemplazar campos entre `< >`. Estos bloques son plantillas, no avance o decisiones aceptadas. Nunca incluir credenciales, PII, transcripciones reales o connection strings.

## Informe de avance

```text
ID / Fecha (America/Bogota) / Responsable / Fase:
Objetivo y alcance autorizado:
Resultado: completado | parcial | bloqueado
Terminado: ID de trabajo + ruta/issue/PR verificados
Evidencia: entorno, comando/comprobación, resultado, revisión/versiones relevantes
No comprobado: capas y límites explícitos
Pendientes: IDs, prioridad, dependencias, responsable y aceptación
Riesgos/coste/cambio de alcance:
Decisiones: ADR aceptado o propuesta pendiente
Siguiente unidad y condición de inicio:
Autorizaciones de entrega/despliegue: concedidas | no concedidas | no aplican
```

## Pendiente o impedimento

```text
ID estable / Título / Fase / Prioridad:
Estado: abierto | en curso | bloqueado | en revisión | completado | diferido
Responsable y aprobador:
Problema/resultado observable:
Aceptación:
Dependencias:
Evidencia actual y no comprobado:
Condición para desbloquear/cerrar:
Issue/PR: URL verificada o aún no creado
```

## ADR — decisión con aprobación

Archivo futuro `docs/decisions/ADR-NNN-<slug>.md` (ruta planeada, no creada). ID consecutivo no reutilizable. Estado: propuesto → aceptado o rechazado → reemplazado por otro ADR; conservar historia.

```text
ADR-ID / Título / Fecha / Estado:
Decisor autorizado y evidencia de aprobación:
Contexto y restricción:
Decisión propuesta:
Alternativas reales y tradeoffs:
Consecuencias: coste, operación, seguridad, estilo y compatibilidad
Alcance / fuera de alcance:
Migración/reversión:
Validación y evidencia requerida:
Documentos/pendientes afectados:
Reemplaza / reemplazado por: ID o no aplica
```

La existencia del ADR no aprueba su contenido. Cambios de invariantes se escalan; los agentes no firman por el propietario. Guardar reportes fechados cuando haya trabajo nuevo, sin fabricar un historial previo.
