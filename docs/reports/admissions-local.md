# Primer corte de admisiones con información real

Fecha: 2026-10-15. Entorno: copia local autorizada DBSIIE/SQLEXPRESS. Rama de trabajo existente: `codex/integracion-coolify`. Sin publicación Git ni despliegue externo.

## Alcance implementado

La instrucción del propietario autoriza comenzar admisiones del período 2026-B con estudiantes existentes para evitar duplicados, selección de período y datos reales. El módulo **Admisiones** consulta aspirantes de SIIE; el período predeterminado se obtiene exclusivamente del único registro de `GEPeriodo.EstadoPeriodo = 1`. Ni el texto 2026-B ni su ID están codificados en el producto. Si no hay un activo único, se exige selección explícita; nunca se consulta todo el histórico como alternativa.

Listado de 25 aspirantes por página, búsqueda parametrizada por nombre/documento y detalle bajo demanda. El cambio de período o búsqueda reinicia la página; respuestas anteriores no sustituyen la selección actual. La consulta utiliza `ACAspirante.Id_Periodo`, no el período de su oferta. La ficha expone la diferencia y no corrige registros históricos automáticamente. Aspirantes sin período no se incluyen artificialmente en un período seleccionado.

| Dato | Fuente y semántica |
|---|---|
| Aspirante y período solicitado | `ACAspirante.Id_Aspirante` / `Id_Periodo` y `GEPeriodo`; clave institucional conservada |
| Oferta y programa | `ACAspirante.Id_PrgOfrecido` → `ACProgramaOfrecido` → `ACProgramas`; período de oferta independiente |
| Jornada del programa | `ACProgramas.Id_Jornada` → `ACJornada`; no implica disponibilidad de cupos ni jornada elegida por aspirante |
| Jornadas de la oferta | `ACDetalleJornada`; ausencia de relaciones se presenta explícitamente, sin usar la jornada del programa como reemplazo |
| Estudiantes existentes | `GEEstudiante.TipoId` y documento con espacios exteriores retirados; comparación exacta binaria, conserva ceros/puntuación. Se consulta todo el historial para ese documento, sin restringirlo al período del aspirante |
| Seguimiento histórico | `ACSeguimiento`, paginado por fecha e ID, con estado de `ACEstadoSeguimiento`; solo lectura, notas visibles hasta 4.000 caracteres con aviso de truncamiento |
| Seguimiento nuevo | Tablas `crm_admissions`; notas propias, estado del catálogo SIIE y próxima fecha opcional; origen CRM explícito |

Las coincidencias de estudiantes son candidatos para revisión, no identidad resuelta. No se fusionan personas, crean estudiantes ni registran matrículas. Documento vacío o tipo de identificación desconocido impiden la comparación y se informan. Estados del seguimiento como «Matriculado» son etiquetas del catálogo y no acreditan ni ejecutan matrícula académica.

## Persistencia y preservación

Migración explícita `backend/migrations/002_local_admissions.sql`, sin DDL al iniciar la aplicación. El esquema separado contiene `AdmissionCase` (UUID y `AspirantId` único), `Followup` (nota/estado/fecha/revisión) y `Operation` (identidad idempotente y hash). Se valida origen/estado desde el servidor. Las referencias institucionales tienen columnas tipadas; no se guardan en JSON arbitrario ni se copia población completa.

Se reutilizan transacciones, bloqueo de escritura y TLS estricto del repositorio local existente. Huella y versión propias protegen el nuevo esquema sin modificar el contrato ADR-006 ni las cuatro tablas CRM. Una primera nota crea su caso atómicamente; editar exige revisión vigente; el mismo ID de operación/payload puede reintentarse sin duplicar. Un conflicto preserva el borrador y permite revisar la versión vigente. Borradores separados por período/aspirante permanecen en la pestaña al cambiar de ficha o módulo; no se almacenan en almacenamiento persistente del navegador.

No hay creación automática de contactos/conversaciones al consultar. Por ello, navegar admisiones no aumenta el snapshot de Clientes/Inbox ni cruza sus límites 500/2.000. La API sintética `/api/local/clients` deja de instalarse en `local_sql_copy`; pruebas y otros modos históricos permanecen separados.

La migración aplicada y repetida preservó metadatos core y conteos de negocio; únicamente el trigger existente de auditoría DDL añadió siete filas autorizadas, conservadas. Conteos de las cuatro tablas CRM preservados. Respaldo y restauración anteriores comprobados y su existencia verificada antes de aplicar. No se deshabilitó el trigger ni se alteraron credenciales.

