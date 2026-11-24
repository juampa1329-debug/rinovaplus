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
