# ADR-018 · Extensión CRM con partición explícita

Fecha: 2026-10-25, America/Bogota. **Propuesta técnica revisada en SQL-C6; implementación y aceptación conectada pendientes.** Continúa [ADR-017](ADR-017-foundation-ui-capabilities.md) y conserva su runtime C5.

## Problema

La copia restaurada tiene siete tablas foundation y CRM poblado. Su lector/guard congelado separa managed de académicas por tres esquemas. Ampliarlo por prefijos ocultaría objetos desconocidos y modificarlo reescribiría evidencia C3/C4/C5. Los consumidores legacy tienen dependencias que no aparecen en las FK de sus migraciones.

## Propuesta

El siguiente paquete es `CBN-channels-local-v1` propuesto: B011 sintetiza 011+012 en forma final, con ocho tablas vacías y diez FK exclusivamente CRM. Se implementará y ensayará en una restauración independiente del estado poblado C5. SQL-C6 sólo define el contrato.

Un lector/guard nuevo distingue tablas académicas enumeradas, foundation existente, extensión enumerada y objetos desconocidos. Congela también objetos no tabulares, dependencias, ACL y datos preexistentes; metadatos incompletos bloquean. No modifica los helpers, release, snapshots o prueba C3/C4/C5, ni excluye schemas por prefijo. Las 50 tablas académicas y siete foundation no reciben DDL; sólo se añaden ocho tablas en otro destino de ensayo.

El diario mantiene su esquema y prefijo de cinco filas; incorpora eventos de la extensión mediante una cadena de releases explícita. La nueva herramienta conserva locks, STARTED durable, COMMITTED atómico con DDL y reconciliación de cualquier COMMIT incierto. No vuelve a ejecutar instalación vacía ni adopta un esquema parcial.

No se añaden permisos al login C4 ni se cambia su ticket/destino. Preparación, migración, evidencia administrativa y runtime se separan. Sólo se permite DDL de objetos enumerados y REFERENCES CRM necesarios; se prueban permisos efectivos y efectos indirectos. TLS sigue validado. El runtime de siete tablas rechaza la extensión; su integración requiere otra aceptación.

Crear Canales no activa rutas, cuentas, credenciales, webhooks, workers, comentarios UI ni transporte. B015 y luego B018 preparan Inbox y churn/campañas; evaluación propuesta apagada. B013 es una rama independiente. B007/B008 y los consumidores ligados a SIIE siguen condicionados a sus fuentes y servicios reales. No hay WooCommerce o billing.

## Opciones consideradas

- Añadir todas las tablas candidatas juntas: aumenta el ensayo y no resuelve dependencias funcionales ausentes.
- Activar identidad/unificación por sus FK CRM: no cubre consultas SIIE ni `crm_inbox.Operation`.
- Modificar el lector y hashes C3: altera la evidencia histórica y puede ocultar drift.
- **Paquete B011 pequeño y contrato nuevo por objetos:** mantiene continuidad y prepara las capacidades solicitadas sin inventar SIIE.

## Evidencia y aceptación

[SQL_C6_REVIEW](../adaptation/sql/SQL_C6_REVIEW.md), [plan](../adaptation/sql/crm-extension-plan.json) y [validación offline](../adaptation/sql/sql_c6_validation.json). SQL-C7 implementará contratos/snapshots/DDL y comprobará la matriz de preservación, permisos, concurrencia, drift y recuperación en otra restauración. SQL-C8 integrará runtime/UI; el preview C5 permanece igual durante C7. La aceptación institucional SQL2019, RBAC y módulos restantes siguen pendientes.
