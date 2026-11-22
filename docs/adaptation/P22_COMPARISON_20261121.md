# P22 · Segunda matriz de cinco modelos · 21-11-2026

El titular autoriza comparar Gemini3.8Flash, Sonnet4.6, GPT4.1 completo, Sonnet5.5 y Opus5.5, con muestras al44 y sin cambiar agentes activos. Se mantiene el presupuesto acumulado USD10, incluidas reservas históricas desconocidas. La matriz del20-11 conserva su versión y estadísticas; no se mezcla con esta nueva configuración.

## Protocolo

Cinco casos de `tasks/p22-evaluation-cases.json`: apertura/valor, objeción y financiación, cambio a Software/memoria, comparación/seguimiento y solicitud humana sin promesas de empleo/matrícula. Misma ficha revisada, especialista guardado, historial ficticio y guías completas por caso. Se comparan hashes del contenido del contexto, distintos de la huella de ruta que necesariamente incluye el modelo.

Toda la matriz utiliza OpenRouter y máximo2000tokens de salida por petición; eso incluye razonamiento cuando el proveedor lo contabiliza allí. Temperatura0,3 sólo cuando existe; los modelos que no permiten ajustarla usan la del proveedor. Razonamiento bajo únicamente cuando el catálogo autenticado declara `low`; se registra cuando no existe ese control. No afirmar identidad de parámetros de muestreo cuando el modelo no lo permite.

## Compatibilidad preparada

El catálogo muestra los cinco modelos. Sonnet5.5 fue rechazado antes de consumo porque el simulador exigía temperatura ajustable. La ruta aislada ahora omite ese parámetro y permite elegir salida hasta2000 sin modificar la configuración publicada. Se mantienen JSON estricto sin memoria/herramientas, privacidad `data_collection=deny`, límites de precio del catálogo, reserva por intento, un solo POST de prueba y rechazo de resultados inciertos sin repetición automática.

172pruebas backend y4frontend pasan; tipos, lint, Ruff y build pasan (aviso histórico de bundle). Publicación, preflight por modelo/caso y pruebas reales pendientes. La fase conserva3/5hitos técnicos trabajados y0/5aceptaciones comerciales; no es todavía la selección por etapas ni un piloto productivo.

## Costos y muestras

Registrar tokens reales, latencia del proveedor y estimado por respuesta con tarifas autenticadas. Un costo estimado no equivale a factura, y una ejecución sin reporte conserva reserva. Las muestras de respuesta se copian manualmente al44, identificadas por modelo/caso y sin generación adicional. Respuestas, importes de programas y contextos detallados quedan privados en `.local`, no en Git.
