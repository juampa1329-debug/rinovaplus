# P22 · Segunda matriz de cinco modelos · 21-11-2026

El titular autoriza comparar Gemini3.8Flash, Sonnet4.6, GPT4.1 completo, Sonnet5.5 y Opus5.5, con muestras al44 y sin cambiar agentes activos. Se mantiene el presupuesto acumulado USD10, incluidas reservas históricas desconocidas. La matriz del20-11 conserva su versión y estadísticas; no se mezcla con esta nueva configuración.

## Protocolo

Cinco casos de `tasks/p22-evaluation-cases.json`: apertura/valor, objeción y financiación, cambio a Software/memoria, comparación/seguimiento y solicitud humana sin promesas de empleo/matrícula. Misma ficha revisada, especialista guardado, historial ficticio y guías completas por caso. Se comparan hashes del contenido del contexto, distintos de la huella de ruta que necesariamente incluye el modelo.

Toda la matriz utiliza OpenRouter y máximo2000tokens de salida por petición; eso incluye razonamiento cuando el proveedor lo contabiliza allí. Temperatura0,3 sólo cuando existe; los modelos que no permiten ajustarla usan la del proveedor. Razonamiento bajo únicamente cuando el catálogo autenticado declara `low`; se registra cuando no existe ese control. No afirmar identidad de parámetros de muestreo cuando el modelo no lo permite.

## Compatibilidad publicada y comprobada

El catálogo muestra los cinco modelos. Sonnet5.5 fue rechazado antes de consumo porque el simulador exigía temperatura ajustable. La ruta aislada ahora omite ese parámetro y permite elegir salida hasta2000 sin modificar la configuración publicada. Se mantienen JSON estricto sin memoria/herramientas, privacidad `data_collection=deny`, límites de precio del catálogo, reserva por intento, un solo POST de prueba y rechazo de resultados inciertos sin repetición automática.

172 pruebas backend y 4 frontend pasan; tipos, lint, Ruff y build pasan (aviso histórico de bundle). Runtime 806e8a9 publicado: backend efhpkw8jbytzbj7fpswpck8i saludable, 4m17s, rollout 22-11-2026 01:14:24 UTC; frontend svca9gbxsriipcyj7pqobuxe Success, 42s. Los 25 preflight y 25 generaciones reales finalizaron; ningún resultado incierto nuevo ni repetición de POST pagado. Un vencimiento del observador del navegador se resolvió capturando el mismo resultado, sin volver a generar.

## Costos y muestras

Las 25 copias manuales al 44 quedaron en el historial una sola vez, con recibos: 1 leída y 24 entregadas en el corte. Cada copia contiene modelo, pregunta, respuesta íntegra, tiempo y costo estimado. El chat se devolvió a IA y se verificó después de recargar. No se modificaron modelos activos ni fichas de clientes desde las inferencias; las copias manuales sí son mensajes reales del ensayo autorizado.

Costo = tokens de entrada/salida reportados × tarifas autenticadas del catálogo. No es factura ni incluye envío Meta, ASR/TTS, herramientas externas o infraestructura; no se verificaron descuentos por caché. La latencia es la generación registrada por el adaptador, sin colas, pausas de conversación ni entrega WhatsApp.

| Modelo (OpenRouter) | Entrada/salida USD por millón | Total 5 respuestas USD | Promedio por respuesta USD | Latencia media s |
|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | 0,75 / 3,75 | 0,049293 | 0,009859 | 4,44 |
| Sonnet 4.6 | 3 / 15 | 0,246495 | 0,049299 | 11,42 |
| GPT-4.1 completo | 2 / 8 | 0,120886 | 0,024177 | 3,12 |
| Sonnet 5.5 | 2 / 10 | 0,223856 | 0,044771 | 4,85 |
| Opus 5.5 | 4 / 20 | 0,451312 | 0,090262 | 8,36 |

Ronda: **USD 1,091842 estimados**. P22 acumulada conocida: **USD 1,8725702**; reservas históricas desconocidas **USD 0,052892631**, conservadas. Total conocido + reservado **USD 1,925462831**, dentro de USD 10. No hubo recarga ni cambio de agentes.

### Costo de cada respuesta

Los números coinciden con las muestras R2 del teléfono. Celdas en USD estimados.

| Caso y muestras | Gemini 3.8 | Sonnet 4.6 | GPT-4.1 | Sonnet 5.5 | Opus 5.5 |
|---|---:|---:|---:|---:|---:|
| Apertura/valor · 1–5 | 0,009777 | 0,048798 | 0,024192 | 0,044394 | 0,089788 |
| Objeción/financiación · 6–10 | 0,010026 | 0,050376 | 0,024078 | 0,044382 | 0,089564 |
| Software/memoria · 11–15 | 0,0098565 | 0,049986 | 0,024334 | 0,044842 | 0,088724 |
| Comparación/seguimiento · 16–20 | 0,00974775 | 0,048519 | 0,023888 | 0,045240 | 0,091200 |
| Límites/atención humana · 21–25 | 0,00988575 | 0,048816 | 0,024394 | 0,044998 | 0,092036 |

Respuestas, importes de programas y contextos detallados se conservan sólo en `.local`, ignorado por Git. Tokens, tiempos, hashes y tarifas están en `artifacts/live/p22-five-models-20261121.json`.

## Qué se observó

Los cinco recibieron exactamente el mismo contenido de mensajes por caso: hash SHA-256 comparado antes de cada generación. Se usaron las fichas guardadas de Barismo 24/v3 y Software 8/v2, la política `cbn-sales-skills-v6` y las guías completas seleccionadas por intención dentro de la biblioteca de 34. La ficha de Barismo ya era v3 al comenzar; no se sustituyó por la versión histórica v2.

