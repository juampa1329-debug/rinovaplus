# Escuelas y modalidades: APIs y pantalla verificadas con DBSIIE

**Snapshot histórico A-024/P-036:** conserva el cierre de estas dos fuentes. La frontera actual añade programas con cuatro permisos de columna por aprobación posterior; [estado vigente A-025/P-037](programs-local-api.md). Las referencias siguientes a tres catálogos/cuatro rutas pendientes corresponden al momento de este cierre anterior.

**Fecha:** 2026-10-14, America/Bogota. **Estado:** A-024/P-036 completados exclusivamente para escuelas y modalidades; 12 escuelas y 2 modalidades reales verificadas en SQL/HTTP/navegador. **Autorización:** «Adelante con escuelas y modalidades. Amplía crm_catalog_reader con lectura solo de las tablas necesarias y prueba las APIs y la pantalla con datos reales, sin modificar tablas ni datos.» Se implementaron exclusivamente los GET `schools` y `modalities`, conservando períodos y los controles existentes.

DTOs `id`/`label`: `ACEscuela.Id_Escuela`/`NomEsla` y `ACModalidad.Id_Modalidad`/`Modalidad`; consultas fijas parametrizadas, orden por ID y paginación 25 (1–100)/offset 0 (0–10.000), sin COUNT/procedimientos. No se exponen Correo, UrlEscuela, Id_CstvoEmpld ni DescripcionMod. Guard exige únicamente las cuatro columnas nuevas y rechaza SELECT de tablas nuevas completas o columnas ajenas; PK propias se clasifican por tipo/parent en scope KEY, sin admitir OTHER.

React añade un selector finito Períodos/Escuelas/Modalidades, con una clave temporal en memoria y carga manual del recurso activo. Cambiar catálogo aborta/descarte obsoleto y limpia página/selección, sin auto-fetch; períodos conserva fechas/bit de origen. No cambios de diseño, configuración, dependencias, IAM o otros recursos.

**Checks después de normalizar:** Ruff formato/check y **103 pruebas backend** aprobados; `npm run check` completo con **74 pruebas frontend**, formato/lint/tipos/build aprobados. Dos pruebas nuevas fallaron inicialmente por reutilizar un Response mock consumido; se corrigió el fixture para generar un Response por fetch, y el check final aprobó. No se cambiaron reglas de producto para resolver ese error.

## Permisos mínimos ampliados y comprobados

El coordinador ejecutó dos GRANT dentro de una transacción confirmada, con **cuatro permisos de columna** y cero grants completos sobre las tablas nuevas:

```sql
GRANT SELECT ON OBJECT::dbo.ACEscuela (Id_Escuela, NomEsla) TO crm_catalog_reader;
GRANT SELECT ON OBJECT::dbo.ACModalidad (Id_Modalidad, Modalidad) TO crm_catalog_reader;
```

La identidad/SID y contraseña existentes no cambiaron; cero identidades nuevas, roles vacíos y nueve DENY anteriores conservados. Permisos efectivos nuevos: cuatro columnas DTO en 1; SELECT completo de cada tabla nueva en 0; Correo/UrlEscuela/Id_CstvoEmpld/DescripcionMod en 0; INSERT/UPDATE/DELETE/ALTER/CONTROL/EXECUTE y fuentes de los próximos catálogos en 0. PUBLIC de servidor/base y esquema de negocio intactos; **cero modificaciones de tablas/datos**. El secreto DPAPI CurrentUser existente permanece privado e ignorado, sin texto plano persistido.

El adaptador actual `SqlCatalogReader` conserva tres métodos fijos `read_periods`, `read_schools`, `read_modalities`, una capacidad SQL compartida y configuración/TLS anteriores. El guard requiere flags `[0,0,0,0,1,1,1,1,1]` y revisa tuplas `(scope, permission, column)`: períodos conserva su permiso previo, escuelas/modalidades únicamente sus dos columnas y KEY exclusivamente SELECT vacío para PK de padres aprobados. `subentity_name` nulo se normaliza a vacío en metadata; eso no admite SELECT completo de las nuevas tablas.

Fuentes oficiales del control por columna: [GRANT de permisos de objeto](https://learn.microsoft.com/en-us/sql/t-sql/statements/grant-object-permissions-transact-sql?view=sql-server-ver17), [HAS_PERMS_BY_NAME](https://learn.microsoft.com/en-us/sql/t-sql/functions/has-perms-by-name-transact-sql?view=sql-server-ver17) y [sys.fn_my_permissions](https://learn.microsoft.com/en-us/sql/relational-databases/system-functions/sys-fn-my-permissions-transact-sql?view=sql-server-ver17).

## Aceptación real por capa

| Capa | Resultado comprobado |
|---|---|
| SQL/TLS | Adaptador: 32 períodos, 12 escuelas y 2 modalidades; proyección validada, orden estable y sin solapamiento, sin persistir filas completas. Certificado validado, ODBC 18 `18.06.0002`, `encrypt_option=TRUE`, Shared memory. |
| Guard real | Once casos CASE ejecutados en SQL Server distinguen tablas/PK aprobadas de triggers/objetos ajenos; cinco negativos inyectados rechazan tabla nueva completa, columna extra, OTHER y escritura de KEY. Sin ampliar permisos para resolver pruebas. |
| HTTP | **31 casos aprobados** entre las tres rutas: listas/páginas/vacío, 401, 422 límite/duplicados/desconocidos/no enteros, salud, CORS y rechazo de Host. Envelope/DTO exactos; `/health/ready` permanece 503. |
| Navegador | IAB escritorio: 12 escuelas y 2 modalidades seleccionables por ID; cambio de recurso limpia página/selección sin auto-fetch, clave compartida solo en memoria. Clave incorrecta 401 genérico; salir a Resumen y volver borra la clave. Regresión períodos 25+7 y fechas/bit originales. |
| Móvil | Viewport emulado 390×844 sin overflow en escuelas/modalidades, incluida etiqueta larga de escuela. No equivale a teléfono físico. |
| Inmutabilidad | **41/41 hashes** fuente/pruebas coinciden con el freeze final. Dependencias/configuración intactas; ningún cambio de fuente tras checks y QA. |

Evidencias saneadas ignoradas: `.local/school-modality/live-qa.json`, `runtime-qa.json`, `source-freeze.json` y `browser/qa.json`. Capturas: `schools-desktop.png`, `modalities-desktop.png`, `schools-mobile.png`, `modalities-mobile.png`, `periods-regression.png` dentro de `browser/`. No secretos, stacks o filas completas en informes. Runtime nuevo propio en 8013/5193, identidad/procedencia comprobadas; no reutilizar PIDs de intentos anteriores. Entrega abierta en `http://127.0.0.1:5193/#/knowledge`, Escuelas seleccionada.

## Continuación y límites

P-035 conserva su cierre histórico de períodos; la frontera de lectura actual es la descrita aquí, con tres catálogos. Siguen propuestas cuatro rutas de programas/ofertas/jornadas y requieren contrato/permiso/aceptación propios. Fase 1 completa, IAM empresarial, datos personales, escrituras, producción y publicación no se aprueban por este cierre.

Si se autoriza revertir solo esta ampliación, retirar exclusivamente los cuatro grants de columna añadidos y revalidar el corte anterior de aplicación; conservar identidad, contraseña, nueve DENY y permisos previos. No retirar la cuenta existente ni cambiar PUBLIC para revertir esta unidad.
