# R4 local — análisis incremental preparado, activación externa pendiente

Corte del 2026-10-16. El consumidor, la persistencia y la interfaz están implementados en el preview privado. **No hay proveedor/modelo/política configurados, no se enviaron conversaciones a proveedores y no existe análisis real generado.** La aceptación de inferencia permanece pendiente; las pruebas sintéticas no sustituyen esa evidencia. Contrato: [ADR-009](../decisions/ADR-009-conversation-analysis.md).

## Qué incorpora

Inbox → Configurar operación → **Análisis continuo de conversaciones · R4** permite escoger proveedor/modelo de catálogo real, presupuestos explícitos, autorización del alcance y activación independiente. Sin configuración, el worker permanece desactivado; no aparecen modelos, presupuestos ni contextos de demostración. En la ficha derecha, **Contexto conversacional · IA** muestra cobertura, estado y procedencia; los resultados son de lectura. Tras un resultado, una corrección humana separada puede pedir reevaluación con revisión original e idempotencia.

Todas las conversaciones son elegibles, incluidas cerradas y atendidas por humanos. Cada lote incorpora hasta seis mensajes nuevos, contexto previo y cinco correcciones. Los recibos por referencia/generación permiten continuar historia parcial y detectar referencias tardías. Los mensajes del operador registrados localmente no prueban entrega externa ni declaraciones del contacto. Citas locales muestran dirección y fecha; vacío significa sin evidencia. No se implementan respuestas, canales, especialistas ejecutables, puntuación, probabilidades ni entrenamiento.

La reserva SQL de solicitudes/tokens precede a cada llamada; fallos e incertidumbre también consumen cuota diaria UTC. Lease, revisión, configuración y fingerprint impiden confirmar resultados obsoletos. Una conversación sin referencias preparadas se difiere sin impedir que otra avance. La configuración específica de análisis y las credenciales invalidan resultados; cambiar preferencias ajenas del Asistente no reinicia el historial. La procedencia de un contexto anterior se conserva aunque cambie la política.

## Evidencia por capa

| Capa | Resultado comprobado |
|---|---|
| Migración | Respaldo COPY_ONLY/CHECKSUM, restauración independiente y CHECKDB aprobados; ensayo/repetición y aplicación de 005. Seis tablas vacías en `crm_analysis`; datos/contratos anteriores preservados. Diez auditorías DDL automáticas conservadas. |
| SQL funcional | 29 comprobaciones con rollback: replay/409, dos conversaciones, control humano/cerrada, referencia bloqueada, lotes parciales, feedback, presupuesto, lease recuperado, resultado obsoleto y procedencia. Ningún mensaje, política, corrección ni contexto técnico quedó persistido. |
| Backend | 365/365 pruebas combinadas aprobadas; incluye 19 pruebas R4 de redacción, instrucciones no confiables, citas/sujetos, política y worker. Ruff y exportaciones canónicas aprobados. |
| Frontend | Corrida combinada 20/21; se corrigió la espera de recarga en una aserción anterior de Inbox. Inbox/R4 11/11 posteriores; después del bloqueo del selector durante carga, R4 6/6. Lint, tipos y build aprobados. No se afirma una segunda corrida completa. |
| Runtime/HTTP | Imagen nueva healthy en el mismo preview privado 4173; 20 comprobaciones de lectura aprobadas. Worker vivo/desactivado y ciclo automático, cero reservas/contextos, dos conversaciones/dos miembros actuales y 15 referencias R3A preservadas; snapshot CRM, Admisiones y volumen IA conservados. |
| Navegador | Configuración desactivada aceptada en CUA: campos vacíos, guardar deshabilitado, contexto sin edición/demos, borradores conservados y descartados, scroll independiente y móvil sin desbordamiento. No constituye inferencia real. |
| Inferencia externa | No ejecutada: destino/modelo, credencial, alcance explícito y presupuesto requieren configuración del propietario. |

Evidencia saneada en `.local/analysis-r4-20261016/`: `backup-result.json`, `migration-result.json`, `repository-result.json`, `docker-final.json`, `runtime-freeze.json`, `http-result.json`, `cua-result.json` y captura saneada `r4-configuration.png`. Imagen: `sha256:8187e38a09b99526b82e5c3e81594665272153880156f2a7bd89910426bb9fbf`. El primer ensayo SQL falló por comparación de UUID con distinto uso de mayúsculas en el harness; corregir la comparación permitió verificar el mismo comportamiento. La corrección de espera frontend reconoce que confirmar escritura y completar lectura son operaciones distintas.

