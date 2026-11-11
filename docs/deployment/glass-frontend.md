# Glass: desarrollo en caliente en el mismo proyecto

## Flujo vigente — 2026-10-19

Por instrucción del propietario, el servicio existente `crm-cbn-integration-20261014-preview-1` se ejecuta ahora desde las fuentes actuales de `E:\Nuevos_Proyectos\CRM_CBN`, en la misma URL `http://127.0.0.1:4173`. No se creó otro checkout, instancia de aplicación ni base. La imagen de desarrollo incorpora únicamente el runtime Node y las dependencias fijadas; las fuentes frontend/backend se montan directamente en lectura desde el proyecto actual. El volumen adicional `frontend-dependencies` contiene dependencias Linux, no datos de negocio ni copias del proyecto.

El problema anterior era verificable en la receta estática: la imagen Glass copiaba `frontend/dist` y heredaba el backend C5, sin montar fuentes ni activar recarga. Por eso modificar el árbol de trabajo no cambiaba la aplicación abierta.

- `frontend/` se monta en `/app/frontend-source`; Vite sirve los componentes y estilos actuales mediante HMR, con polling para Docker Desktop/Windows y caché temporal. No carga archivos `.env` privados al frontend.
- `backend/app/` se monta en `/app/backend/app`; Uvicorn StatReload observa los archivos Python y conserva un único proceso de aplicación. Sus workers normales se detienen/reinician con el ciclo de vida existente.
- Nginx conserva loopback 4173 para la interfaz y API local, sus restricciones de Host y el proxy. La ampliación autorizada del 2026-10-20 incorpora loopback 4174 exclusivamente para el callback Meta mediante Tunnelmole, con ruta exacta y métodos limitados; no expone administración ni UI. [Guía del ingreso Meta](meta-webhook-tunnelmole.md). Vite 5173/backend 8002 quedan internos al mismo contenedor; el WebSocket HMR usa el mismo origen del navegador.
- Se conserva `local_sql_copy`, la base externa local `DBSIIE`, el certificado público/TLS y el mismo volumen `ai-state`. Las variables preexistentes mantuvieron su huella agregada tras la recreación. No hubo DDL, migraciones, escritura API de negocio ni cambios de credenciales/permisos IA.

```powershell
Set-Location 'E:\Nuevos_Proyectos\CRM_CBN'
docker compose -p crm-cbn-integration-20261014 -f compose.yaml -f compose.local-sql.yaml up -d --no-build preview
```

La construcción inicial de `docker/Dockerfile.development` y la recreación del mismo servicio ya se realizaron para ponerlo en marcha. Guardar cambios frontend/Python no requiere reconstruir imagen. Cambiar dependencias o scripts de arranque requiere actualizar la imagen/instalación correspondiente; cambiar variables de proceso requiere recrear el mismo servicio. Los cambios SQL se aplican deliberadamente sobre el destino autorizado, nunca automáticamente por HMR. No utilizar `down -v` ni eliminar el volumen IA.

La pestaña que todavía ejecuta el paquete estático requiere una recarga inicial después de guardar borradores; las siguientes ediciones de componentes/estilos usan HMR. Una recarga completa o una edición incompatible con React Fast Refresh puede perder borradores de la pestaña; los datos confirmados siguen en SQL. El breve reinicio backend puede interrumpir peticiones en vuelo.

Observaciones directas de runtime: contenedor saludable, `/health/live` 200; index contiene el cliente Vite; procesos Vite y StatReload activos; OpenAPI actual incluye la verificación Meta y su estado. `GET /api/v1/webhooks/meta/status` devuelve solo disponibilidad/configuración, sin secreto/digest, y muestra actualmente verificación implementada, token sin configurar, recepción/despacho pendientes y canales sin conectar. Ajustes > Canales consulta ese endpoint y presenta el callback como dirección local, sin afirmar que Meta pueda alcanzarlo. El endpoint GET de challenge conserva rechazo seguro cuando falta el hash configurado.

Observación manual del navegador en la misma URL: Ajustes > Canales recibió el nuevo bloque mediante HMR sin otra recarga de página. Mostró verificación implementada, token sin configurar, callback local, recepción/despacho pendientes y canales sin conectar. La acción ordinaria Actualizar estado conservó ese estado real; no se envió un token de prueba ni se simuló un evento.

Por solicitud expresa no se ejecutaron pruebas automatizadas, lint, typecheck ni builds de comprobación. La construcción Docker fue necesaria para servir el runtime. La exportación de metadatos actualiza el catálogo/OpenAPI desde las fuentes; no conecta SQL/proveedores ni inicia workers. Sprint 2 completo y Sprint 3 permanecen pendientes.

## Historial — imagen estática anterior

El diseño aprobado está incorporado a `crm-cbn-preview:glass-20261019`. El 2026-10-19 se recreó realmente el servicio `preview` y se conservaron backend, configuración, montajes y datos comprobados. La receta de [Compose](../../compose.yaml) usa [Dockerfile.frontend](../../docker/Dockerfile.frontend), que copia únicamente el index y los assets compilados sobre la imagen del runtime anterior. No reconstruye el backend del árbol de trabajo.

Los comandos de esta sección describen el corte histórico; `compose.yaml` selecciona ahora el flujo de desarrollo anterior, no esta imagen estática.

