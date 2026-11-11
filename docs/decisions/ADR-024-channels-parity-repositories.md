# ADR-024 · Integración B011 y repositorios C12 aislados

Estado: aceptada en el ensayo local solicitado, 2026-10-25. Alcance: una restauración independiente, SQL2019 como objetivo institucional pendiente.

Se conserva el release C11 y sus89 tablas. La importación B011 es DML atómico con unidad/bindings/auditoría propios; no añade unidades al diario DDL de17 filas. No se aplican scripts históricos sobre una base poblada.

Cada fila fuente conserva su firma SQL binaria y una correspondencia determinista por institución/clave. Las identidades externas conservan BIN2 y su namespace. La etapa se enlaza al contrato B006 existente. La ausencia de ID externo o ruta de envío se representa como borrador pendiente/cuarentena; nunca como identidad fabricada, entrega o verificación real.

El recifrado exige la clave original autenticada. Bóveda y cuerpos usan claves distintas; propietarios AAD canónicos y versiones explícitas. Las claves quedan fuera del perfil de runtime y de la API. El importador WITHOUT LOGIN tiene permisos de inserción acotados; el runtime tiene permisos propios por tabla/columna y ninguna escritura en las tablas anteriores.

Se usa una composición ASGI separada y una capacidad privada de propietario local para este ensayo. No es identidad institucional ni sustituye P2. El guard fija SID, contexto, catálogo/ACL/propietarios y diario, permitiendo únicamente los datos mutables del contrato nuevo. Revisión, idempotencia y auditoría de cambios locales comparten transacción; no hay efectos HTTP de proveedores.

La reversión se demuestra restaurando el respaldo C11 en otra base y comparando catálogo/datos completos. No hay DOWN destructivo, borrado de fuentes o reseteo de IDs. C5/C9 conservan sus archivos, bases, tickets y previews.

Por petición humana se reportan porcentajes por fase mediante criterios canónicos completos; no se asignan porcentajes intuitivos al software. Los subconjuntos C12 son evidencia parcial de P4, no su cierre. Ver [informe C12](../adaptation/sql/SQL_C12_REVIEW.md) y [contrato de medición](../adaptation/phase-progress-contract.json).
