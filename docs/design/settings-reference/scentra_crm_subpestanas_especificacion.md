# CRM de creadores — especificación funcional

**Aplicación:** [Scentra +AI][1]  
**Revisión:** 13 de octubre de 2026

Este documento se refiere al módulo **CRM de creadores**, distinto de **Clientes CRM** (el módulo de clientes documentado antes). En esta sesión el navegador mostró la pantalla de inicio de sesión, por lo que no pude verificar datos ni estados dinámicos desde la aplicación. La estructura descrita corresponde a la plantilla pública del módulo y su definición en el front-end. [1] [2] [3]

## Estructura común

El módulo es una sola página con siete botones de subpestaña, que muestran una vista a la vez: **Creadores**, **Campañas**, **Recursos**, **Derechos**, **Rendimiento**, **Spark** y **Auditoría**. El encabezado incluye ayuda contextual y **Actualizar**; este último vuelve a cargar la información y se deshabilita mientras está cargando.

Debajo aparecen contadores de **Creadores**, **Campañas**, **Entregables** abiertos, **Recursos** y **Derechos OK**. Según los accesos disponibles, también pueden mostrarse botones de navegación **Contenido** y **Anuncios**; son accesos a otros módulos, no subpestañas del CRM. [2] [3]

## Creadores

La vista combina el formulario **Nuevo creador** con un panel **Pipeline**. El formulario registra el perfil y su relación comercial:

- **Nombre visible**, obligatorio.
- **@handle** y plataforma: `TikTok`, `Instagram`, `Facebook` o `YouTube`.
- **Nicho** y **País**.
- **Audiencia**, **Interacción %** y **Tarifa**, como campos numéricos.
- Etapa de relación, seleccionada de las etapas configuradas. Si no hay una lista configurada, la plantilla ofrece `prospect`, `contacted`, `negotiating`, `producing`, `approved` y `published`.
- **Correo/contacto**, **URL perfil** y **Notas**.

**Guardar creador** crea el registro; durante la operación cambia a **Guardando...**. El pipeline muestra nombre o handle, plataforma, nicho, audiencia y etapa. Cada creador tiene **Contacto**. Esa acción prepara un registro de alcance por correo con estado `planned`, usando una plantilla y sustituyendo variables como creador, nicho y oferta. No envía por sí sola el correo. Si no hay creadores registrados, se muestra un estado vacío. [3]

## Campañas

El formulario **Campaña UGC** contiene **Nombre campaña** —obligatorio—, **Objetivo/oferta**, proveedor (`Manual`, `TikTok` o `Meta`), **Presupuesto** numérico y **Entregables**. **Crear campaña** guarda la campaña y actualiza las listas. El encabezado indica si la función está activa o si **requiere módulo**.

El panel **Campañas** lista campaña, objetivo, proveedor y estado. Incluye **Oferta para generar brief** y un botón **Brief** por campaña. El brief utiliza esa oferta si está escrita; de lo contrario, usa el objetivo de la campaña. El proceso asocia hasta cuatro creadores de la lista y muestra una vista previa breve del resultado. **Brief** genera contenido para revisión; no publica una campaña. [3]

## Recursos

La vista **Recurso UGC** guarda referencias a contenido autorizado y sus metadatos. No es un cargador de archivos: el campo de contenido es **URL contenido/drive**. Los controles son:

- **Título del recurso**, obligatorio.
- Selectores **Creador** y **Campaña**.
- URL del contenido y estado de derechos: `Pendiente`, `Aprobado`, `Limitado` o `Vencido`.
- **Gancho**, **Texto/copy**, **B-rolls / tomas** y **CTA**.

**Guardar recurso** crea el recurso. La lista **Recursos** muestra el título, creador, canal, tipo de recurso y estado de derechos. Al seleccionar un recurso, la interfaz lo carga y cambia directamente a **Rendimiento** para revisar su puntuación. [3]

## Derechos

La subpestaña **Derechos** contiene un formulario **Entregable** con selector obligatorio de **Campaña**, selector obligatorio de **Creador**, **Título del entregable**, fecha/hora de vencimiento y área de texto de requisitos. **Crear entregable** lo guarda; si no se define vencimiento, se envía como vacío.

El panel **Derechos y entregas** muestra recursos y sus estados de derechos. **Aprobar 6m** actualiza el recurso con estado de derechos aprobado y vencimiento de licencia a seis meses desde la acción. También registra una nota de aprobación manual para canales propios que recuerda verificar el contrato antes de pauta; si el recurso estaba en borrador, cambia su estado a aprobado. Es una acción de registro de derechos, no una validación automática de contrato.

La lista de entregables muestra campaña, creador, vencimiento y estado; la plantilla muestra hasta ocho en esta sección. [3]

## Rendimiento

La vista requiere el permiso **Inteligencia UGC**; de lo contrario indica que requiere permiso. Con un recurso seleccionado, muestra su gancho o texto, creador y campaña, y las métricas **Creatividad**, **Rendimiento** y **Reuso**, más los problemas detectados cuando existan.

**Puntuar** solicita una actualización del análisis del recurso y refresca los datos. **Derechos OK** ejecuta la misma aprobación de derechos por seis meses descrita en la subpestaña Derechos. El panel **Mejores recursos** lista recursos con recomendación de reutilización y puntuación creativa; seleccionar uno cambia el recurso en contexto. [3]

## Spark

La subpestaña **Spark** muestra si la revisión previa de Spark Ads está activa o si **requiere módulo**. Para un recurso seleccionado presenta su título, estado de derechos y puntuación creativa. **Ejecutar revisión previa** solicita un preflight y luego muestra las razones y el estado devueltos.

El panel **Contacto** lista registros de alcance con creador, estado, canal, próxima fecha de seguimiento y mensaje. En esta plantilla, el control visible de Spark es una revisión previa; no aparece un botón de publicación de anuncios. [2] [3]

## Auditoría

**Auditoría Creator CRM** es una lista de eventos con contador. Cada fila presenta tipo de evento, fecha/hora y referencia del elemento relacionado, como un creador o recurso. En la vista declarada no aparecen controles para editar eventos ni filtros propios. [3]

## Flujo entre subpestañas

La secuencia funcional que conectan los paneles es: registrar creadores; crear una campaña y generar un brief; guardar recursos asociados a creador/campaña; registrar entregables; revisar puntuación, reuso y derechos; y, si está habilitado, ejecutar la revisión previa de Spark. **Contacto** deja preparado un alcance planificado. La aprobación de derechos y el preflight son acciones distintas y no equivalen a publicar contenido o anuncios. Las funciones de campañas, inteligencia UGC y Spark pueden depender de módulos o permisos habilitados. [2] [3]

## Referencias

[1]: https://app.scentra-ai.online/ "Scentra +AI"
[2]: https://app.scentra-ai.online/assets/index-DWDcwbSI.js "Bundle principal y definición del módulo CRM de creadores"
[3]: https://app.scentra-ai.online/assets/CreatorCrmPanel-CLnfh3CB.js "Componente público del CRM de creadores"