## Verificación

- Backend final: **354/354** pruebas aprobadas (admisiones, SQL workspace, clientes y contratos), Ruff formato/lint y exportación canónica correctos. La ejecución normal de TestClient quedó bloqueada por sockets/temporales del sandbox Windows; ejecución nativa aislada aprobada, con IO real prohibido por fixtures.
- Frontend: **20/20** pruebas focalizadas aprobadas, incluidos borradores por entidad. La suite completa registró **159 aprobadas y un fallo** por una aserción antigua de 13 enlaces tras agregar Admisiones; se actualizó para comprobar el inventario vigente y la visibilidad del acceso principal, y el archivo pasó **3/3**. No se presenta como una segunda suite completa. Formato, lint, tipos y build aprobados.
- SQL real: listado/período, páginas disjuntas, detalle y catálogo; una nota técnica propia confirmó COMMIT y lectura desde nueva conexión, edición, reintento idempotente y conflicto. Limpieza limitada por UUID y contenido de propiedad verificados; conteos originales restituidos, sin registros ficticios finales. El primer harness usó un host Docker desde Windows; se corrigió solo su endpoint nativo manteniendo validación TLS.
- HTTP→SQL real: repitió la prueba a través del contenedor privado, con lectura, COMMIT confirmado desde nueva conexión SQL, edición, retries, conflicto 409 y limpieza de los UUID técnicos propios. No quedan registros ficticios. Evidencia: `.local/admissions-20261015/http-result.json`.
- Docker Linux AMD64 reconstruido y contenedor existente actualizado en `http://127.0.0.1:4173/#/admissions`: healthy, snapshot Clientes/Inbox idéntico, volumen IA idéntico, router sintético ausente y catálogo/listado reales disponibles. Imagen `sha256:c2a3b9bd89e9ca0a0becadd5baa1988938f41bf8a56104576f0e581d06ffc2aa`; siete comprobaciones finales en `.local/admissions-20261015/docker-final.json`.
- Evidencia saneada local adicional: `.local/admissions-20261015/migration-result.json` y `repository-result.json`. La lectura focalizada tomó 563 ms directamente y 688 ms por HTTP en esas ejecuciones; no es un SLA ni benchmark de concurrencia.

- Navegador real: período inicial 2026-B/128 derivado de SQL, 25 filas y página siguiente; selección 2026-A/127 reinicia a página 1 y restringe las filas, regreso a 2026-B. Ficha con regiones de coincidencias, historial y seguimiento comprobadas. Borrador sin guardar conservado al cambiar de período y reabrir al mismo aspirante; retirado después sin guardarlo. Búsqueda sin coincidencias muestra cero resultados sin fixtures; sesión devuelta al período activo y búsqueda vacía. Sin desbordamiento horizontal en 390 × 844 y 1440 × 1000, con ficha montada. Evidencia saneada: `.local/admissions-20261015/browser-result.json`; captura del estado vacío sin registros personales: `browser-empty-state.jpg`.

La aceptación del navegador fue de lectura e interacción con borradores; la persistencia está acreditada separadamente por SQL y HTTP. No se confunde viewport móvil con prueba en teléfono físico. Una captura recortada defectuosa del navegador se descartó; no fue un defecto de la aplicación.

## Límites y siguiente unidad

Este corte incorpora consulta y seguimiento CRM. No crea aspirantes en el core ni modifica los existentes; ese contrato de admisión requiere una unidad posterior con reglas y transacciones del SIIE comprobadas. No hay fusión automática, matrícula, envío externo ni IA sobre datos personales. No se agregaron índices al core: el rendimiento de búsquedas documentales/historial deberá reevaluarse con carga concurrente y volúmenes reales, antes de proponer índices específicos.

El acceso sigue siendo privado local, con operador local y sin RBAC empresarial; esa capa precede el acceso compartido. Próximo corte: resolver contrato de alta/actualización de aspirantes, campos obligatorios y relación con oferta/jornada; después recepción de solicitudes y revisión académica. El período de aspiración y la oferta deben conservar su significado separado.

Reversión conservadora: retirar la ruta/módulo y conservar las tres tablas y sus datos. No ejecutar eliminación del esquema con notas confirmadas. Una retirada física posterior exige exportación/restauración comprobada o verificación explícita de que las tablas siguen vacías. No borrar auditoría DDL ni historial SIIE.
