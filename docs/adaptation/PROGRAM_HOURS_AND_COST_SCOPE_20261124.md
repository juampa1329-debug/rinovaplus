# Horarios y alcance de consultas académicas · 24 de noviembre de 2026

## Datos confirmados y persistidos

Se guardaron por interfaz nativa 24 fichas con jornada definida (18 diurnas y 6 nocturnas). Tras recargar, las 24 coinciden con los valores revisados:

- Inglés diurno: 15:00–18:00; Inglés nocturno: 18:00–21:00.
- Otras jornadas diurnas: hasta las 18:00, inicio por confirmar.
- Otras jornadas nocturnas: 18:30–21:00.

Se conservan PRE-ICFES, fines de semana y la oferta sin jornada definida. No se crean días, grupos, cupos ni horas de entrada no informados, ni se escribe en SIIE. Inglés ya tenía ambas franjas en su presentación; ahora también están en el campo Jornada.

## Consultas con ambigüedad de concepto

Un caso real preguntó si el plan de estudios era gratuito o había que pagar. La IA interpretó costo del semestre y dijo no disponer de importes. La ficha nativa de Primera Infancia sí tiene temario y dos planes financieros vigentes; no fue necesario volver a cargar esos datos.

Se localizó una brecha en la vinculación de campaña: se recuperaba el contexto de «Hablar con Juan Pablo», pero no de «Conocer el programa», «Ver jornadas» y «Ver próxima oferta». Esos títulos ahora pueden recuperar programa y jornada sólo desde un botón nativo procesado y una campaña aceptada de la misma institución, cuenta, identidad e hilo. La etiqueta del evento debe coincidir con el texto de la entrada. No incluye bajas, texto libre ni títulos arbitrarios. La excepción comercial de no derivar a Humano sigue siendo exclusiva del botón de Juan Pablo; no se amplía a las demás entradas.

La campaña sirve para identificar el interés; los valores se consultan en la ficha vigente. No se copian importes antiguos del Snapshot al prompt factual ni se cambia una asignación académica/manual. Un cambio explícito posterior de interés conserva precedencia.

Las skills nativas de pricing y discovery añaden aclaración de concepto: cuando el historial no resuelve si se pregunta por consultar las materias o por el costo de estudiar, hacer primero una sola pregunta. No afirmar todavía que es gratis, que debe pagar ni presentar abonos. Si ya pregunta claramente por semestre, matrícula o costo del curso, responder directamente con los datos disponibles. Se reconocen gratis, gratuito, costo, pagar y cobrar; «plan de estudios» sin pregunta financiera ya no se clasifica como financiación sólo por contener «plan».

## Pruebas y límites del corte

96 pruebas focalizadas y Ruff pasan: contexto de botones nativos positivos y negativos, títulos incompatibles, bajas, contrato de derivación, selección de skills, hashes del paquete, ambigüedad temario/costo y conservación de planes financieros y materias. La biblioteca conserva 37 guías y el límite de contexto; se actualiza la expectativa antigua de 34 y se admiten encabezados Markdown de las tres guías sociales existentes. No nuevas inferencias de simulación ni afirmación de resultado generativo por una prueba de ensamblado.

Se están atendiendo las consultas de horarios mediante mensajes nativos expresamente autorizados. Cada envío y restauración IA/Humano requiere recibo real; un estado incierto no se reproduce ni se cuenta como entregado. Publicación y cierre de recibos aún en verificación en este corte.

Aceptaciones anteriores y P22 conservadas. Sin DDL, seeds, servicios nuevos, cambios de modelos ni escrituras SIIE.

## Verificación posterior en producción

Código 55cbb66 publicado y saludable: backend `gxsosyylfe63xt0qmlznfgyw`, Success/Running, 4m17s; frontend `x4no1yivlv0tmxy8kmni9ner`, Success, 24s. No se atribuye a esta publicación una prueba generativa nueva del caso de ambigüedad.

### Inglés: datos confirmados por el propietario

Ambas fichas, diurna y nocturna, revisión 9 comprobada tras recarga:

