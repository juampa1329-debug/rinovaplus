# Cuentas de proveedores · Saldo y consumo

Por solicitud del titular, Ajustes → APIs y modelos → Proveedor de API ofrece «Saldo y consumo» para OpenRouter y ElevenLabs. El modal consulta al abrir y permite actualizar manualmente. Conserva la fecha de la lectura anterior si una actualización falla; cierre por botón/Escape y devolución de foco, con estilos institucionales y movimiento reducido respetado.

## OpenRouter

`GET /api/v1/key` con la clave normal devuelve consumo y límites de esa clave, incluyendo períodos diario/semanal/mensual cuando están informados. Un límite nulo no es saldo ilimitado ni prueba de crédito en la cuenta. [Referencia oficial de la clave](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key).

El saldo global se calcula exclusivamente como `total_credits - total_usage` de `GET /api/v1/credits`. La referencia exige una Management API key, que tiene facultades administrativas en OpenRouter. Se habilita su entrada opcional en Credenciales → Clave de administración de OpenRouter, cifrada y separada por Kind=management_key. El usuario debe crearla/guardarla directamente; el agente no la genera ni extrae. La clave de modelos sigue en Kind=api_key y los motores de IA sólo leen esa clase. El adaptador de saldo sólo utiliza la administrativa para GET credits, sin crear/revocar claves ni cambiar presupuestos. [Créditos](https://openrouter.ai/docs/api/api-reference/credits/get-remaining-credits), [claves administrativas](https://openrouter.ai/docs/guides/overview/auth/management-api-keys).

Si no hay clave administrativa, se muestra consumo de la clave y una explicación del requisito, sin inventar saldo global. Un rechazo o indisponibilidad de esa consulta no borra el consumo leído correctamente. No se retornan etiquetas de claves, identificadores de usuario, organizaciones ni el cuerpo crudo del proveedor.

«Recargar en OpenRouter» abre su [página oficial de créditos](https://openrouter.ai/settings/credits). El antiguo endpoint de Coinbase está retirado y la documentación dirige al recorrido web. El CRM no cobra ni activa recargas automáticas. [Aviso oficial del endpoint retirado](https://openrouter.ai/docs/api/api-reference/credits/deprecated-coinbase-commerce-charge-endpoint).

## ElevenLabs

`GET /v1/user/subscription` con la clave existente informa unidades usadas/límite/disponibles, plan y fecha de renovación. Se muestran también cupos de voces y si el plan admite sobreconsumo, sin habilitarlo. Las unidades no se convierten a USD ni a minutos garantizados: el uso depende de modelo/servicio. [Referencia oficial](https://elevenlabs.io/docs/api-reference/user/subscription/get).

«Gestionar plan» abre ElevenLabs para que el titular revise y confirme cualquier cambio. Las suscripciones web se gestionan allí; las contratadas por App Store/Google Play se administran con la tienda correspondiente. [Ayuda oficial sobre la gestión del plan](https://elevenlabs.io/docs/help-center/product/mobile-apps/elevenlabs-for-ios-and-android/managing-your-elevenlabs-subscription-mobile-app-vs-website). No se implementa una compra, mejora de plan o aumento de gasto mediante API.

## Límite operativo y verificación

Endpoint CRM GET `/api/institution/provider-balance/{provider}`, sólo OpenRouter/ElevenLabs, requiere settings.providers.read antes del acceso a claves. Se revalidan credencial y permisos al terminar; cambio de clave invalida la respuesta. Sin consultas al cargar toda la aplicación, sin sondeo periódico, sin inferencias/TTS, sin escrituras de saldo ni datos de facturación almacenados. El middleware institucional marca la respuesta no-store. Las claves y facturas nunca se retornan.

74 pruebas backend y17frontend seleccionadas pasan, tipos/lint y build del workspace de producción pasan (aviso histórico de bundle). Incluyen GET exclusivo, aislamiento de claves, desconocido frente a cero, valores inválidos, rechazo parcial, denegación antes de IO, rotación y cierre/foco/refresco del modal. Publicado a0b8310: backend tkpeigkbj4bwaw3nobnq3fqm Finished4m16s y Running; frontend gqgybvju6dhrxguczshcqi1w Success43s. La consulta real de OpenRouter mostró uso y límite de clave; el refresco mostró una fecha nueva. ElevenLabs devolvió plan, unidades usadas/disponibles, renovación y cupos de voces. Escape cerró el modal y devolvió el foco al botón. El titular difirió la clave administrativa hasta recuperar acceso en la oficina: el campo está listo, pero el saldo global no fue consultado ni verificado. No se generaron audios/mensajes ni se compraron créditos. Evidencia pública sin importes de cuenta: artifacts/live/provider-balances-20261122.json.
