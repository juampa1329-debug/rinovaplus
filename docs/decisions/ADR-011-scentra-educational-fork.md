# ADR-011 Copia educativa de Scentra sobre CRM CBN

Fecha: 2026-10-24, America/Bogota.

## Estado

Aceptada la dirección de producto por instrucciones explícitas del propietario en esta conversación. P0 autoriza roadmap, grafos y continuidad. El orden detallado y la implementación de P1–P11 se revisan por etapas; no hay aceptación implícita de despliegue, migraciones productivas o activación de proveedores.

## Decisión

CRM CBN será una copia educativa independiente de las capacidades seleccionadas de Scentra. Conserva su estilo visual, Admisiones/SIIE, las identidades actuales y la jerarquía orientador → programa → etapa. Scentra es referencia funcional y continúa como producto independiente.

La aplicación funcionará en Linux con Docker. La institución usa SQL Server **2019**, con una base existente; se crearán únicamente las estructuras CRM faltantes mediante migraciones explícitas. No se presume la edición, compatibilidad o sistema operativo del servidor SQL. SIIE conserva autoridad académica.

Incluye Inbox/comentarios/mini CRM, CRM, mensajería masiva, campañas, remarketing, Meta Ads, agentes, conocimiento, memoria colectiva, ADN y aprendizaje, además de ajustes de módulos/modelos/canales/webhooks/usuarios. Excluye planes, suscripciones y cobro del software. Se conservan presupuestos técnicos, permisos, consentimiento y controles de ejecución.

## Consecuencias

- Se compara comportamiento, datos, procesamiento y UI; una pantalla, stub o archivo copiado no demuestra equivalencia.
- Se reutilizan módulos SQL Server y datos existentes antes de diseñar tablas nuevas. No se modifican migraciones aplicadas sin decisión explícita.
- Las dependencias de billing de Scentra se sustituyen por políticas institucionales donde corresponda; no se eliminan controles operativos.
- No se copiarán datos privados, credenciales ni memorias de otros clientes. La memoria compartida será institucional y con separación de aspirantes/programas.
- El estilo Glass actual prevalece. No se autorizó una sustitución general de colores, tipografías o sistema de componentes.
- La dirección supersede propuestas históricas que limiten el producto al prototipo, que no incluyan Ads o que sitúen el trabajo en el SaaS original. Los controles de integridad, TLS y protección del core siguen vigentes.
- Los grafos y la memoria serán artefactos locales reproducibles. Se inspecciona código sin llamadas LLM externas de Graphify; no se instala tooling ni se publican repositorios en P0.

## Seguimiento

Actualización del propietario, 2026-10-24: P1.1 autorizada para inventario estático, compatibilidad SQL Server2019, grafos y memoria, sin cambios en base. WooCommerce queda excluido expresamente del destino y se retira de la referencia candidata; las notas históricas de exclusión se conservan. No cambia el Scentra original ni se autoriza aplicación de DDL por este inventario.

[Roadmap](../SCENTRA_ADAPTATION_ROADMAP.md), [matriz](../adaptation/PARITY_MATRIX.md), [estado](../../tasks/TASK_STATE.md) y [alcance estructurado](../adaptation/scope.json). P0 sólo demuestra planificación e inspección estática. Las pruebas históricas del repositorio no se presentan como ejecutadas de nuevo.