- A1 y A2 juntos en un semestre. Martes y jueves, 15–18 o 18–21 respectivamente.
- Contado: 1.250.000 pesos hasta el 17/12/2026.
- Financiación: matrícula de 440.000 pesos hasta el 17/12/2026 y dos cuotas de 430.000, con fechas 08/03/2027 y 12/04/2027. Total: 1.300.000.
- Libro Interchange Cambridge adicional: 260.000 pesos, sujeto a ajuste para 2027; pago completo con la matrícula o el nivel según la hoja. No multiplicar por A1 y A2 ni afirmar examen externo incluido.
- Requisitos: inscripción gratuita, identidad del estudiante y del acudiente si es menor, diploma o acta, fotografía JPG y certificado EPS/SISBÉN. Edad mínima 16 años. Documentos mediante formulario oficial o canal seguro, no recopilación por chat.

Se retiró la prohibición provisional de cotizar y la incertidumbre anterior sobre precio por nivel/bloque. Las fechas estructuradas, además de las condiciones escritas, se verificaron tras guardar y recargar las dos fichas. La entrada del calendario necesitó un cambio mediante teclado para registrar el valor en el formulario; no se acredita un defecto del backend ni se hizo una modificación de código de fechas.

### PRE-ICFES: contradicción resuelta

El propietario confirmó G1 sábados 07–12, G2 sábados 13–18 y G3 domingos 07–12; inicio general 13/02/2027. Guardado y comprobado en ficha, sin sumar las 120 horas de cada grupo ni inventar otra fecha. Se conservan 120 horas presenciales por estudiante, plataforma con más de 5.000 preguntas, tutor IA 24/7, materiales, simulacros y reportes; contado 800.000 hasta 15/12/2026, o abono 220.000 y tres cuotas de 220.000 el 10 de febrero, marzo y abril de 2027, total 880.000. Formulario específico PRE conservado. Excepción expresa a edad mínima 16 años comprobada.

### Auditoría de las 27 fichas locales

Las 27 fichas tienen duración, precio, requisitos y contenido académico; 51 planes financieros revisados, sin diferencias entre abono más cuotas y total. Son fichas/ofertas, no 27 carreras distintas: se conserva el registro histórico BARTENDER junto al programa conjunto, sin borrar asignaciones.

| Dato pendiente | Alcance real |
|---|---|
| Jornada de Aduanas | Campo sin jornada; no se deduce de otro programa. |
| Inicio y días de jornadas diurnas generales | 17 fichas: sólo fin de jornada hasta 18:00 confirmado. |
| Días de jornadas nocturnas generales | 5 fichas: franja 18:30–21:00 confirmada, días no informados. |
| Repostería fines de semana | Falta precisar días y horas. |
| Fecha de inicio de clases técnicas e Inglés | No confundir vigencia de pago con inicio de clases. |
| Calendario completo/áreas detalladas PRE | Los grupos, inicio y contenido general están confirmados; no se inventa un cronograma clase por clase. |

La presencia de temario no acredita que cada materia tenga horario o calendario completo. Los campos de vigencia desde vacíos y opcionales no invalidan importes revisados con condiciones y fecha hasta conocidas. Ante un faltante, la IA conserva los datos válidos, explica el punto por confirmar y ofrece continuidad con Admisiones; no se acredita por ello un recorrido automático nuevo de todos los agentes.

### Atención y límites operativos

Las respuestas manuales se envían sólo tras leer el hilo real, mediante Inbox y una sola operación; se restaura el modo IA original después de comprobar el resultado. La orientación prioritaria de Inglés fue Leída y la de requisitos/abono de Cocina fue Entregada. Los recibos agregados de la ronda se registran en `artifacts/live/program-hours-academic-audit-20261124.json`, sin nombres ni cuerpos de clientes.

Un envío de horario conserva resultado Sin confirmar con un intento y `provider_unavailable`: no se reenvía ni se cuenta como entregado. Persisten episodios HTTP 429 al navegar rápidamente por varios hilos/pestañas; es el límite HTTP 120, independiente de tokens o saldo. El aviso de acceso/servicio de la captura también coincide con errores PostgreSQL 55P03 de espera de bloqueo observados en registros sanitizados. La consulta posterior y la respuesta prioritaria funcionaron, pero no se declara eliminada toda contención SQL. No se debilitan locks, autenticación ni límites de seguridad para ocultar esos síntomas.
