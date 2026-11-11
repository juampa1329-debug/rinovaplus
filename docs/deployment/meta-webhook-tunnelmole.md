# Callback público de Meta mediante Tunnelmole

El proveedor activo elegido por el propietario es **Tunnelmole (`tmole`)**, sustituyendo ngrok. Se conserva el ingreso del mismo `preview` en `http://127.0.0.1:4174`: únicamente GET/POST en la ruta exacta `/api/v1/webhooks/meta`; otras rutas devuelven 404 y otros métodos 405. No dirigir el túnel al puerto 4173 de interfaz/administración.

## Arranque desde la instalación existente

Se leyó el cliente global Tunnelmole 2.4.0 instalado en el equipo. Su CLI imprime incondicionalmente método y URL completa de cada petición; `TUNNELMOLE_QUIET_MODE` por sí solo no elimina ese registro. Para impedir que la query de verificación o el cuerpo del webhook terminen en consola/archivos, el launcher local ignorado silencia la salida original del cliente y publica exclusivamente la URL HTTPS realmente asignada, validada sin query, junto con errores constantes. También desactiva telemetría y verbose. No modifica ni copia la instalación global ni la aplicación CRM.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'E:\Nuevos_Proyectos\CRM_CBN\.local\tools\tunnelmole\start-meta-tunnel.mjs'
```

El launcher utiliza el CLI instalado `dist/bin/tunnelmole.js` con el puerto fijo 4174. Primero informa `state: starting`; solo el evento real `URL_ASSIGNED` permite informar `state: active`, `httpsUrl` y `callbackUrl`. No inventa dominios. Mantener la sesión de Node abierta hasta detenerla con Ctrl+C. En este entorno el arranque oculto no conservó el proceso; la sesión persistente sí recibió una URL HTTPS real y no mostró errores. Si se redirige salida, utilizar exclusivamente la salida saneada del launcher, nunca la del CLI original. El agente instalado conserva su almacenamiento normal de identidad del cliente; no se agregan registros de peticiones ni claves nuevas desde este procedimiento.

## Configuración Meta

En Meta for Developers se registra el `callbackUrl` HTTPS obtenido del agente activo, que termina en `/api/v1/webhooks/meta`, sin barra final. La misma ruta atiende el challenge GET y los eventos POST. Si cambia el dominio del túnel, hay que actualizarlo también en Ajustes > Canales.

El token de verificación se crea/configura en la aplicación y se coloca en el campo equivalente de Meta; no es el Access Token de WhatsApp. Nunca se documenta su valor ni se añade a comandos, logs o código. El backend devuelve el `hub.challenge` solo si coincide. Los POST conservan firma HMAC obligatoria y necesitan el App Secret de la aplicación configurado desde la UI. Un challenge aceptado no activa envíos ni acredita un Access Token vigente, suscripción o entrega real.

## Preservación y límites

Nginx mantiene un límite de 1.000.000 bytes y timeout de cinco segundos. Su configuración se monta en lectura desde el proyecto. HMR, frontend/API local en 4173, SQL, certificado y volúmenes se conservan en el mismo runtime; no hay otro backend ni otra base. Detener el proceso Tunnelmole retira el acceso público y conserva la aplicación local.

**Observación temporal del rechazo en el panel de Meta:** las consultas reales actuales, incluida una con el User-Agent utilizado por Facebook, devolvieron HTTP 200 y el challenge exacto; todavía no se conoce la causa del rechazo mostrado en el panel. Está activo en Nginx únicamente para el listener 4174 un access log a stdout con timestamp numérico, estado HTTP, estado del upstream y duración. El formato es `$msec status=$status upstream_status=$upstream_status duration=$request_time`: no incluye método, ruta, query, token, cuerpo, IP, headers ni User-Agent. El error log público continúa descartado y 4173 conserva su comportamiento anterior. La recarga de Nginx quedó confirmada y una consulta pública devolvió el challenge exacto con registro saneado `status=200 upstream_status=200 duration=0.205`. Solo falta observar el reintento real del usuario en Meta para correlacionar el resultado; no se presume un token incorrecto por cambios del portapapeles o de revisión. Al cerrar el diagnóstico, volver a desactivar el access log de 4174. No se modificaron firmas, routers, SQL ni credenciales para esta observación.

El operador observó el túnel activo en una sesión persistente y una URL HTTPS asignada realmente; el dominio efímero no se fija en este documento. Con autorización humana explícita se generó el verify token, se guardó cifrado AES-256-GCM en el mismo perfil WhatsApp (revisión 3) y se copió al portapapeles sin mostrar su valor en logs. La consulta GET pública real devolvió HTTP 200 y el challenge exacto; se comprobó también que el portapapeles coincide con el token guardado. Esto acredita la verificación técnica a través del túnel. El usuario todavía debe pulsar **Verificar y guardar** en Meta for Developers; App ID, App Secret y renovación del Access Token vencido siguen pendientes para recibir eventos y habilitar envíos. No se expone TikTok en este corte, no se envían mensajes ni se ejecutan tests/DDL/builds. La URL temporal de desarrollo no acredita disponibilidad productiva.

Historial: ngrok 3.39.11 se instaló y su primer arranque devolvió `ERR_NGROK_4018` por falta de cuenta/authtoken. El propietario eligió reemplazarlo por su instalación existente de Tunnelmole; el flujo ngrok ya no es el procedimiento activo.
