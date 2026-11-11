# Módulo Clientes — especificación funcional

**Aplicación:** [Scentra +AI][1]  
**Revisión:** 13 de octubre de 2026

> Al intentar abrir Clientes en la sesión actual, la interfaz quedó en **Plan y consumo** en lugar de mostrar el módulo. Por eso, no pude validar registros ni opciones dinámicas en pantalla. La especificación siguiente se basa en el componente público `CrmPanel`, que define la vista **Clientes y oportunidades** y sus controles. [1] [2] [3]

## Estructura

La página se presenta como **CRM comercial** y se titula **Clientes y oportunidades**. Su descripción define una ficha comercial persistente por empresa con datos del cliente, etapa, pago, intereses, notas y etiquetas. El componente se organiza en tres paneles: **Base de clientes**, **Ficha CRM** y **Configuración CRM**. En el encabezado hay un botón de ayuda contextual y **Actualizar**, que vuelve a cargar la información. [2]

## Base de clientes

El panel **Base de clientes** muestra el total de registros cargados, un botón **+ Nuevo** y un buscador con el placeholder `Buscar por nombre, teléfono, ciudad o etiqueta`, junto con **Buscar**. La carga de la lista solicita hasta 100 registros por llamada; en esta plantilla no aparece un control visible de paginación. [2]

Cada fila seleccionable muestra avatar, nombre visible —o teléfono/identificador externo si falta—, etapa comercial, estado de pago y modo de atención **Humano** o **IA**. Al seleccionar una fila, la ficha se carga en el panel central. Si no hay registros, aparece el mensaje que invita a crear uno manualmente.

## Ficha CRM

La ficha presenta un resumen compacto del cliente y un formulario de creación o edición. Los campos base son:

- **Nombre visible** y **Teléfono**.
- **Nombre**, **Apellido** y **Ciudad**.
- **Tipo de cliente**, como texto libre; el placeholder sugiere valores como `minorista, mayorista, VIP...`.
- **Tipo de identificación**, selector con `Sin definir`, `Cédula de ciudadanía`, `Cédula de extranjería` y `Pasaporte`; y **Número de identificación**.
- **Etapa comercial**, selector alimentado por las etapas CRM configuradas. Si no hay etapas configuradas, se ofrecen `Contactado`, `Interés`, `Intención de compra`, `Pago pendiente` y `Pago confirmado`.
- **Estado de pago**: `Sin estado`, `Pendiente`, `Pagado`, `Fallido` o `Devuelto`; **Referencia pago**; e **Intención IA**.
- **Intereses** como área de texto, **Etiquetas texto** y **Notas internas** como área de texto.

Para crear un cliente se usa **+ Nuevo** y luego **Crear cliente**. La validación exige al menos **Nombre visible o Teléfono**. En edición, el botón es **Guardar ficha**. **Cancelar** descarta el borrador de creación y vuelve a la selección anterior. Si ya existe un cliente seleccionado, **Abrir en inbox** lleva a su conversación cuando hay una vinculada. [2]

Debajo de **Etiquetas texto** aparecen las etiquetas activas configuradas para la empresa, con su contador de uso. Al pulsar una etiqueta, se aplica a la ficha y se actualizan la lista y las etiquetas disponibles.

Los **Campos personalizados** se añaden a la ficha según la configuración CRM. Los booleanos aparecen como casillas; los tipos de lista, como selectores; y los demás, como entradas con el tipo definido. Las opciones visibles dependen de los campos configurados para la empresa.

### Cobros Stay, si está habilitado

Cuando Stay está habilitado y se selecciona un cliente existente, aparece la tarjeta **Cobros Stay**. **Refrescar** vuelve a cargar sus cobros. El formulario incluye **Valor**, **Moneda** —por defecto `COP`—, **Proveedor** —por defecto `manual`—, **Canal de entrega** —por defecto WhatsApp—, **Concepto** —por defecto `Reserva Stay`—, **Correo opcional** y **Link de pago opcional**. Los canales son WhatsApp, correo, sitio web, punto de venta y copiar link; los proveedores disponibles dependen de la configuración. Se valida que el valor sea mayor que cero.

**Enviar cobro** crea un registro de cobro. La tarjeta lista hasta cinco cobros y ofrece acciones de entrega por WhatsApp, Email o Web/POS, además de **Copiar**. Según el estado, permite marcar **Enviado** o **Pagado**. Estas acciones modifican o comunican información financiera; aquí solo se documentan, no se ejecutaron. [2]

### Eliminación

Si el usuario tiene permiso de borrado, la ficha ofrece **Eliminar cliente**. El botón abre un diálogo que explica que la acción oculta el cliente del CRM, detiene automatizaciones pendientes y queda registrada en auditoría; también aclara que no borra datos de otros clientes.

El diálogo contiene **Motivo interno** y **Tu clave actual**. El motivo es opcional; la clave es obligatoria para habilitar **Eliminar cliente**. También incluye **Cancelar** y **Cerrar**. El código implementa esta operación como baja lógica, no como borrado físico de todos los datos. [2]

## Configuración CRM

El panel **Configuración CRM** muestra cuántas etapas y campos personalizados hay definidos para la empresa.

### Pipeline por industria

El selector ofrece los presets de industria configurados y **Aplicar preset** aplica la selección al pipeline. Las etapas existentes se muestran con su orden, nombre y probabilidad porcentual. Si no hay etapas, aparece **Sin etapas configuradas**.

El formulario **Agregar etapa** contiene una clave (`clave_etapa`), **Etiqueta visible** y un campo numérico de probabilidad entre 0 y 100. La clave y la etiqueta deben estar completas para crear la etapa. La plantilla no muestra controles para editar o eliminar etapas existentes.

### Campos personalizados

El formulario para crear un campo incluye **clave_campo**, **Etiqueta visible**, selector de tipo y **Opciones separadas por coma**, además de **Crear campo**. Los tipos disponibles son **Texto**, **Número**, **Lista**, **Fecha**, **Sí/No**, **Correo**, **Teléfono** y **URL**. La clave y la etiqueta son obligatorias. Las opciones se separan por comas y se aplican a los campos de tipo lista.

Los campos ya definidos aparecen con etiqueta, clave y tipo. Cada uno tiene **Desactivar**; no se muestra un control de edición en esta vista. [2]

## Referencias

[1]: https://app.scentra-ai.online/ "Scentra +AI"
[2]: https://app.scentra-ai.online/assets/CrmPanel-COecDe4s.js "Componente público CrmPanel de Scentra +AI"
[3]: https://app.scentra-ai.online/assets/index-DWDcwbSI.js "Bundle público principal de Scentra +AI"
