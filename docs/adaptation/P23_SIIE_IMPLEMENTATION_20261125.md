# P23 · Implementación y comprobaciones del 25 de noviembre

La preparación de inscripción y recepción de SIIE está publicada, con envíos finales y webhook desactivados por defecto. La fase completa sigue en validación: **0/9 criterios aceptados**. Los siete criterios originales se conservan y se añaden webhook/clasificación y volante PRE-ICFES. No se alteran aceptaciones previas ni P22.

## Lo implementado

- Admisiones → SIIE → **Inscripción y webhook**: borradores protegidos, once secciones nativas, selección desde programas/ofertas vigentes, requisitos reales, revisión antes del envío y recibos separados de los borradores. Los IDs no se deducen desde etiquetas.
- Cuatro rutas de Registration 2 mediante `SIIE_API_TOKEN` existente, conservando la carpeta configurada `SIIEWebPlus`. El navegador no recibe esa clave.
- Documentos: 10 MiB por archivo, 50 MiB total; extensión y firma; fotografía JPG/PNG; nombres generados para transportar, sin aceptar rutas. Los archivos van a SIIE; no se guardan como adjuntos públicos del Inbox. El límite de proxy de 51 MiB sólo se aplica a estas dos rutas autenticadas.
- Una intención duradera precede cada POST. Un mismo comando no vuelve a enviar; ante timeout, reinicio, 201 inválido o commit incierto, bloquea repetición automática. Un conflicto no confirma que dos formularios sean iguales. La conciliación funcional aún necesita el piloto y la consulta de SIIE prevista en el contrato.
- `POST /hooks/siie/v1`: HMAC, reloj de cinco minutos, 64 KiB, JSON estricto, evento estable y secuencia. Acuse después del commit local, dedupe y conflicto de contenido. Firma entrante separada en `SIIE_WEBHOOK_SECRET`, aún pendiente de configuración.
- El formulario de preinscripción ya exige cédula, según confirma el titular: el flujo normal envía documento e `idPreinscripcion`. Este último conserva la referencia técnica hasta la inscripción, junto a los IDs nuevos, sin sustituir la corroboración del documento. La tolerancia a una preinscripción sin documento sólo sirve para una excepción de integración; no autoriza acceso privado. Formato incorrecto se rechaza; cambio de un documento vinculado exige revisión. No se verifica la existencia de la cédula en un registro oficial.
- CRM: origen SIIE filtrable frente a importados Excel y redes; clasificación preinscrito/inscrito. Una inscripción excluye promociones en selección y en despacho de campañas y seguimientos, incluso por alias o teléfono coincidente. No concede consentimiento comercial ni cambia Humano.
- Coincidencias de teléfono: no fusionan personas. El evento queda para revisión del vínculo; si acredita inscripción, se detienen promociones a los candidatos mientras se revisa.
- Formularios y recibos privados cifrados en el almacén existente. Un usuario de sólo consulta ve metadatos del listado; el detalle requiere gestión CRM y módulo Admisiones. Configurar el receptor requiere permiso de webhooks y reautenticación reciente. No se envían estos formularios a modelos ni a conocimiento de agentes.

## Comprobaciones reales

Primera publicación `6d94350`: backend `muhx2pkozoladedthupn7mpq` saludable/Success, 4m32; frontend `j79mjet5crnu2uesisjpnzbs` Success, 45s. Ajuste `c6efe9d` saludable/Success, 4m30. Código final `158be10`: backend `d3cf5mcupoxqkrleycbfrjkm`, Finished y aplicación Running, 4m21; frontend `tz7xw0hdvqiyu56ldyxyejzc`, Success, 45s. Las lecturas nativas posteriores recuperaron los dos requisitos sin alertas. A las **11:36:46 de Bogotá**, los nueve procesos estaban Al día y PostgreSQL respondía. Esto acredita ese corte, no un SLA ni ausencia permanente de fallos.

