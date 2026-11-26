# Motores activos y atención de comentarios

Estado: corrección preparada; publicación y recibos reales pendientes de comprobar.

La consulta nativa de Diagnósticos identifica `comment_ai_pricing_review_required` en un comentario de felicitación: se detuvo antes de invocar al modelo. El motor social todavía exigía una revisión semanal del proveedor/modelo antiguo, aunque el motor central seleccionado era OpenRouter. No era falta de saldo ni demostraba una caída de Sonnet.

## Cambios

- Mensajería, comentarios automáticos y sugerencias consultan la política institucional vigente. Una credencial ausente del principal permite evaluar los respaldos aprobados; una clave Gemini no es un requisito para ejecutar OpenRouter.
- Tarifas sociales tomadas del motor central revisionado. Se conserva exactamente el máximo de solicitudes previamente aprobado para cada cuenta; elegir un motor no concede permiso de envío ni aumenta esa cuota. Si falta ese máximo se muestra su causa específica.
- Felicitaciones y agradecimientos sin consulta comercial permiten una respuesta pública breve, sin exigir programa ni iniciar un DM comercial. La lectura opcional de imágenes de publicaciones utiliza los motores activos compatibles y se omite para ese apoyo explícito. Las preguntas, quejas y casos ambiguos mantienen su evaluación.
- Los bloqueos antiguos por esa revisión de tarifa sólo se reconsideran si tenían cero intentos, menos de 24 horas y ningún SendJob, incluido incierto/fallido. Se revalidan versión de comentario, cuenta conectada/verificada, modo IA y configuración; Humano y cambios de origen detienen la recuperación. Se conserva en metadata el motivo anterior. No se reenvían salidas inciertas.
- Cada inferencia central reserva por ruta una sola vez. La concesión social se alinea con el margen de generación y respaldo, sin cambiar pausas, horario ni trabajadores.
- Transcripción separada de ventas: proveedor/modelo de audio configurados, opciones Gemini, Groq y OpenRouter; no se usa el modelo Lite histórico como sustituto. OpenRouter ofrece sólo modelos del catálogo que declaran audio de entrada y texto de salida. Se guarda proveedor/modelo realmente utilizados. Un modelo sólo de texto no recibe notas de voz; los respaldos de audio permanecen en el proveedor seleccionado.
- Los adaptadores de texto admiten los proveedores configurables existentes. Se contrastan límites publicados cuando están disponibles y se conserva un límite local de petición; si el catálogo directo no publica contexto/salida no se inventan esas capacidades. Imágenes y audio requieren adaptador compatible, y pueden pasar al siguiente motor aprobado. No equivale a certificar todos los modelos de todos los proveedores.
- Identificadores históricos `gemini_whatsapp`, `comment_auto_gemini` y similares permanecen para compatibilidad con recibos e idempotencia: no seleccionan el proveedor.

## Validación

454 pruebas backend focalizadas aprobadas, incluidas 25 nuevas sobre tarifas activas/cupo conservado, clave ausente/rechazo explícito, ocho adaptadores de texto sin Gemini, audio acotado al destino seleccionado, felicitaciones y recuperación sin replay. Son selecciones solapadas con las pruebas anteriores; no suite completa verde. Ruff E9/F aprobado.

25 pruebas frontend focalizadas, tipos, ESLint de archivos modificados y build institucional aprobados. Bundle histórico de 1202,69 kB / 348,19 kB gzip; no se ha optimizado en este cambio. Lint global conserva los fallos ajenos documentados en el informe de modelos.

Revisión ampliada del módulo anterior: cinco fallos de test_ai.py reproducidos en copia aislada del commit ee693ea (reintentos Gemini antiguos, clasificación404, timeout, JSON inválido y expectativa de temperatura). En la misma selección previa fueron126 aprobadas/5 fallidas; no se atribuyen a este cambio ni se declara suite completa verde. El respaldo ante401/403 se limita a la política institucional de rutas explícitamente aprobadas, conservando el comportamiento del módulo anterior.

No nuevas inferencias pagadas de ensayo en esta corrección local. Las respuestas automáticas productivas y sus recibos se verificarán después del despliegue. La selección de audio productiva todavía está en Gemini 3.8 al preparar este corte; la capacidad de elegir otro proveedor no acredita una transcripción real.

Sin DDL, seeds, nuevos servicios ni escrituras SIIE. P22 conserva 3/5 técnico y 0/5 comercial; P23 conserva 0/9 criterios aceptados. La demora de inicio/carga se analizará por separado, sin implementar optimizaciones por instrucción del titular.
