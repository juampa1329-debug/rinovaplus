# ADR-021 · Interfaz de Canales por capacidades

Fecha: 2026-10-25. Aceptada para el ensayo local SQL-C9 autorizado por el propietario; alcance limitado a UI/API de configuración y lectura.

Restaurar otra copia del C8 aceptado con perfil, login y ticket C9 propios. SIIE, C5, C7 y C8 se conservan. No hay migraciones. El perfil UI limita las escrituras a Account y Audit; sólo lee configuración/diario y datos de actividad, con SELECT de Channel/Kind en Credential, sin acceso al contenido cifrado ni clave de proveedores. No se conceden DML CRM, DDL, REFERENCES o INSERT en cola.

El manifiesto UI versionado v2 declara sólo Ajustes/Canales y capacidades locales conocidas. La aplicación valida el manifiesto antes de montar la composición. Una shell separada conserva tokens/componentes Glass y evita montar los hooks CRM/Inbox. No se reutiliza el instalador legacy de Canales, que incluye proveedores y transporte.

Se permiten consulta/guardado de configuración, etapas activas, comentarios de sólo lectura y actividad local. Credenciales, validación remota, activación, respuesta, reintento y recepción pública quedan fuera de la composición. Guardar mantiene revisión optimista, conserva borradores ante error y exige resolver cambios concurrentes. No se presume entrega por estados sintéticos heredados del ensayo.

La UI se sirve en un contenedor y origen loopback separados de C5. Su aceptación requiere pruebas backend/frontend, navegador en escritorio/móvil, rechazo de manifiestos incoherentes y operaciones no disponibles, persistencia real, concurrencia y preservación completa. SQL2019 institucional y la paridad general siguen pendientes.


Evidencia final: [informe C9](../adaptation/sql/SQL_C9_REVIEW.md), [validación](../adaptation/sql/sql_c9_validation.json), [progreso](../../tasks/sql-c9-progress.json). No acepta proveedores o SQL2019 institucional.


Precisión antes del cierre: estructura y funciones objetivo deben igualar Scentra, con estilo CBN y persistencia SQL Server. La organización de seis grupos se adopta; la paridad funcional permanece parcial. Ver [matriz de funciones y diferencias de modelo](../adaptation/sql/SQL_C9_SCENTRA_PARITY.md). No confundir placeholders/acciones deshabilitadas con flujos portados.
