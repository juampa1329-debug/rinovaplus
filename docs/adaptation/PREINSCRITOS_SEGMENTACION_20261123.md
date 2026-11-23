# Preinscritos: clasificación previa a la importación

Fecha de corte: 23 de noviembre de 2026, America/Bogota.

Se clasificaron las exportaciones proporcionadas por el titular, sin ejecutar
contenido de sus celdas. Los datos nominales, teléfonos, correos y resultados
detallados permanecen en `.local/preinscritos-analysis/2026-11-23/`, excluidos
de Git. Esta entrega no acredita importación, consentimiento, envío, saldo de
Meta ni publicación de una nueva versión de la aplicación.

## Resultado de los archivos

| Medida | Cantidad |
|---|---:|
| Filas de octubre | 1.053 |
| Filas de noviembre | 462 |
| Filas originales conservadas | 1.515 |
| Agrupaciones provisionales de contacto | 965 |
| Preinscripciones/intereses con fecha propia | 1.050 |
| Filas solapadas de exportación | 465 |
| Contactos con alguna revisión de datos | 193 |
| Contactos con fecha de gestión registrada | 157 |
| Contactos sin fecha de gestión | 808 |
| Programas distintos en los archivos | 32 |

El archivo Octubre contiene 590 filas de octubre y 463 de noviembre. Su nombre
no determina el período. Hay 76 contactos con más de una preinscripción/interés.
Las 965 agrupaciones no son identidades verificadas contra el CRM. Se encontraron
108 coordenadas de contacto compartidas entre grupos con nombres distintos;
se preservaron por separado. Los datos con formato válido no prueban titularidad
ni disponibilidad de WhatsApp.

La agrupación exige nombre normalizado coincidente y al menos un celular o correo
con formato válido compartido. No se fusionan personas sólo por teléfono, correo
o nombre, ni por similitud de nombres. Un mismo contacto conserva sus distintos
programas y fechas. Las copias de una misma preinscripción conservan todas sus
filas de origen; un estado contradictorio queda pendiente de revisión.

## Tiempo y etapa son dimensiones distintas

`Fecha` es la fecha de preinscripción. El campo `Ultimo asesor`, presente sólo en
Octubre, permite extraer una fecha de gestión. No demuestra mensaje, llamada,
entrega ni respuesta. Último contacto verificado queda vacío hasta contrastar la
actividad real del CRM. Sin gestión registrada no significa nunca contactado ni
sin respuesta.

| Tiempo desde la gestión registrada | Contactos |
|---|---:|
| 0–7 días | 39 |
| 8–14 días | 46 |
| 15–29 días | 5 |
| 30–59 días | 67 |
| 60–89 días | 0 |
| 90+ días | 0 |
| Sin gestión registrada | 808 |

Los tramos se calculan a partir de fechas y una fecha de corte explícita, no se
guardan como etiquetas que se vuelvan obsoletas. El Excel permite cambiar el
corte y recalcula días y tramos; sus propuestas de acción pertenecen al corte
original. No se inventaron prospectos con 60/90 días para llenar las categorías.

| Estado agrupado de preinscripción | Cantidad | Propuesta de uso en CRM |
|---|---:|---|
| Pendiente de calificación | 885 | Calificación; revisar historial antes del mensaje |
| En negociación | 142 | Seguimiento, conservando el estado de origen |
| Intento sin respuesta | 6 | Seguimiento; contrastar intentos y respuestas posteriores |
| Negociación no aceptada | 7 | Pausar y revisar motivo; excluir captación automática |
| Inscrito según origen | 1 | Inscripción pendiente de comprobar; no afirmar matrícula |
| Duplicado marcado en origen | 8 | Revisar antes de importar |
| Etapas contradictorias | 1 | Resolver conflicto antes de importar |

Los conteos de etapas son preinscripciones, no personas. El formulario publicado
del CRM muestra Calificación, Seguimiento e Inscripción: no hace falta duplicar
esas etapas. El criterio de prioridad se basa en etapa, tiempo, contexto y calidad
de datos. No se construyó una puntuación de intención ni de probabilidad de matrícula
con información inexistente.

## Campos para el siguiente paso

