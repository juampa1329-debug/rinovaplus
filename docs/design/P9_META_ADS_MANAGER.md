# P9 · Administrador de publicidad Meta

Ampliación solicitada el 18/11/2026: datos reales de Meta y preparación de creación/edición en borradores revisables. El inventario histórico de Scentra sólo cubría registros locales y captación. El cierre P9 sigue pendiente hasta comprobar esta ampliación; no se cambia la definición ni el peso del roadmap.

## Producto y diseño

Mantener Manrope/Source Sans 3 y los tokens RinovaPlus (petróleo #12343B, lima #C4F04D, superficie clara #F5F7F2). Una vista de rendimiento ocupa el ancho disponible: cuenta/período/conexión arriba; seis indicadores; tendencia diaria; tablas Campañas → Conjuntos → Anuncios y vista previa; borradores en su propia pestaña. Captación y CRM conservan el módulo P9 anterior.

Skills aplicadas: ui-ux-pro-max (líneas para tendencias temporales; se descartaron gauges porque no hay metas definidas), kpi-dashboard-design (fuente, período y fórmula explícitos; no promediar ratios), interaction-design (transiciones 180–320 ms, trazado inicial de gráfico sin bucle, reduced-motion, foco y tabla accesible). Sin cifras ni tendencias de demostración en el panel real.

## Integración

- Marketing API exclusivamente GET para descubrir cuentas autorizadas, campañas, conjuntos, anuncios/creativos e Insights de período y por día. Host fijo graph.facebook.com, Bearer en cabecera, cursores acotados; nunca seguir URLs next arbitrarias.
- OAuth de sólo lectura ads_read reutiliza la app y callback seguros de Canales. La autorización de publicidad no selecciona ni pausa una Página/número ni cambia sus webhooks. Solicitar ampliación de permisos en Meta con confirmación explícita cuando corresponda.
- Conservar credenciales AES-GCM existentes. Revalidar autoridad, cuenta, app y versión de credencial después del IO antes de guardar. Error conserva la última captura válida, nunca sustituye métricas por ceros.
- Capturas append-only y borradores versionados en el diario Event de P9 existente, con fuente, moneda, zona horaria y período. Sin DDL ni modificación de releases/checkers históricos.
- Borradores locales de campaña, conjunto y anuncio, nuevos o derivados de un objeto consultado. No se publica ni se activa gasto. La revisión vincula versión de borrador y captura de origen; editar invalida la revisión.

## Métricas

Gasto/impresiones/alcance/clics/resultados se obtienen de Insights. CTR = clics totales / impresiones; CPC = gasto / clics; CPL = gasto / leads. Denominador cero produce «Sin dato», no una eficacia inventada. Alcance del período viene del agregado de Meta: no sumar alcance diario ni de anuncios. Para leads se prioriza el agregado lead frente a sus aliases para evitar duplicar acciones. No sumar monedas diferentes. Atribución de Meta separada de captaciones/conversiones observadas en CRM.

## Validación y límites

Pruebas puras: paginación/errores/fechas, secretos y cambios de autoridad, ratios y ceros, aislamiento de cuentas, borradores sin POST publicitario, respuestas UI tardías, teclado, reduced-motion. Pruebas de producción: conectar una cuenta autorizada, sincronizar y contrastar objetos/fecha/fuente, guardar/releer un borrador; comprobar captación/deduplicación/reversión local. Sin publicar anuncios ni presupuestos.

Fuentes primarias: [Ads Insights](https://developers.facebook.com/docs/marketing-api/insights/), [Ad Account](https://developers.facebook.com/docs/marketing-api/reference/ad-account/), [Ad](https://developers.facebook.com/docs/marketing-api/reference/adgroup/), [Campaign](https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/). Se usa la versión configurada de la app, no una versión inferida del navegador.
