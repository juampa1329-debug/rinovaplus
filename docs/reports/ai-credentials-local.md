# Credenciales IA desde Ajustes > APIs

**2026-10-14.** Implementación autorizada expresamente en el worktree `117d/CRM_CBN`, rama `codex/proveedores-ia`. No se modificó ni contactó el chat de diseños. Extiende el [banco local IA](ai-settings-local.md), sin SQL, canales, autenticación de producción o dependencias nuevas.

## Operación

1. Abrir Ajustes > APIs en `http://127.0.0.1:5175/#/settings` (backend 8002).
2. Pegar la clave emitida por Gemini, xAI/Grok u OpenRouter en su campo de contraseña y guardar. La pantalla informa presencia y origen, nunca el secreto guardado.
3. Autorizar **Permitir consultas y pruebas externas**; se guarda inmediatamente. No inicia ninguna consulta por sí solo.
4. Pulsar **Cargar modelos** para el proveedor, seleccionar y guardar modelo. En IA, habilitar pruebas, guardar y probar con texto ficticio.

Cambiar una clave o el permiso invalida catálogos y resultados/historial sintético, conservando los borradores de ajustes. Recargar catálogos antes de probar. Las claves locales prevalecen sobre las variables de entorno y el permiso local sobre `CRM_AI_OUTBOUND_ENABLED`; sin preferencia local se conserva la compatibilidad anterior. Las variables solo se releen al arrancar el proceso. Guardar una clave no acredita que sea válida. Errores de autorización del proveedor se muestran saneados; no disparan fallback.

## Protección y límites

`backend/app/modules/ai/infrastructure/credentials.py` usa DPAPI de Windows, ámbito usuario actual y sin diálogos; no usa `CRYPTPROTECT_LOCAL_MACHINE`. Windows administra la clave de cifrado. El archivo `.local/ai-credentials.dpapi` contiene solo ciphertext y está excluido por `.local/` de Git; la configuración de estilos/modelos sigue separada. Escritura temporal cifrada con fsync y reemplazo atómico, revisión optimista independiente, tamaño acotado y validación estricta sin eco. El servidor no reemplaza un almacén corrupto; no hay fallback a plaintext. El catálogo y gateway se actualizan inmediatamente, con mutaciones rechazadas mientras hay una operación externa en curso.

`PUT /api/ai/credentials/{provider}` acepta revisión y secreto; `PUT /api/ai/outbound` acepta revisión y permiso. Ambos heredan cliente loopback, Host/Origin, cabecera local y JSON/body acotado; devuelven solo metadatos con `Cache-Control: no-store`. La clave viaja transitoriamente del campo password al backend local y al proveedor autorizado cuando se consulta; no persiste en almacenamiento del navegador ni se devuelve. El campo se limpia incluso ante un error al guardar y al salir de APIs. No se registra el body ni la clave.

DPAPI protege en reposo para la cuenta de Windows; no protege frente a código ejecutado por esa misma cuenta o un administrador. El archivo no es un backup portable. No existe rotación automática, borrado/revocación de claves remotas ni RBAC; reemplazar la clave local se hace guardando otra, y la revocación corresponde al proveedor. Un solo proceso backend, loopback y uso personal. Otros sistemas conservan las variables de entorno existentes, con guardado desde UI no disponible y sin fallback inseguro. P-005/006/017/026 mantienen controles conectados pendientes.

## Evidencia de implementación inicial

- Backend: 70 pruebas completas aprobadas, incluidas 18 nuevas de credenciales; Ruff aprobado. DPAPI real en Windows con secreto sintético, lectura desde una nueva instancia y alteración del ciphertext; contratos HTTP de los tres proveedores simulados, sin red externa. También validación, origen rechazado, conflicto, concurrencia, escritura fallida preservando anterior, corrupción sin sobrescritura y permiso persistente que prevalece sobre entorno.
- Frontend: **71 pruebas completas aprobadas** con `npm test -- --maxWorkers=1`, formato/lint/tipos/build aprobados; siete casos IA incluidos. La prueba específica verifica guardado password/limpieza, errores saneados, borrador conservado, permiso explícito, catálogo y modelo guardado, sin escrituras de Storage. Detector Impeccable `[]`. La primera suite concurrente agotó 5000 ms en una prueba histórica de fase 2 y arrastró un fallo posterior: esa fase pasó 5/5 aislada y la suite completa pasó 71/71 con un worker, sin cambiar pruebas ni aumentar sus timeouts.
- Navegador del coordinador sobre backend reiniciado en 8002 y frontend 5175: APIs muestra tres campos password; Gemini comprobado como `type=password`, guardar vacío y cargar sin autorización deshabilitados, permiso externo desmarcado. Escritorio y móvil 390 × 844 legibles, sin overflow horizontal (client/scroll 375) ni errores de consola. Vista final APIs abierta. No se ingresó ni guardó clave ni se activó salida externa; ajustes vivos preservados.
- Primera ejecución pytest en sandbox no pudo crear temporales; otra ruta temporal no tenía padre. Se corrigió al directorio `.local` del worktree y se ejecutó con permisos aprobados. Una prueba de alteración inicialmente cambió metadatos DPAPI que Windows tolera; se corrigió para alterar la firma del ciphertext y acreditar rechazo. No se relajó validación del producto.
- En este corte inicial no se suministraron claves reales ni se probó una respuesta real de Gemini; la app quedó sin claves y con permiso externo desactivado. La aceptación posterior se registra a continuación.

## Aceptación real de Gemini — 2026-10-14

El propietario ingresó y guardó su propia clave desde APIs y autorizó expresamente catálogo, selección de modelo y prueba real. El coordinador confirmó después de **Recargar** el metadato de credencial local, sin registrar el secreto. Se habilitó explícitamente salida externa y Gemini devolvió **46 modelos**.

La primera prueba con `gemini-2.5-flash-lite` falló con `404 NOT_FOUND`. Una repetición diagnóstica acotada confirmó que el proveedor no lo ofrecía a usuarios nuevos y recomendaba la familia 3.5. Esto acredita que figurar en catálogo no garantiza disponibilidad de inferencia para esa credencial; no se activó fallback para ocultar el rechazo.

El coordinador seleccionó y guardó `gemini-3.5-flash-lite`: revisión de ajustes **5**, IA habilitada y fallback deshabilitado; límites de solicitud/salida **700 tokens** y temperatura **0.5** conservados. La prueba real desde la UI, con texto sintético, terminó con **un intento exitoso y cero mensajes históricos**. Respuesta recibida:

> Hola Prueba, soy el asistente virtual de CRM CBN, y el resultado de calcular 17 + 25 es 42.

La aceptación local de guardar credencial, consultar catálogo, seleccionar modelo y obtener una respuesta real queda comprobada. Se usaron exclusivamente frontend **5175** y backend **8002** de este worktree; chat de diseños intacto, sin contactos ni SQL. La clave guardada por el propietario permanece local y cifrada; salida externa e IA quedan habilitadas para las pruebas solicitadas. No se acredita producción, RBAC, canales ni calidad general del modelo.

Esta actualización es documental sobre la evidencia del coordinador: lectura estructural de Markdown, sin nuevas llamadas, acceso a secretos, cambios de código/configuración, reinicios ni repetición de tests/build.

Referencias: [CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [CryptUnprotectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata). La librería estándar ctypes evita incorporar una dependencia criptográfica propia.