Reutilizar nombre, teléfono, programa, etapa, tipo e intereses nativos. Comprobar
en la configuración vigente si ya existen correo, fecha de preinscripción,
estado de origen, canal de inscripción, fecha/asesor de gestión, procedencia y
revisión de importación. Crear únicamente los que falten mediante la configuración
CRM. Las fechas verificadas, dirección y resultado de la actividad deben alimentar
los cálculos de tiempo; no sustituirlas por la fecha de preinscripción.

No asignar asesor por nombre parecido, mapear programas por posición ni dar de
alta matrículas. No conceder consentimiento comercial ni entrenamiento por importar.
Los casos ambiguos se mantienen en revisión y no se borran.

## Plantillas

Se prepararon seis contenidos de categoría Marketing, idioma `es`, nombre y
programa como variables, ejemplos ficticios y tres respuestas rápidas incluyendo
la opción de no recibir mensajes:

- `cbn_presentacion_interes_v1`: interés sin gestión documentada.
- `cbn_seguimiento_negociacion_v1`: información pendiente en una negociación.
- `cbn_seguimiento_sin_respuesta_v1`: intento sin respuesta confirmado por historial.
- `cbn_retomar_interes_30_v1`: revisar vigencia del interés.
- `cbn_retomar_interes_60_v1`: retomar o pausar, para historia futura.
- `cbn_cierre_seguimiento_90_v1`: actualizar preferencias, para historia futura.

Se usan pautas de CRM Automation, Follow-up Discipline y WhatsApp Automation ya
instaladas: una pregunta útil por situación, respeto de la respuesta y pausa,
sin precios, plazos, descuentos ni cupos inventados. No hizo falta instalar más
skills. La preinscripción no sustituye el permiso exigido por las guardas del CRM.
Los borradores no acreditan aprobación de Meta.

Los seis se guardaron mediante el editor de Mensajería masiva en la cuenta
WhatsApp · CBN y se comprobaron de nuevo tras recargar la aplicación. Todos
aparecen como Borrador local; ninguna confirmación de envío a revisión de Meta
se seleccionó. Se guardaron cabecera, dos variables CRM, ejemplos ficticios,
pie y tres botones. No se crearon campañas ni se enviaron mensajes. La captura
de esa comprobación está en la salida privada, junto al HTML de vista previa.

Referencias verificadas el 23-11-2026: [política de WhatsApp](https://whatsappbusiness.com/policy/)
y [fundamentos de plantillas de Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview).

## Validación y continuidad

`backend/tools/classify_preinscritos.py` sólo lee archivos y produce JSON/CSV
privados. No abre conexiones SQL, no importa contactos, no crea conversaciones ni
activa productores. Los `.xls` se leen con xlrd 2.0.2, sin macros ni cálculo de
fórmulas. Se conservan archivo/hoja/fila, serial y sistema de fecha de Excel,
así como SHA256 de las fuentes. El destino dentro del repositorio se limita a
`.local`; los CSV neutralizan prefijos de fórmula sin alterar el JSON de evidencia.

Las 11 pruebas pasan y cubren solapamiento, identidades compartidas, homónimos sin
coordenadas coincidentes, nombre numérico, fechas ausentes/futuras, fronteras
30/60/90, varios programas, estados contradictorios y exclusiones comerciales.
El workbook se contrasta contra el resumen independiente, se cambia/restaura el
corte para comprobar recálculo y se revisan las cinco hojas renderizadas.
La exportación se reabrió con un lector independiente: 965 contactos, 1.050
preinscripciones, 1.515 filas de origen y los ocho totales del resumen coinciden;
las fechas de contacto verificado permanecen vacías. El runtime de authoring
devolvió código 1 tras informar la exportación; el archivo existe y su reapertura
y conciliación pasaron. Ruff no está instalado en el runtime usado; no se afirma
una ejecución de lint. `git diff --check` pasa.

Pendiente del siguiente paso: contrastar los contactos con las identidades e
historial del CRM publicado, revisar los 193 grupos señalados, mapear los 32
programas al catálogo, configurar campos faltantes e importar con idempotencia.
La comprobación de facturación deberá hacerse sobre la cuenta de WhatsApp
correcta; el estado Connected del CRM no demuestra saldo o medio de pago.
No se envían mensajes para inferir saldo ni se crean cargos sin una prueba
controlada acordada. Commit/push de esta herramienta no equivalen a importar o
redesplegar la aplicación. Los hitos y porcentajes del roadmap no se modifican.
