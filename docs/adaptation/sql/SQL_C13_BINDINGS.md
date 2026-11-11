# C13 · Preparación del enlace académico

HORARIOSSIIE sigue siendo el fragmento autorizado de DBSIIE. Se conserva su catálogo observado y las 50 tablas académicas, sin modificar nombres, datos o relaciones. La copia general usa únicamente los contratos CRM aceptados; no interpreta la ausencia de un vínculo académico como una matrícula, un estudiante o un programa inexistente.

El propietario confirmó que indicará los nombres y las tablas equivalentes cuando estén disponibles. Por ahora se cierra el sprint C13/P1.4 y se continúa con P2 en copias independientes; el cierre SQL2019 de P1 queda visible como pendiente.

La plantilla [academic-bindings-c13.json](academic-bindings-c13.json) identifica cada referencia académica de los consumidores y su presencia en el fragmento. Es un documento de preparación; no redirige consultas ni admite SQL libre. Las columnas observadas sirven para contrastar candidatos. Un nombre parecido no demuestra equivalencia de identidad o reglas.

Para aceptar un enlace se comprobarán:

1. Base e identidad del servidor, TLS y permiso de lectura del objeto exacto.
2. Tabla, columnas, tipos, longitud, nulabilidad y clave estable de la entidad.
3. Relación padre/hijo, cardinalidad, significado de estados y vigencia del registro.
4. Consulta acotada con parámetros, aislamiento y resultado de muestra autorizado.
5. Un contrato, perfil y pruebas nuevos antes de activar al consumidor correspondiente.

No se renombra una tabla académica, se crea una tabla ficticia o se cambia un guard histórico para hacer pasar un consumidor. Los aliases futuros pertenecerán al adaptador validado. El motor local continúa siendo SQL2022 Express/160. Un respaldo nativo de ese motor no puede utilizarse como si fuera una restauración SQL2019; la transferencia lógica requerirá tratar IDENTITY, columnas calculadas y rowversion y ensayar su propia restauración.

La aprobación de operación de la institución pertenece a P11. El ensayo técnico de una copia SQL2019 y sus migraciones sigue siendo el criterio P1.close, separado del sprint Docker P1.4 y de la autorización para preparar P2.