Los cinco conservaron Alex, Santa Marta y el objetivo de emprendimiento al cambiar a Software, y respondieron cuatro semestres, sin confundir la carrera con una herramienta para el negocio de Barismo. Esto comprueba lectura del historial ficticio proporcionado: no acredita escritura nueva en el grafo ni traspaso automático del CRM.

En financiación todos utilizaron el abono mínimo documentado, las cuotas y fechas correspondientes, el alcance semestral y la exclusión de uniforme. Gemini y Sonnet 4.6 no enumeraron tan claramente el importe de la primera cuota como los otros tres modelos; el importe se infiere del resto y del total, pero conviene exigirlo explícito. GPT-4.1 usó separadores de miles anglosajones. El beneficio de organizar el siguiente pago para el año entrante apareció sin prometer descuentos nuevos ni cupos garantizados.

La solicitud humana produjo `handoff=true` en los cinco; ninguno garantizó empleo en España, una fecha exacta de prácticas ni matrícula por declaración del cliente. Gemini afirmó directamente que todavía no estaba matriculado: es preferible «no puedo confirmarlo sin verificación», ya que falta de evidencia no prueba un estado negativo. El simulador no ejecutó una transferencia real. Este quinto caso es independiente y conserva el historial base de Barismo; no continúa la salida del tercer caso de Software.

| Modelo | Aciertos observados | Correcciones antes de activarlo |
|---|---|---|
| Gemini 3.8 Flash | Menor costo de esta ronda; calidez, emojis y preguntas pertinentes; recupera nombre, ciudad y objetivo. | Importes legibles, primera cuota explícita y matrícula desconocida expresada sin afirmación negativa. |
| GPT-4.1 completo | Menor latencia media; financiación ordenada y prudente, memoria correcta, respeto a Humano. | Cierres algo genéricos, formato local de importes y menos frases de catálogo. |
| Sonnet 4.6 | Buen vínculo entre emprendimiento, valor y pregunta diagnóstica sobre la objeción. | Añadió formación en barra real «desde el primer día» sin fuente. También exageró independencia de terceros y presentó una errata. No aprobar esa promesa por sonar comercial. |
| Sonnet 5.5 | Memoria y límites correctos, datos financieros completos, rápido para su tamaño en este corte. | Introduce advertencias de empleo no solicitadas y repite financiación completa en seguimiento; fechas ISO poco conversacionales. No mostró ventaja comercial clara sobre los más económicos. |
| Opus 5.5 | Preguntas concretas de proyecto, diplomas opcionales condicionados correctamente y explicación completa. | Más extenso y caro; no se observó una mejora proporcional a su costo para atención cotidiana. |

Las respuestas no se editaron para ocultar esos defectos antes de enviarlas al titular. La muestra de financiación de Sonnet 4.6 queda identificada como **no aprobada para publicación automática** por la afirmación no respaldada. Usar skills no garantiza obediencia perfecta a cada guía; se evalúa la respuesta, no sólo la presencia de las guías.

## Recomendación provisional por etapa

| Etapa o función | Candidato para el siguiente piloto | Motivo y condición |
|---|---|---|
| Nuevo / Calificación | Gemini 3.8 Flash | Atención frecuente con menor costo, tras ajustar los puntos señalados. |
| Programa definido | Gemini 3.8 Flash; GPT-4.1 si se prioriza rapidez | Ambos explicaron el programa y conservaron objetivo/contexto. |
| Propuesta y financiación | GPT-4.1 completo | Condiciones ordenadas y menor latencia; normalizar formato de importes. |
| Dudas y objeciones | Sonnet 4.6 como candidato, GPT-4.1 como alternativa | Sonnet conecta mejor el valor con la inquietud, pero debe superar de nuevo la guarda contra promesas sin fuente antes de activación. |
| Inscripción / Seguimiento | GPT-4.1 completo | Próximo paso prudente; confirmación humana/institucional de matrícula permanece obligatoria. |
| Revisión de casos complejos | Opus 5.5 sólo bajo demanda | Buen detalle; no justifica usarlo en cada turno según esta muestra. |

Sonnet 5.5 continúa como alternativa a evaluar, sin asignación predeterminada. No se cambia el principal ni el respaldo institucional. Son recomendaciones de una observación por caso/modelo, con orden fijo y sin repetición estadística; no prueban tasa de matrícula ni superioridad comercial general.

## Extensión y costo

La guía pide una respuesta breve orientativa de 75 palabras, conservando lo solicitado y todas las condiciones financieras. Sólo una de las 25 respuestas quedó por debajo de 75 palabras; no se acredita cumplimiento uniforme de brevedad. Se puede pedir un turno más breve y una sola pregunta, sin recortar condiciones ni cortar frases. Esa variante requiere otra muestra controlada: no se probó una mejora nueva de resumen en esta ronda.

El contexto de entrada representa la mayor parte del costo aquí. Reducir sólo la salida disminuye algo el costo y la lectura, pero no elimina el costo de fichas y skills. Como ejemplo aritmético a las tarifas observadas, ahorrar 100 tokens de salida reduce USD 0,000375 en Gemini, 0,0008 en GPT-4.1, 0,0015 en Sonnet 4.6, 0,001 en Sonnet 5.5 y 0,002 en Opus; no es una medición de un prompt abreviado.

## Estado del roadmap

P22 conserva **3/5 hitos técnicos trabajados (60%) y 0/5 aceptaciones comerciales**. Comparativa y entrega de muestras terminadas; faltan selección del titular, enlace agente/modelo al pipeline y piloto supervisado con reversión. Las matrices anteriores conservan sus versiones y consumo. No se agregan estos resultados a su denominador ni se acredita P22 al 100% por completar simulaciones.
