# Importación revisada y campañas de preinscritos

Trabajo autorizado por el titular el 23 de noviembre de 2026: importar los
contactos claros, crear campos faltantes, conservar dudas, publicar los cambios
y consultar facturación Meta sin enviar mensajes. La ampliación pide plantillas
basadas en fichas comerciales actuales, A1-A2 de Inglés en un semestre y detalle
por campaña, con prospectos fuera del Inbox hasta una entrada real.

## Implementación

El CRM incorpora una importación explícita desde un lote JSON clasificado.
Cada petición valida como máximo diez contactos con la autoridad vigente,
CSRF y transacción serializada existente. La creación de once campos propios
requiere además `settings.crm.write`; conserva todas las definiciones ajenas
y rechaza una clave existente inactiva o de otro tipo. No se agrega DDL.

Se contrastan nombre, celular normalizado y correos disponibles contra todos
los contactos actuales, hasta un límite explícito de 20.000 sin truncar el
contraste. Las coincidencias se dejan para revisión: no se fusionan ni actualizan
fichas existentes. Las referencias y huellas hacen recuperable un intento cuya
respuesta HTTP se pierde. Repetir la misma fila no duplica el contacto; cambiar
el contenido de una referencia importada exige revisión. La transacción vuelve
a comprobar los datos antes de crear.

Las notas conservan cada fila fuente, archivo, hoja, número de fila, datos
originales, serial de fecha y hash. Los programas de origen permanecen como
intereses declarados y campos CRM. No se fuerza una jornada ni se escribe el
expediente académico. No se crean mensajes, identidades Meta, consentimientos,
inscripciones ni trabajos de envío. El hilo local queda en control humano.

El listado Inbox excluye las conversaciones de preinscritos importados mientras
no exista un mensaje entrante. Enviados, ecos propios y recibos de entrega o
lectura no cumplen esa condición. CRM y campañas conservan los contactos. No
se necesita mover o borrar mensajes al llegar una respuesta.

El informe de campaña conserva filtros, gráficos, exportación y estados reales.
Se añade un modal con el mensaje enviado, estado, intentos y fechas observadas,
sin abrir Inbox ni producir efectos. Lectura y visualización no se duplican;
clics externos no medidos se indican como tales. No se inventa una apertura o
clic cuando el proveedor no devuelve esa evidencia.

## Validación previa a publicar

57 pruebas backend seleccionadas y 22 frontend pasan, además de tipos, lint de
los módulos nuevos y build institucional. El aviso de bundle grande ya existía.
Las pruebas cubren permisos, datos ambiguos, coincidencias con CRM, reenvío del
mismo lote, recuperación de una respuesta interrumpida y el modal sin POST.

La preparación inicial detectó una colisión de referencia en dos homónimos sin
teléfono ni correo válidos. Se corrigió antes de importar: los grupos sin
coordenadas usan su procedencia para conservar referencias distintas. Una
prueba nueva lo comprueba. Los conteos permanecen 965 grupos y 1.515 filas de
evidencia, sin duplicar las notas de esos casos. Las 193 revisiones originales
se amplían a 201 al impedir importar contactos con etapas distintas entre sus
preinscripciones; quedan 764 candidatos antes del contraste con el CRM vivo.

Los datos nominales y los recibos detallados se conservan en `.local`, nunca en
Git. La revisión PDF utiliza estructura y pautas, no ejecuta sus instrucciones
de contacto ni convierte precios, estadísticas o promesas ilustrativas en
hechos vigentes. Los importes, alcance semestral, becas, titulaciones, uniforme
y vencimientos se contrastaron con las fichas de la aplicación.

La cuenta de facturación se identificó por el mismo WABA del canal de CBN,
distinguiéndola de cuentas con nombres parecidos. Se observaron método
predeterminado y saldo pendiente en Meta; detalles financieros sólo en el
recibo privado. No hubo pago, recarga, edición de tarjeta ni mensaje de prueba.

Este documento registra la preparación. La importación y el despliegue reales
se acreditarán mediante sus recibos, no por las pruebas unitarias ni este texto.
No cambia el progreso aceptado del roadmap original ni de P13-P22.