## Identidad y preservación comprobadas

| Elemento | Identidad |
|---|---|
| Base local | `crm-cbn-runtime-base:c5-fa3bb5bc73b9` |
| ID exacto de la base | `sha256:fa3bb5bc73b915f1f5ff36e98ae9f9da8978f95eb9e243a2ac9897349db2fb10` |
| Imagen Glass | `crm-cbn-preview:glass-20261019` |
| ID construido | `sha256:bf5afcf92bd61ba73ef85b08d9a51e6c97b0ff09c0c14c920ac43ff9d6a907f1` |
| Proyecto Compose | `crm-cbn-integration-20261014` |
| Preview privado | `http://127.0.0.1:4173` |

Los 48 archivos de backend/configuración del runtime coincidían con la imagen base y permanecen idénticos en la imagen nueva. La configuración de imagen se heredó sin cambios; entorno, configuración de ejecución, montajes y red también coinciden después de recrear. La respuesta completa de `/api/local/crm` conserva su SHA-256, revisión 22, dos clientes y dos conversaciones. Los dos archivos del volumen IA conservan su huella agregada. SQL permanece externo; esta unidad no ejecutó escrituras API, DDL ni migraciones.

`/health/live` devuelve 200 y el contenedor está saludable. `/health/ready` conserva el 503 explícito del contrato anterior: no acredita que todas las integraciones estén listas. Los hashes HTTP de index, CSS y JS coinciden con el build previamente comprobado. No se volvió a compilar frontend ni a ejecutar sus 208 pruebas porque sus bytes permanecen intactos.

Evidencia saneada local: `.local/glass-image-20261019/`, especialmente `build-result.json`, `preservation-before.json`, `preservation-after.json` y `http-final.json`. No contiene cuerpos de contactos ni valores de credenciales. El detalle anterior del overlay se conserva en `.local/glass-real-runtime-20261019/`.

## Recrear conservando esta imagen

El navegador comprobó la instancia recreada: dos registros en Clientes, sin alertas, desbordamiento ni errores de consola y con los assets finales. Evidencia: `browser-proof.json` y `permanent-glass.jpg` en la carpeta local anterior. La pestaña de prueba se cerró y se conservó la pestaña del usuario.

Ejecutar desde la raíz del proyecto, con el mismo `.env` privado y certificado público existentes. Mantener exactamente el nombre del proyecto evita crear otro volumen IA. No sustituir variables por valores de otra instalación.

```powershell
docker compose -p crm-cbn-integration-20261014 -f compose.yaml -f compose.local-sql.yaml up -d --no-build --force-recreate --wait --wait-timeout 90 preview
```

Compose selecciona la imagen Glass y `pull_policy: never`. Un reinicio o una recreación con esta receta conserva el diseño; ya no depende del overlay del contenedor anterior. Conservar ambas imágenes locales y el tag base. No se publicaron imágenes en un registro ni se preparó recuperación en otro equipo.

## Reconstruir solamente el paquete estático

`frontend/dist` es el artefacto compilado previamente comprobado, no código fuente ni datos de prueba. Para este corte debe contener `index-C2aDtdYy.css` e `index-DUJ_8gIJ.js`, con hashes registrados en `frontend-release.json`. No reemplazarlo por una copia del harness de navegador. La exclusión específica del Dockerfile impide enviar backend, `.env` o estado del operador al contexto de construcción.

Antes de construir, comprobar que el tag base resuelva al ID exacto anterior. Si falta el tag pero el ID sigue disponible, recuperarlo desde ese ID; no usar una imagen homónima descargada ni un build del backend actual.

```powershell
$expectedBase = 'sha256:fa3bb5bc73b915f1f5ff36e98ae9f9da8978f95eb9e243a2ac9897349db2fb10'
$actualBase = docker image inspect crm-cbn-runtime-base:c5-fa3bb5bc73b9 --format '{{.Id}}'
if ($LASTEXITCODE -ne 0 -or $actualBase.Trim() -ne $expectedBase) { throw 'La imagen base no coincide; no construir.' }
docker build --pull=false -f docker/Dockerfile.frontend -t crm-cbn-preview:glass-20261019 .
if ($LASTEXITCODE -ne 0) { throw 'La construcción no finalizó correctamente.' }
```

La construcción por sí sola no cambia el contenedor activo. Después de comprobar los hashes del paquete, la receta de recreación anterior aplica la imagen.

## Reversión del paquete

La reversión selecciona la base exacta, conservando el mismo proyecto, entorno y montajes; recupera la interfaz anterior. No requiere borrar contenedores con `down`, volúmenes ni datos SQL.

Crear `.local/glass-image-20261019/compose.rollback.yaml` con este contenido:

```yaml
services:
  preview:
    image: crm-cbn-runtime-base:c5-fa3bb5bc73b9
    pull_policy: never
```

```powershell
docker compose -p crm-cbn-integration-20261014 -f compose.yaml -f compose.local-sql.yaml -f .local/glass-image-20261019/compose.rollback.yaml up -d --no-build --force-recreate --wait --wait-timeout 90 preview
```

La reversión está preparada, no ejecutada. Para volver a Glass, utilizar la receta normal sin el archivo de reversión. En ambos casos comprobar salud, assets y los agregados de datos preservados; no modificar configuración de proveedores para conseguir readiness.

