# Seguridad y operación desde el diseño

**Estado:** controles requeridos y riesgos registrados; no implementados ni auditados. Producción y cumplimiento legal no se declaran listos. Revisiones de privacidad/menores requieren responsables cualificados (**P-005**), no conclusiones inventadas.

## Controles mínimos por superficie

**Ingreso local Meta autorizado, 2026-10-20:** se preparó un listener separado del mismo runtime en loopback 4174 para dirigir el túnel Tunnelmole únicamente a `/api/v1/webhooks/meta` (GET/POST). Las demás rutas se rechazan y las firmas POST permanecen obligatorias. El puerto 4173 de administración/frontend no debe ser el destino del túnel. La configuración del ingreso no acredita todavía túnel activo ni aceptación del proveedor. [Alcance y operación](deployment/meta-webhook-tunnelmole.md).

| Superficie | Control y prueba antes de habilitar |
|---|---|
| SIIE | Lectura acotada, mínimo privilegio, TLS válido, límites de pool/carga; DBA revisa índices/planes/bloqueos en test. Separar autorización de lectura, DDL `CRM_` y core writes. |
| Asesores/admin | Autenticación y RBAC por acción/recurso; revocación, expiración/sesión y auditoría; no basta ocultar botón. Proveedor de identidad/MFA y roles pendientes. |
| Webhooks | HTTPS, firma/validación de origen según contrato verificado, body/size/time límites, deduplicación, replay/abuso y rate limits; sin aceptar llamada por confianza en prompt. |
| Formulario | Token criptográfico de un uso, expiración y consumo atómico; minimización, validación backend, rate limit, CSRF según modelo de sesión, no token en analytics/logs. |
| IA/proveedores | Redacción/minimización antes de enviar; respuestas validadas; prompt injection no permite SQL o tool execution; costes/timeouts/capacidad limitados y aprobación de tratamiento por terceros. |
| Secretos/media | Vault o almacén seguro/cifrado con llaves separadas; DB solo referencias o ciphertext controlado; rotación y acceso auditado. Media temporal con acceso limitado, vencimiento y borrado. |
| Datos personales | Consentimiento/avisos, finalidad, menores, retención/borrado y atención de solicitudes definidos; logs/fixtures/informes anonimizados. No conservar transcripción/perfil por conveniencia. |

## Riesgos abiertos

| ID | Riesgo | Mitigación / responsable por asignar | Puerta |
|---|---|---|---|
| R-01 | Dañar datos o rendimiento SIIE. | DBA: contratos/backup restore/rollback, cargas y locks test, piloto acotado. | P-001/011/012 |
| R-02 | Doble mensaje, doble registro o IA respondiendo tras handoff. | Técnico: inbox/outbox, restricciones, transacciones, control durable y pruebas de carrera. | P-010 |
| R-03 | Fuga de datos, claves o tratamiento de menores inadecuado. | Seguridad/propietario: minimización, redacción, RBAC, retención y revisión cualificada. | P-005/006 |
| R-04 | Suspensión del canal o recordatorios sin autorización. | Responsable Meta: validar reglas/ventanas/templates/opt-out antes del envío. | P-007/014 |
| R-05 | Alucinación, engaño de identidad o perfilamiento invasivo. | Propietario/técnico: transparencia IA, fuentes SIIE, control humano y autorización de perfilamiento. | P-005/008/010 |
| R-06 | Proveedor caído, gasto sin límite o retrasos indefinidos. | Operación: budgets por ambiente, cuotas, timeout, retries, circuit breaker si probado necesario y pausa segura. | P-012/013 |
| R-07 | Restauración no probada o caída de Redis pierde trabajo. | Operación/DBA: inbox/outbox durable, recovery drills y respaldo/restauración test. | P-006/012 |

## Operabilidad y recuperación

Entornos separados, datos sintéticos/anonimizados y credenciales distintas; no apuntar local/CI al SQL Server productivo. El repositorio no contiene backups ni connection strings reales.

Observar: correlación redacted, errores, latencia end-to-end, edad de cola, reintentos/cola muerta, duplicados, handoff, fallos envío, DB pool/locks y coste IA/media. Logs no contienen texto completo del chat, tokens, llaves o PII. Auditoría de acciones debe conservar actor/acción/resultado/referencia mínima con acceso y retención controlados.

Antes del piloto acordar numéricamente **RPO/RTO**, concurrencia, budgets y SLAs en P-012; no hay valores aprobados todavía. Crear runbooks para proveedor/DB/cola caída, revocación/rotación de claves, fallo envío incierto y reversión de release; responsable y contacto seguro definidos. Pausar automatización y preservar handoff cuando falte certeza de control, consentimiento o dato.

Backup no equivale a recovery: comprobar restauración y reconciliación de tareas/mensajes en SQL Server no productivo. Migraciones reversibles cuando sea posible; cambios destructivos necesitan plan de compatibilidad, respaldo/restauración y autorización propia. Validar carga sin comprometer SIIE antes de ampliar volumen.

