# P9 — administrador de publicidad Meta

Corte: 18 de noviembre de 2026. Alcance ampliado por el propietario: consultar datos reales y preparar creación/edición en borradores locales con revisión antes de publicar. La referencia histórica de Scentra sólo acreditaba registros locales de captación; esta ampliación añade Marketing API y no reinterpreta aquel recibo como prueba externa.

## Implementado y publicado

- Conexión OAuth ligada a app, usuario y sesión; exige `ads_read`. Descubre las cuentas publicitarias autorizadas. El retorno de este flujo va a Publicidad y no selecciona de nuevo una Página ni pausa el canal.
- Consulta explícita de cuenta, campañas, conjuntos, anuncios/creatividades e Insights por período. GET a Graph fijo, sin seguir URLs arbitrarias de paginación ni publicar anuncios. Límite de 500 objetos por nivel y 93 días por consulta; un exceso falla completo en vez de guardar un informe truncado.
- Seis KPIs, gráfico diario animado y tabla accesible; filtros de nombre/estado, detalles y creatividad disponible. Moneda, zona horaria, período y fecha de consulta visibles. Sin datos, no se inventan cifras o curvas. Movimiento reducido respeta la preferencia del sistema.
- Versiones de borradores y revisiones en el diario P9 existente, sin DDL nuevo. Control de revisión exacta y de cuenta; nueva versión o consulta invalida la revisión anterior. Los cambios sin guardar requieren decisión antes de sincronizar.
- Captación y CRM conserva sus vistas existentes. Los registros locales siguen identificados como declarados; no se confunden con Insights de Meta.

## Comprobaciones realizadas

Commit de implementación `00ac7af`: frontend por webhook, backend con redeploy manual. Coolify terminó ambos; backend nuevo `nwbyrdvtsfclmm6zyffjqjqp-20261118T163013`, readiness correcto y relevo completado a las 16:34:31 UTC. La pantalla nueva abrió con la sesión existente.

Meta app RinovaPlus `1688152039579779`: caso de uso Marketing API guardado; configuración de Páginas `1672600597931078` conserva sus seis permisos y añade `ads_read`. OAuth completado desde RinovaPlus, modalidad de usuario, Página institucional CBN seleccionada. Consulta posterior `/me/permissions`: HTTP 200, `ads_read=true`, `ads_management=false`, `pages_messaging=true`. Canal Facebook · CBN conectado/verificado. La revisión automática rechazó la selección amplia de Páginas actuales/futuras; se corrigió seleccionando únicamente CORPORACION BOLIVARIANA DEL NORTE y la autorización limitada sí terminó.

La consulta real de cuentas devolvió Cbneistas Bienestar (`52067617`) y Cbneistas Carlos Quintero (`393527636692914`). Está pendiente la elección del propietario antes de incorporar una y consultar sus campañas. Esto acredita OAuth/descubrimiento, todavía no KPIs ni creatividad reales.

Pruebas locales: 128 backend en la selección de suites de autenticación/workspace/HTTP/Publicidad y 19 frontend de Publicidad; tipos, lint de archivos modificados y build pasan. Son suites solapadas con verificaciones anteriores, no una suma de tests únicos. El build conserva la advertencia previa de bundle grande. No se repitió el replay histórico SQL2019: siguen ausentes veinte artefactos históricos; no se fabricaron.

## Para terminar la aceptación

1. Elegir la cuenta institucional entre las autorizadas y conectarla desde Publicidad.
2. Consultar un período real; contrastar moneda, campañas, conjuntos, anuncios, métricas y creatividad con Meta. Un período vacío debe identificarse como vacío confirmado.
3. Guardar, recargar, editar y revisar un borrador real de propuesta local; comprobar invalidación al editar y conservación al cancelar navegación/sincronización. No publicar ni activar gasto.
4. Confirmar aislamiento por cuenta, historial y captación/CRM con las pruebas pertinentes; registrar alcance y límites antes de aceptar `P9.close.m4`.

P4 ya está aceptada en Meta. P9 conserva 93,75% técnico y 3/4 criterios mientras falta esta aceptación del alcance ampliado. General 97,14%, 272/279 hitos, 52/56 criterios. No cambian textos, pesos ni denominadores; P10/P11 no se cierran por esta entrega.

## Uso y reversión

Publicidad → Campañas y anuncios → Conexión y cuentas publicitarias. Usa Facebook · CBN, Conectar con Meta, completa la autorización y pulsa Completar conexión de publicidad. Elige Usar esta cuenta, selecciona fechas y pulsa Sincronizar con Meta. Borradores locales permite crear campañas/conjuntos/anuncios propuestos; Preparar edición copia un objeto real a una propuesta local. La revisión es local, no aprobación de Meta.

Para detener consultas, pausa la cuenta desde Captación y CRM → Cuentas publicitarias. Conserva cuenta, IDs, consultas, borradores e historial. Revertir la imagen de aplicación conserva los eventos nuevos sin modificar anuncios reales. No borrar captaciones ni revocar credenciales compartidas para revertir la pantalla. La publicación y sus permisos son un trabajo posterior, con autorización explícita antes de cualquier gasto.
