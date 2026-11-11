# ADR-009 — Contexto incremental y consumidor IA local

Fecha: 2026-10-16. Implementación local R4 solicitada por el propietario. El permiso para implementar no activa tráfico externo: el preview actual no tiene proveedor/modelo/credenciales ni salida habilitados. La aceptación real de inferencia queda pendiente de configurar destino y autorizar alcance.

## Contrato

La migración explícita 005 añade seis tablas `crm_analysis`: política, estado por conversación, recibos por referencia R3A/generación, intentos/reservas, correcciones humanas y operaciones idempotentes. No cambia contratos anteriores, core ni stack. La revisión propia aumenta al reclamar/confirmar o corregir; LastEventId/PreparedAt de R3A no son cursores. Referencias nuevas, incluidas tardías, se encuentran por ausencia de recibo. Cambiar política o credenciales/configuración de salida pertinente invalida la generación anterior sin atribuirle procedencia nueva.

El worker integrado incluye todas las conversaciones, también cerradas y bajo control humano. Consume hasta seis mensajes nuevos por lote, contexto anterior y cinco correcciones; cada lote tiene cobertura visible y no declara vigente un histórico parcialmente cubierto. Redacción antes de transmitir: identidad conocida, teléfono, correo y patrones de documentos/credenciales. Solo referencias opacas viajan al modelo; UUID y mapeo se quedan en SQL/memoria local. Ficha, adjuntos y claves quedan excluidos. La redacción no garantiza anonimato del texto libre: el operador debe autorizar expresamente mensajes redactados, contexto previo y correcciones para el destino elegido.

Se reutiliza el gateway HTTPS fijo con claves del backend; sin nuevos proveedores, herramientas, fallback entre destinos ni acceso SQL del LLM. `AiSettings.enabled` pertenece a pruebas/Asistente; R4 tiene activación separada y respeta además el permiso global de salida. Proveedor/modelo proceden del catálogo real; no se preseleccionan modelos ni presupuestos. En Linux, claves y permiso pertenecen al entorno privado del servidor y requieren reinicio; no se crea un almacén nuevo ni se solicitan claves en chat.

## Consistencia y límites

Reserva durable antes de generar: máximo diario de solicitudes y tokens de salida reservados, reinicio del día en UTC. Fallos e incertidumbre consumen reserva; no se declara costo monetario ni uso exacto. Lease de sesenta segundos, tres intentos automáticos, pausa técnica entre intentos y reintento humano acotado. La inferencia ocurre fuera de la transacción. Token, expiración, revisión, fingerprint de fuentes y configuración se revalidan al confirmar; resultados antiguos no reemplazan datos nuevos. Una caída posterior a la llamada puede exigir repetir inferencia: no se promete exactamente una llamada facturada.

La salida es JSON acotado validado: resumen, intención, comportamiento observable, objeciones, compromisos y siguiente acción. Cada afirmación identifica hecho/declaración/inferencia, sujeto y evidencias existentes. Vacío significa sin evidencia; no se inventan probabilidades ni puntuaciones. Un registro saliente local prueba texto del operador, no entrega externa ni intención del contacto. Las correcciones humanas son evidencia del operador, nunca declaraciones del contacto o instrucciones privilegiadas.

El contexto es de lectura. Una corrección de hasta mil caracteres conserva referencia a su revisión, fecha UTC y operación idempotente, y solicita reevaluación. Borradores conservan revisión original; conflictos no sobrescriben silenciosamente. La procedencia real del contexto (proveedor/modelo/prompt/política) se conserva aunque cambie la política vigente.

## Compatibilidad, recuperación y aceptación

Backup COPY_ONLY, restauración y ensayo previo; DDL aditivo guardado, sin ejecución automática. La imagen anterior ignora el nuevo esquema y conserva sus datos; volver a R4 reanuda recibos/leases pendientes. No ejecutar DROP ni restaurar sobre datos posteriores. Logs/informes no guardan texto, claves ni datos personales; los derivados/correcciones permanecen en la copia SQL con acceso local. Retención/purga y autenticación compartida siguen requiriendo contrato antes de compartir.

Pruebas exigidas: privacidad/inyección/citas, salida local frente a entrante, presupuesto, replay/409, cambio de fuente/configuración, lease obsoleto, varios lotes, ausencia de bloqueo entre conversaciones, procedencia conservada, corrección/reevaluación y no activación sin consentimiento/credencial. Pruebas sintéticas solo en tests, negocio SQL reversible y navegador con datos reales. Ningún contexto sintético se publica como análisis real; la aceptación de inferencia requiere una llamada autorizada al proveedor configurado.
