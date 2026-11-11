# Ejecutar los catálogos académicos locales

Los GET `periods`, `schools`, `modalities` y `programs` y su cliente React están verificados con **32 períodos, 12 escuelas, 2 modalidades y 228 programas reales**. `crm_catalog_reader` conserva SELECT previo de GEPeriodo y nueve DENY; solo columnas DTO autorizadas de ACEscuela/ACModalidad/ACProgramas, sin SELECT completo de esas tres tablas. Tablas/datos/PUBLIC intactos; la aplicación no provisiona cuentas ni amplía permisos. Una cuenta elevada sigue bloqueada antes de filas.

## Ejecución protegida

Trabajar únicamente en `C:\Users\Developer_PC\.codex\worktrees\f615\CRM_CBN`, rama `feat/sqlserver-python-api`.

1. Mantener `CRM_APP_MODE=local_demo` para el diseño aislado: catálogo y `/health/ready` devuelven 503.
2. Para el corte autorizado, configurar privadamente `CRM_APP_MODE=local_readonly_catalog` y `CRM_CATALOG_TOKEN`, aleatoria alfanumérica de al menos 32 caracteres. `.env.example` es documentación y no se carga automáticamente. No guardar valores reales en Git/logs/capturas.
3. Usar el lector autorizado. Su secreto SQL está protegido con DPAPI CurrentUser y ACL exclusiva en el directorio privado ignorado; el helper lo recupera únicamente en memoria. Una identidad Windows restringida o cuenta SQL existente suministrada privadamente sigue siendo alternativa admitida por configuración; no usar la cuenta administrativa como reemplazo.
4. Desde `backend`, ejecutar `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log`. Desde `frontend`, ejecutar `npm run dev` y abrir `http://127.0.0.1:5173/#/knowledge`.
5. En **Catálogo académico**, elegir Períodos/Escuelas/Modalidades/Programas, ingresar manualmente la clave temporal y cargar. La clave se comparte solo en memoria de esta vista. Cambiar recurso limpia página/selección y cancela respuestas anteriores, sin cargar automáticamente; salir y volver borra la clave. No existe fallback ficticio de negocio.

En Programas, **Cargar filtros** obtiene todas las opciones de escuela y modalidad secuencialmente (máximo 1.000 por fuente, falla ante exceso/deriva sin truncar). «Todas» omite ese filtro; seleccionar no ejecuta consulta. **Cargar programas** busca manualmente; ambos filtros se combinan por AND. Paginar conserva filtros; cambiarlos cancela/limpia resultados y vuelve a offset cero. Las opciones muestran `ID n · nombre` para distinguir nombres repetidos, incluso en móvil. NULL/vacío se presenta como `ID n · Sin nombre` sin cambiar el DTO; esos casos se probaron sintéticamente, no aparecen en la muestra real actual.

QA aislado puede usar backend 8013/frontend 5193: `VITE_CATALOG_API_BASE_URL=http://127.0.0.1:8013` y `CRM_CATALOG_ORIGINS=http://127.0.0.1:5193,http://localhost:5193`. Solo orígenes HTTP loopback explícitos se aceptan. Iniciar procesos propios; no reutilizar PIDs de la carpeta original. Detener con Ctrl+C.

## Recuperar el backend local autorizado

La entrega actual está abierta en `http://127.0.0.1:5193/#/knowledge`, con backend propio en 8013. No lanzar otro proceso sobre ese puerto mientras siga activo. Para un reinicio posterior, comprobar/detener únicamente el proceso propio y liberar 8013; desde la raíz del worktree:

```powershell
& '.\backend\.venv\Scripts\python.exe' '.\.local\periods\launch_reader.py'
```

El helper privado solicita una clave de operador por entrada oculta, o usa `CRM_CATALOG_TOKEN` ya suministrada privadamente al proceso. Recupera el secreto SQL DPAPI solo en memoria y abre el backend oculto en loopback, sin access logs. El único argumento mostrado es la ruta del helper: no incluir claves/contraseñas en comandos. Registrar PID solo en el manifiesto ignorado. La contraseña SQL nunca se ingresa en la interfaz; esta recibe únicamente la clave de operador temporal.

El runtime vigente está identificado en `.local/programs/runtime-qa.json` y comprobado en `final-qa.json`, con propiedad de procesos/puertos validada. No usar PIDs históricos de `.local/periods/` o `.local/school-modality/` para controlar los procesos actuales. Si se reinicia mediante el helper, comprobar el nuevo manifiesto que produzca y el PID/puerto propios antes de futuras acciones.

