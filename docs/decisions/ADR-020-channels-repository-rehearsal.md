# ADR-020 · Repositorios Canales con perfil de ensayo propio

Fecha: 2026-10-25. **Aceptada en SQL-C8 sólo para repositorios y API local de ensayo.** Autorizada por el propietario; preview compartido C5 conservado.

Continuación de ADR-019: restaurar otra copia del trial C7 aceptado, sin modificar HORARIOSSIIE, C5 o C7. Perfil cifrado, login y ticket nuevos; TLS validado. El guard C8 compara identidad, catálogo completo visible, ACL directa/efectiva y diario inmutable. No exige CONTROL ni congela datos de negocio, que pueden crecer en el ensayo.

El lector reutiliza consultas canónicas congeladas y normaliza antes de ordenar. Se exige VIEW DEFINITION y se verifica igualdad exacta de catálogo administrativo/runtime al preparar. El ticket fija esa forma, SID y diario; no se heredan tickets ni se excluyen prefijos desconocidos. La aplicación no recibe DDL, REFERENCES, escritura al diario, impersonación o DML académico. Los permisos se conceden por tabla y operación, incluidos sólo los DML foundation necesarios para ingestión local sintética.

La composición C8 monta sólo configuración y lecturas locales. Los helpers de recibos, ingestión, comentarios y estados se ensayan con datos sintéticos sin arrancar workers ni proveedores. enqueue_message requiere MessageRoute/B015 y queda bloqueado; la cola no recibe INSERT del runtime C8. No se montan recepción pública de webhooks, discovery, activación, reply ni reintentos. La clave AES de Canales es independiente y preparada antes del ensayo, nunca compartida con C5.

Pruebas requeridas: TLS/destino/perfil inválidos, permisos directos y efectivos, metadatos incompletos/drift, diario alterado, transacciones/rollback, credenciales cifradas y redacción, revisiones concurrentes, idempotencia, crecimiento legítimo del CRM sin invalidar guard y preservación completa de fuente/C5/academia. Reversión: detener composición C8 y conservar copia/evidencia; no down migration ni redirección de C4.

Verificación: 189 pruebas offline (44 nuevas), 38 comprobaciones conectadas y Ruff. Login propio con 33 GRANT mínimos, incluido SELECT de la vista de dependencias, y siete DENY dbo. Catálogo administrativo/runtime exactamente iguales; diario heredado7 y 199 registros CRM previos conservados; cuatro registros sintéticos CRM nuevos. La primera preparación incompleta se retiró con login deshabilitado y otra restauración. No hubo migraciones, DML académico, proveedores o workers. API probada con TestClient/SQL en Docker; sin otro servidor ni cambio del preview C5. [Informe, evidencia y límites](../adaptation/sql/SQL_C8_REVIEW.md).

SQL-C9 abordará UI por capacidades y permisos de CRM/Inbox en otra composición de ensayo; ampliar ACL exige nuevo perfil/ticket y pruebas. El contrato C8 y el guard C4 no se redirigen ni se flexibilizan para habilitar módulos pendientes.
