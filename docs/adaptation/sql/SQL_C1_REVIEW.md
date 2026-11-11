# SQL-C1 — Selector de base y estructura local observada

Fecha: 2026-10-24, America/Bogota. Resultado: selector implementado, conexión de metadatos y persistencia verificadas. P1 general sigue incompleta.

## Precisión del propietario

Se pidió una sección para elegir a qué base conectar, solicitando credenciales. La base disponible `HORARIOSSIIE` es un fragmento de DBSIIE. Esta precisión sustituye la suposición de que había una DBSIIE completa en el equipo. No se modifica ni clona el fragmento para suplir la base faltante.

## Función entregada

En [preview local](http://127.0.0.1:4173/#/settings), abrir **Ajustes → Base de datos**. Introducir servidor TCP, puerto, credenciales SQL y hostname del certificado; listar bases, elegir, probar y guardar. «Ver estructura» muestra tablas, columnas, tipos, nulabilidad y relaciones. El acceso existente ya está guardado cifrado para HORARIOSSIIE; dejar contraseña vacía permite reutilizarla para el mismo destino/usuario/TLS. Al cambiar esos campos se exige la credencial correspondiente.

El panel administra la conexión de inspección. **No activa el CRM contra la base elegida**. La UI lo indica desde el inicio, descarta resultados anteriores al probar/guardar y diferencia metadatos restringidos de una revisión con visibilidad completa. [ADR-014](../../decisions/ADR-014-database-selection.md) fija ese contrato y sus límites.

## Observación conectada

| Elemento | Resultado |
|---|---|
| Base / instancia | HORARIOSSIIE / SQLEXPRESS, confirmada como fragmento por el propietario |
| Motor local / edición / compatibilidad | 16 (SQL Server 2022) / Express 64-bit / 160 |
| Objetivo institucional | SQL Server 2019; no validado por esta lectura local |
| Tablas / columnas / FK | 50 / 437 / 41; las 41 FK tienen una pareja de columnas cada una |
| Visibilidad de metadatos actual | Base completa para el acceso usado; la UI avisa si otro acceso tiene visibilidad restringida |
| DBSIIE | No está entre las bases accesibles listadas con este acceso |
| Mapeos académicos presentes | dbo.GEPeriodo, dbo.ACProgramas, dbo.ACProgramaOfrecido, dbo.GEEstudiante |
| Mapeos académicos ausentes | dbo.ACAspirante, dbo.ACEscuela, dbo.ACModalidad, dbo.GEEmpleado |
| CRM base ausente | crm.Contact, crm.Conversation, crm.Message, crm.Operation |
| Aceptación de esquema / activación CRM | No evaluada / no activado |

Los nombres esperados proceden de los mapeos de catálogo/admisiones/identidad existentes, descritos en [CONNECTION_CONTEXT.md](CONNECTION_CONTEXT.md). Detectar ausencia no autoriza crear tablas académicas. La lista CRM de la UI es un indicador de cuatro tablas, no la aceptación de las 68 declaraciones del inventario.

La captura saneada [observed-schema.json](observed-schema.json) incluye tablas, columnas, FK y hash del código de consultas, sin credenciales, identidad de máquina ni filas de negocio. No incluye índices, defaults, CHECK, triggers ni todos los atributos requeridos para drift P1.3. Es una lectura secuencial de catálogos, no un snapshot consistente bajo DDL concurrente. No se leyó contenido de tablas de usuarios ni contraseñas académicas.

## TLS, Docker y archivos privados

El propietario ejecutó el helper elevado específico de SQLEXPRESS; se configuró el certificado local y luego el cliente original validó TLS y acceso SQL. No se desactivó validación ni se sustituyó automáticamente la identidad del guard legado. Se usa el PEM público actual, sin clave privada en Docker. No publicar los helpers/estado de `.local`, `.env`, perfiles ni claves.

Docker fue iniciado por autorización del propietario. Se reconstruyó la base desde el Dockerfile reproducible y la imagen de desarrollo desde esa base, conservando volúmenes. Se corrigió `.dockerignore` para excluir tests anidados del build de producto, cuyo setup ya se excluía. La versión de desarrollo anterior referenciaba una imagen base no disponible en este equipo.

Preview local en loopback: `local_demo`, salida IA desactivada; live 200 y ready 503 porque SQL CRM no está activado. La selección cifrada revisión 2 sobrevivió a recrear el contenedor, con nueva prueba TLS y descubrimiento exitosos. No se activaron envíos, proveedores ni otros proyectos Docker.

## Verificación y límites

- 89 pruebas backend aprobadas: 17 del selector/almacén/guard y 72 del contrato SQL existente. Incluyen rechazo de entradas y accesos inválidos, secreto no reflejado, TLS fijo, escaping ODBC, revisión, recuperación fallida de clave/perfil y cierre de conexiones.
- 3 pruebas frontend aprobadas: descubrimiento/guardado y limpieza de contraseña, cambio de destino/error, descarte de estructura anterior al volver a probar.
- TypeScript, ESLint del cambio, Ruff de los archivos nuevos y build de producto Docker (tsc/Vite) aprobados. El intento de suite backend general encontró fallos previos y no constituye una suite completa aprobada.
- Navegador real: selección guardada, prueba TLS, estructura y detalle de dbo.ACProgramas con relaciones, conservando Glass. Persistencia comprobada por HTTP tras recrear el contenedor.
- Cero DDL/DML, migraciones, restauraciones o cambios a tablas/datos SQL. Se escribieron únicamente configuración/certificado del host autorizados y perfil/artefactos locales.

Grafo observado: [HTML](../../../graphify-out/sql-observed/graph.html), [JSON](../../../graphify-out/sql-observed/graph.json), [manifiesto](../../../graphify-out/sql-observed/source-manifest.json): 529 nodos, 651 relaciones, 23 comunidades. El grafo de declaraciones sigue separado. Los helpers de grafos son offline y no actualizan la captura conectada por sí mismos.

## Próxima unidad

Obtener la copia completa o identificar el conjunto de bases que aporta SIIE; seleccionarla y capturar su esquema con el acceso correspondiente. Después contrastar forma final/índices/claves/permisos contra P1.3, preparar migraciones CRM explícitas y ensayarlas en copia restaurable antes de activar repositorios. No rellenar lo académico que falta ni declarar funcionamiento integral desde HORARIOSSIIE. El acceso remoto y la autenticación institucional son unidades pendientes.