En el CRM, filtro SIIE: cero registros antes del primer evento. Importados Excel: **772 resultados**, con etiqueta visible. Ambos cargaron sin alerta. La recepción aún no tiene eventos reales.

Con la clave única actual, la pantalla consultó programas ofrecidos, incluidos **PRE ICFES SABADO**, **PRE ICFES SABADO B** y **PRE ICFES DOMINGO**. Se preparó **un borrador vacío**, sin nombres, cédulas, aceptación de políticas ni archivos, para PRE ICFES SABADO, oferta 2027-A, DIURNA, nivel 1. Es preparación local; no una inscripción ni un aspirante creado en SIIE.

La consulta protegida de tipos de documento devolvió **CC, TI, CE, PA, NIP y PPT**. La jornada proviene de la oferta. Quedan seis catálogos sin ruta documentada: departamentos, EPS, géneros, modalidades, municipios y tipos de estudio. El formulario permite guardar; los selectores dependientes no admiten IDs inventados y bloquean el envío final.

La primera consulta de requisitos recibió HTTP 200 pero falló la validación local: sin estudiante consultado, SIIE devuelve `archivoExistente=null`. El cliente exigía un booleano. Se conserva ahora el estado desconocido y la interfaz muestra **Archivo sin comprobar**. La consulta real posterior recuperó sin alertas:

- Documento de identidad: obligatorio inicial, entrega no marcada y archivo sin comprobar.
- Documento de identidad del acudiente: entrega posterior, aplicabilidad pendiente de edad, entrega no marcada y archivo sin comprobar.

No se subieron archivos ni se ejecutaron las tres escrituras de SIIE. No hay prueba real productor→webhook, inscripción completa, conciliación de escritura, generación de volante ni envío de PDF.

## Verificación local

Selección inicial: 298 backend y 19 frontend. Selecciones posteriores de 118, 160 y 113 backend se solapan; no se suman. El archivo actual de P23 contiene 54 casos, incluidos SQL ejecutado con datos sintéticos y consultas traducidas analizadas como PostgreSQL, firma/dedupe, identidad, exclusión de promociones, POST incierto, multipart, edad y consentimiento. La interfaz añade la prueba de consulta sin acceso a expedientes privados. Tipos, ESLint, Ruff y build institucional pasan; permanece el aviso de bundle histórico. No se afirma que la suite completa sea verde.

## Dependencias para aceptar la fase

1. Compartir el [contrato del webhook](SIIE_WEBHOOK_CONTRACT_V1.md) con el desarrollador de SIIE; configurar la firma en ambos lados y habilitar el receptor con una etapa inicial vigente. Emitir después del commit con reintentos duraderos.
2. Recibir los seis catálogos oficiales, con sus IDs y reglas de consulta; no sustituirlos por un listado manual de IDs.
3. Acordar retención y ejecutar un piloto con datos/archivos de ensayo autorizados, incluida la conciliación de resultados inciertos y el comportamiento de las tres escrituras. La instalación y permisos de SIIE deben ser confirmados por su responsable; RinovaPlus no aplica su SQL.
4. Para PRE-ICFES, aportar el contrato de consulta de inscripción previa a matrícula, modalidades/planes vigentes, generación idempotente de volante, consulta de la orden y descarga autenticada del PDF. El titular aprobó preparar este flujo, pero esas rutas no están documentadas en Registration 2.

Nombre o cédula solos no autorizan abrir un expediente o entregar un PDF. El recorrido acordado usa IDs confirmados, vínculo de contacto verificado y elección expresa de contado/financiado. Generar un volante no acredita pago ni matrícula.

## Reversión

Desactivar recepción/envíos finales desde la preparación de SIIE; conservar recibos, vínculos, borradores e intenciones inciertas. Una imagen previa permite revertir código, pero no se deben borrar los registros ni volver a enviar operaciones desconocidas. No hay DDL, seeds ni servicios nuevos que revertir. Las lecturas previas de P16 y las guardas del Inbox se conservan.