La carpeta y blob privados tienen ACL sin herencia y acceso exclusivo del usuario Windows actual. No copiar, mostrar o publicar secretos/blob; no crear `.env` con contraseña en texto plano. Si cambia la cuenta Windows o se pierde el blob, solicitar recuperación/rotación administrada por el propietario. La guía privada adicional es `.local/periods/reader-private-runbook.md`; estos artefactos quedan fuera de Git. La clave sintética de QA debe sustituirse para uso privado posterior, sin publicarla aquí.

## Contrato implementado

| Aspecto | Resultado |
|---|---|
| Entrada | `limit=25`, rango 1–100; `offset=0`, rango 0–10.000. Query desconocida/duplicada/no entera/fuera de rango: 422 antes de SQL. |
| DTO | `id`, `label`, `startDate`, `endDate`, `sourceState`. Fechas ISO originales y bit sin inferir inscribible/año actual/estado activo. |
| DTO nuevos | Escuelas y modalidades: únicamente `id`/`label`; no contacto, URL, empleado o descripción adicional. |
| Program | Exactamente `id`, `label` nullable, `schoolId`, `modalityId`; IDs SQL int32 y nombre fuente, sin código/jornada/fecha/semestres. |
| Filtros Program | `schoolId?`/`modalityId?`, enteros ASCII firmados incluidos cero/negativos, rango SQL int32. Omitidos → NULL; combinación AND; inexistente → 200 vacío. Duplicados/vacíos/otros formatos → 422; otras rutas rechazan estos filtros. |
| Consultas | Períodos: cinco columnas explícitas de GEPeriodo; escuelas: Id_Escuela/NomEsla; modalidades: Id_Modalidad/Modalidad; programas: Id_Programa/NombrePrograma/Id_Escuela/Id_Modalidad, CAST de parámetros nullable y filtros AND. Orden fijo por cada ID, `?`, `limit+1` para `hasMore`, sin COUNT o procedimientos. |
| HTTP | Bearer de operador local comparado en tiempo constante, alcance fijo `catalog:read`; 401 sin credencial válida. No hay usuarios, sesiones empresariales, roles ni 403 por RBAC implementado. |
| SQL | Guard de roles/permisos efectivos antes de filas. Rechaza cuentas elevadas, roles amplios, escritura/control/ejecución/impersonación y SELECT de otros objetos/columnas. Nuevas tablas no admiten SELECT completo. |
| Transporte | pyodbc 5.3.0 + ODBC Driver 18, destino local fijo, cifrado y certificado validado sin bypass. |
| Capacidad | Una lectura simultánea por proceso, ocupado 503; sin pool/reintentos/caché. Login y cada consulta tienen timeout de cinco segundos. No se acredita todavía un plazo SQL total o cancelación del servidor al abortar UI. |
| React | Validación runtime, selección por ID, páginas de 25, carga/vacío/error/reintento, AbortController/descarte obsoleto y espera máxima UI de diez segundos. |
| Errores | 401/422/503 y 500 inesperado: código, mensaje genérico y correlación nueva; sin SQL, identidad, cadena de conexión, stack o contenido del error original. `Cache-Control: no-store`. |
| Salud | `/health/live` acredita proceso/modo; `/health/ready` permanece 503, integraciones completas pendientes. |

`readonly=True` de ODBC es una defensa adicional, no una garantía de permisos. La cuenta mantiene SELECT de GEPeriodo, dos columnas DTO de escuela y modalidad y cuatro de programas, más metadata pública inocua. Un permiso adicional no reconocido bloquea; nunca se amplía automáticamente.

Composición actual: `SqlCatalogReader` en `backend/app/modules/catalog/infrastructure/sql_reader.py`, métodos fijos `read_periods`, `read_schools`, `read_modalities`, `read_programs`; estado `app.state.catalog_reader`. El guard comprueba trece flags y tuplas `(scope, permission, column)`; escuela/modalidad/programa exigen columna autorizada, y PK propia usa KEY solo para SELECT sin columna, por tipo/parent. No se aceptan SELECT vacío de tabla nueva, columnas extra, OTHER o triggers. Salud/readiness conservan su contrato independiente.

## Corte cerrado y continuación

[Informe vigente A-025/P-037](../reports/programs-local-api.md): 139 pruebas backend, 83 frontend/checks, catorce CASE reales/seis negativos de guard, 31 HTTP/diez escenarios de filtros y tres GET finales; IAB escritorio/móvil final. Períodos/escuelas/modalidades/programas completados exclusivamente para sus cortes. Ofertas, jornadas y jornadas por oferta mantienen tres rutas propuestas; IAM/RBAC empresarial, fase 1 íntegra y aislamiento completo de datos de prueba conservan pendientes. No ampliar GRANT, catálogos o endpoints personales automáticamente.
