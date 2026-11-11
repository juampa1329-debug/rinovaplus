# P2 · Ajustes e identidad institucional

Estado: implementación autorizada en curso, 26 de octubre de 2026. No es una aceptación ni cambia porcentajes.

El propietario pidió completar toda P2. La implementación usa otra restauración de C13, un perfil y principal nuevos, una entrada web propia y el estilo Glass vigente. Las fuentes y evidencias C3–C13, Scentra y las tablas académicas anteriores se conservan.

Precisión de presentación del propietario (2026-10-26): «ensayo», códigos de sprint y detalles de persistencia no pertenecen a la interfaz final. Esos identificadores se conservan en documentación, herramientas y evidencias técnicas. El producto muestra CRM CBN, nombres normales de secciones y estados reales de configuración. Las capacidades todavía sin implementar deben indicarse con lenguaje claro, sin simular funcionamiento. La entrada 4173 sigue siendo C5; esta decisión no significa que su interfaz histórica ya se haya actualizado ni que P2 esté publicada.

Estado intermedio: consultar [P2_CHECKPOINT.md](P2_CHECKPOINT.md). Hay 38 pruebas puras de identidad/validación/perímetro aprobadas; todavía no hay perfil, migración de acceso, UI o listener P2 aceptados. La calificación SQL2019 usa ahora un fixture separado de sólo CRM: no es una copia académica restaurada ni aceptación de DBSIIE. Una regla temporal académica impidió transferir el fragmento sin alterar su confianza; se conservó y se detuvo esa transferencia. P1.close y todos los porcentajes permanecen pendientes de sus pruebas completas.

1. P2.1: perfil institucional y personal; ajustes IA completos, proveedores/modelos, canales y webhooks. Guardado validado, revisión optimista y secretos cifrados. Se conserva la selección aunque no se ejecute un diagnóstico externo.
2. P2.2: cuentas humanas separadas de contactos, empleados y agentes; contraseñas derivadas con KDF estándar, sesiones opacas revocables en SQL, roles y acciones, confirmación de contraseña, TOTP y recuperación. No portar el fallo de revocación de los access JWT de referencia.
3. P2.3: disponibilidad institucional explícita y cuotas técnicas. No hay planes, trial, suscripciones, checkout, WooCommerce ni cobro del software. Disponibilidad solicitada y preparación operativa son estados distintos.
4. P2.4: matriz exhaustiva método/ruta/acción, permisos comprobados dentro de la transacción, auditoría append-only, protección del último administrador y pruebas de acceso directo/concurrencia.
5. Cierre: persistencia tras reinicio, revocación efectiva, ausencia de datos secretos en respuestas/logs, recuperación y reversión conservando cuentas y auditoría.

P2.close depende de P1. Se preparará un ensayo auténtico en SQL Server 2019 con TLS, contratos aceptados, respaldo/restauración, conflictos y drift. No se reducirá ese criterio ni se aceptará un cambio de compatibilidad de SQL2022 como motor2019. Una transferencia lógica del fragmento sólo puede escribir nuevas copias; cualquier regeneración de rowversion debe declararse y no sustituye la preservación íntegra de la fuente original.

La API nueva no importará los routers SaaS acoplados a billing ni helpers que crean tablas al primer uso. Las migraciones serán explícitas, con diario durable y principal sin login acotado. El runtime no tendrá DDL ni UPDATE/DELETE sobre auditoría.

La interfaz del producto no mostrará «ensayo», códigos de fase ni instrucciones internas. La preparación pendiente de una función se explicará en lenguaje del usuario. La documentación técnica sí conservará el contexto y las limitaciones comprobadas.

Referencias de lectura: [inventario de ajustes](../fragments/p2-settings-source.draft.json), [identidad de referencia](../fragments/p2-auth-source.draft.json), [cierre C13](SQL_C13_REVIEW.md). Los borradores semánticos no acreditan paridad implementada.
