# P9 — cierre aceptado de consulta Meta y borradores locales

Corte vigente: 18 de noviembre de 2026. **P9 100%, 4/4 criterios; general 97,59%, 273/279 hitos y 53/56 criterios.** Los apartados inferiores conservan las etapas previas, sus fallos y condiciones pendientes de entonces; prevalece este cierre. Evidencia detallada: [aceptación](../../artifacts/live/p9-meta-acceptance-20261118.json) y [cálculo sin cambiar definiciones](../../artifacts/live/p9-progress-validation-20261118.json).

## Resultado comprobado

Cbneistas Bienestar (52067617), elegida por el propietario, está conectada con ads_read y sin ads_management. La consulta completa conserva 375 campañas, 420 conjuntos y 526 anuncios. El período cerrado 1–17 de noviembre tiene 17 puntos diarios. Gasto, impresiones, alcance, clics y leads coinciden con una consulta independiente a Meta del mismo período; el gasto diario suma el total. Se conserva un hash del informe, sin publicar importes ni datos financieros privados en el repositorio. El inventario es actual y las métricas corresponden al período; ambos se identifican en pantalla.

El gráfico cambia de métrica con animación y mantiene los KPIs. La interfaz respeta movimiento reducido. El detalle abre un modal accesible con retorno del foco; se verificó una creatividad real cargada desde Meta. La imagen disponible es una miniatura de 64 píxeles, no una promesa de resolución alta ni de reproducción exacta de cada ubicación.

Se crearon dos propuestas ficticias locales marcadas NO PUBLICAR: una campaña nueva con revisiones 1 y 2 y una edición de una campaña real. Guardar, recargar y revisar funcionan; una nueva versión o consulta invalida revisiones antiguas. La propuesta de edición conserva el identificador y presupuesto disponible. La campaña real mantiene nombre, estado, objetivo y presupuestos sin cambios. No existe publicación de anuncios en esta entrega; revisión local no significa aprobación de Meta.

La importación manual repetida del mismo lead ficticio produjo exactamente un lead, un contacto y una conversación en Humano, con cero mensajes y sin consentimiento comercial. Es una prueba de captación manual e idempotencia; no se presenta como un envío real de formulario Lead Ads. Pausar la cuenta local deshabilitó la sincronización manteniendo informes/borradores/IDs; se restauró a Disponible/conectada. El período inválido mayor de 93 días produjo un modal con causa y solución antes de llamar a Meta; volver al período válido recuperó la consulta guardada.

## Validación y límites

Pasan 129 pruebas backend y 24 frontend seleccionadas, tipos, lint de archivos modificados y build de `vite.workspace.config.ts`. El build mantiene la advertencia de bundle grande; las suites se solapan con comprobaciones previas y no se suman como pruebas únicas. Coolify confirmó backend d40d3f1 saludable y frontend cf09994 Success. Las pruebas de navegador y el contraste autenticado son evidencia separada de los tests locales.

La consulta está acotada a 1000 objetos por nivel, páginas de 250, 93 días y límites de tiempo/tamaño sobre host Graph fijo. Un exceso falla completo sin persistir cifras parciales. Se conservaron el fallo inicial por 526 anuncios y el modal oculto en details; ambos fueron corregidos y repetidos satisfactoriamente. No se realizó reversión de imagen esta vez: la prueba live de reversión es la pausa/reactivación local conservando estado, junto con regresiones controladas.

La evidencia corresponde a PostgreSQL en producción. No revalida SQL2019, SIIE ni aceptación institucional y no reconstruye veinte artefactos históricos ausentes. No se afirma prueba móvil real ni auditoría formal de accesibilidad. Textos, pesos, denominadores, releases, checkers y grafos congelados permanecen intactos. Se acepta exclusivamente P9.close/P9.close.m4; P10 mantiene 95% pendiente de revisión propia y P11 72,50%.

## Etapas históricas conservadas

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

## Continuación con cuenta elegida

El propietario eligió Cbneistas Bienestar (52067617). La conexión quedó guardada. Primera consulta detenida sin guardar datos parciales: inventario real de 375 campañas, 420 conjuntos y 526 anuncios; superaba el tope inicial de 500 por nivel. Se amplía a 1000 objetos por nivel en páginas de 250, manteniendo el límite de tiempo, tamaño y host Graph fijo. La tabla muestra 50 filas por página y busca en todo el inventario cargado. Un aviso de conexión situado dentro de details plegado bloqueaba la pantalla: se traslada fuera y se prueba su visibilidad. Publicidad incorpora también el proveedor común de modales de error. Se conserva el fallo como evidencia; la aceptación requiere repetir la consulta desplegada. Pruebas seleccionadas actuales: 129 backend y 22 frontend, tipos/build workspace correctos.