## Aceptación visual local

En 1440 × 1000, ficha de 716,516 px y desplazamiento derecho de 700 px sin mover mensajes/documento. En 390 × 844, ficha de 358 px con scroll automático y sin desbordamiento horizontal. Se observaron dos conversaciones y cero contextos generados; proveedor/modelo/presupuestos vacíos y guardar deshabilitado. Un presupuesto temporal de siete solicitudes y un borrador de mensaje sobrevivieron a navegación y se descartaron. No se guardaron políticas ni mensajes ni se llamó a proveedores. La pestaña propia quedó disponible con viewport restaurado; la pestaña del usuario no fue intervenida.

## Conexión Gemini — bloqueo de aprobación

El propietario seleccionó Gemini y el alcance redactado de R4. El sondeo confirmó configuración histórica en el checkout IA aislado, pero sus puertos 5175/8002 están detenidos; el modelo almacenado no constituye catálogo vigente. La revisión automática rechazó ejecutar la transferencia de credencial DPAPI al `.env` privado de la integración porque requiere aprobación humana explícita de descifrado y persistencia en texto plano. El script preparado no se ejecutó: no cambiaron credenciales, permisos ni runtime; no se consultó catálogo ni se activó política/inferencia. La integración continúa sin Gemini configurado. Se requiere esa confirmación concreta antes de reanudar la transferencia.

## Configuración pendiente para inferencia real

1. El propietario define proveedor/modelo y autoriza transmitir **mensajes redactados, contexto previo y correcciones humanas**, también de conversaciones cerradas o bajo control humano. No se transmite ficha ni adjuntos. La redacción por patrones no garantiza anonimato de texto libre.
2. En este contenedor Linux las claves pertenecen al entorno privado del backend: `GEMINI_API_KEY`, `XAI_API_KEY` u `OPENROUTER_API_KEY`, junto con `CRM_AI_OUTBOUND_ENABLED=true`. Configuración existente: [compose.yaml](../../compose.yaml), plantilla sin secretos [.env.example](../../.env.example), entorno local privado `.env` no versionado. Recrear el mismo servicio para aplicar entorno; nunca copiar claves al chat, navegador, informe o Git. Ajustes → APIs muestra el estado; no hay almacenamiento DPAPI disponible en Linux.
3. Cargar el catálogo real desde R4, seleccionar modelo compatible, fijar máximos diarios de solicitudes/tokens de salida y límite por respuesta, autorizar alcance y activar. No hay umbrales iniciales aceptados en nombre del propietario. El permiso global de salida también afecta otras funciones IA autorizadas; R4 no activa el Asistente ni envíos.
4. Comprobar una inferencia autorizada sobre la fuente real: cobertura, abstención, citas, procedencia, consumo, corrección y reevaluación. Solo entonces aceptar R4 conectado; la calidad semántica no está probada por validación JSON o pruebas sintéticas.

Comando de recreación, únicamente después de configurar el entorno privado y autorizar la activación, desde la raíz del proyecto:

```powershell
docker compose -p crm-cbn-integration-20261014 -f compose.yaml -f compose.local-sql.yaml up -d --force-recreate preview
```

Este comando conserva los volúmenes; no usar `down -v`. No se ejecutó para activar salida en este corte.

## Recuperación y límites

La [migración 005](../../backend/migrations/005_conversation_analysis.sql) es explícita, nunca automática al arrancar. Volver a la imagen anterior detiene R4 y conserva las tablas; reanudar recupera leases/recibos. No borrar el esquema ni restaurar encima de cambios posteriores. La tabla de intentos registra reservas, no facturación exacta: una caída después de llamar puede requerir otra llamada. Intervalo técnico de cinco segundos tras el ciclo, lease de sesenta segundos, tres intentos automáticos y reintento humano de hasta 25 fallos; no son SLA de producción.

Solo se conserva el contexto más reciente con procedencia; no hay historial completo de resultados ni RAG. La redacción y validación de citas limitan exposición y referencias inventadas, pero no demuestran que cada inferencia sea verdadera. Retención/purga, métricas de calidad y autenticación para uso compartido siguen pendientes. No se acredita operación productiva 24/7 ni aprendizaje R6. `LastEventId`/`PreparedAt` R3A continúan siendo diagnósticos, no cursores del consumidor R4.
