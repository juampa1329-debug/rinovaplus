# Canales · referencia de paridad Scentra → CBN

Precisión del propietario durante SQL-C9, 2026-10-25: la sección debe conservar la estructura y las funciones de Scentra. Cambia PostgreSQL por SQL Server; se mantiene el estilo visual CBN ya aprobado. Una pantalla de configuración reducida no acredita por sí sola esa igualdad funcional.

## Fuente y organización

Referencia primaria: `../saas-version/frontend/src/App.jsx`, sección Canales, líneas 9609–10468 y sus handlers de integraciones. La [captura funcional de Ajustes](../../design/settings-reference/scentra-settings-specification-2026-10-13.md) complementa el código; la fuente actual prevalece. No se modifica Scentra ni se copian credenciales/datos privados.

El orden de referencia es: Meta WhatsApp Cloud → Verificar número WhatsApp → Instagram Business → Facebook Messenger → TikTok → Webhooks. La interfaz C9 adopta estos grupos en acordeones verticales; conserva las cinco cuentas SQL heredadas y sitúa Comentarios de Facebook como subconfiguración de Facebook Messenger. La pantalla no presenta estados sintéticos como conexión externa demostrada.

## Contrato de paridad por función

| Grupo Scentra | Comportamiento que debe conservarse | Estado real en C9 y trabajo restante |
|---|---|---|
| Meta WhatsApp Cloud | Proveedor/canal, estado y modo de envío; Phone Number ID, WABA ID, Meta App ID, Graph API; App Secret/token permanente cifrados; guardar/refrescar y pista protegida | IDs/configuración con revisión y guardado SQL ensayados. Gestión de secretos, hints, estado operativo/método de envío y flujo completo pendientes |
| Verificar número WhatsApp | Sincronizar números WABA, elegir número, PIN6 y registrar/verificar con respuesta real | Grupo y acciones identificados como pendientes; no se solicita PIN ni se simula verificación. Portar contrato y pruebas de Meta/SQL |
| Instagram Business | OAuth con App ID/Graph API/App Secret; diagnóstico; descubrir/seleccionar cuenta; ruta manual, Page ID/Business ID/nombres/portfolio, token y endpoint | Configuración básica SQL e identificación del producto de acceso. OAuth, activos, secretos/hints, campos completos, diagnóstico y webhooks pendientes |
| Facebook Messenger | OAuth; diagnóstico/carga y selección de páginas; configuración manual, token cifrado y endpoint; mensajes y comentarios | Configuración básica de cuentas messenger/facebook heredadas. Unificar comportamiento de la sección sin perder su historial; OAuth/activos/secretos/campos completos pendientes |
| TikTok | OAuth/estado/modo; Client Key/Open ID/Business ID/Advertiser ID/scopes; revisión/productos/scopes aprobados/eventos; modo de envíos/rollout/cuotas; flags de Business Messaging/comentarios/IA/agentes/activadores/remarketing; rutas/API/secrets/notas; diagnóstico/descubrimiento/eventos/endpoint | Configuración básica SQL y acciones señaladas como pendientes. Portar el modelo completo, validación y permisos operativos antes de habilitar acciones |
| Webhooks | Selector de canal educativo, HMAC, crear/actualizar endpoint con Callback URL/verify token, refrescar listado y procesar eventos con contratos idempotentes | Grupo pendiente en C9; la API pública y los workers siguen bloqueados. No generar endpoints o tokens ficticios para completar la pantalla |

Las cuotas de TikTok son controles operativos y se conservan. Stripe/billing y conectores de comercio excluidos por el alcance educativo no se portan por aparecer en el selector de Scentra.

C8 ya tiene cifrado AES-GCM ensayado. La brecha es completar la gestión, rotación y pistas de secretos y los flujos de conexión; no la ausencia del cifrado. C9 no tiene permiso para leer Ciphertext/Nonce/KeyId ni monta la clave de proveedores. Los campos de credenciales no se habilitan hasta disponer del contrato SQL, perfil/ACL propios y pruebas; mostrar una acción deshabilitada no cuenta como implementarla.

Hay diferencias de modelo que deben resolverse antes de aceptar la igualdad: Scentra lista, edita y elimina varias integraciones WhatsApp; B011 Account usa Channel como clave y admite una cuenta por canal. No se acreditará paridad de cardinalidad con ese modelo. El DTO C9 sólo permite diez campos de configuración: no persiste los controles completos de TikTok. Sus Client Secret y Webhook Secret tampoco son equivalentes por nombre a los cuatro tipos genéricos de secretos CBN. SQL-C10 debe definir cardinalidad, claves, contratos de secretos y compatibilidad de datos antes de habilitar esos formularios. No crear inputs que parezcan guardar campos que el servidor descarta.

## Aceptación y continuidad

La aceptación local de C9 cubre capacidades, configuración y lectura, conflictos, caída/recuperación, copia aislada y preservación. El estado de paridad con Scentra es **parcial**. Ni C9 ni P4 se cierran como copia completa de Canales.

SQL-C10 debe detallar y versionar los DTO, datos/configuración, permisos y casos de aceptación de esta matriz, incluidos OAuth, secretos y activos; resolver B015/MessageRoute y el transporte en la secuencia que corresponda. No reducir la referencia a los campos que ya admite CBN ni ampliar tickets existentes para evitar drift.

Cada función se cierra sólo con el mismo flujo/validaciones/estados observables de Scentra, persistencia SQL Server probada en otra restauración, secretos protegidos, pruebas de error/reintento/concurrencia y aceptación en navegador. La operación real de proveedores y la aceptación institucional SQL2019 son puertas distintas. No se activan por registrar esta matriz.

Véanse [informe C9](SQL_C9_REVIEW.md), [roadmap](../../SCENTRA_ADAPTATION_ROADMAP.md), [progreso](../../../tasks/sql-c9-progress.json) y [fragmento de paridad](../fragments/sql-c9-scentra-parity.json).
