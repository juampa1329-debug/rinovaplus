# Motores activos y atención de comentarios

Estado: corrección publicada, selecciones recargadas y ensayo real de audio e imagen respondido. Corte de verificación: 26 de noviembre de 2026, 02:23 UTC (25 de noviembre en Bogotá).

Publicación final funcional a45f63d: backend sraangtg5zkko8l9pmeh8ifc, Success/Running, 4m20s, 02:07:40 UTC. Frontend a576ffe: izysljtoh2yyzrjiy1o34yfi, Success, 25s. Este último commit sólo añade documentación y corrige el montaje controlado de un test; conserva el mismo código de producción que a45f63d. No se requiere otro rollout del backend para documentación.

Primer corte productivo: bcc8f67 backend g4el6suefi74a3rdrtiohqnd Success4m17; 8bff156 qkksgvviogkmjpbkbn9tdupj Success5m27, incluye espera de cola. Frontend a99b494 Success45s. Diez felicitaciones verificadas individualmente con «Publicado en Meta» y sin privado asociado; tres solicitudes recientes de Facebook con privado «Aceptado por el proveedor», no entrega/lectura acreditada. No se repitieron intentos ni se alteraron controles IA/Humano. Un comentario ambiguo y otros históricos no se declaran atendidos por este corte.

Ampliación por instrucción del titular: selección específica de visión, independiente de apertura/ventas, con motor compatible y respaldos aprobados. Catálogo Modelos7 y configuración IA37 guardados y recargados: audio OpenRouter google/gemini-3.8-flash; imágenes OpenRouter anthropic/claude-sonnet-4.6; salida4000. El titular autorizó expresamente la interpretación de las notas entrantes mediante OpenRouter; la voz saliente sigue en ElevenLabs con sus controles y expresiones. Apertura Flash3.8, comercial Sonnet4.6 y respaldo Sonnet5.5 se conservan. No se fuerza Gemini directo ni se usa el perfil Lite antiguo como sustituto de estas rutas.

Se encontró en la interfaz real una validación HTML que impedía guardar ajustes con el límite4000 existente: step128 sólo aceptaba3968/4096 alrededor. Cambiado a step1 conservando el rango512–8000; prueba de validez para4000/4001 y rechazo8001. No se cambió4000 para eludir el error.

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

456 pruebas backend focalizadas aprobadas en el corte final, incluidas 27 del archivo de motores activos sobre tarifas/cupo conservado, clave ausente/rechazo explícito, ocho adaptadores de texto sin Gemini, audio acotado al destino seleccionado, visión separada, felicitaciones y recuperación sin replay. Son selecciones solapadas con las pruebas anteriores; no suite completa verde. Ruff E9/F aprobado.

26 pruebas frontend focalizadas, tipos, ESLint de archivos modificados y build institucional aprobados. Bundle final de 1202,89 kB / 348,25 kB gzip; no se ha optimizado en este cambio. Lint global conserva los fallos ajenos documentados en el informe de modelos.

Revisión ampliada del módulo anterior: cinco fallos de test_ai.py reproducidos en copia aislada del commit ee693ea (reintentos Gemini antiguos, clasificación404, timeout, JSON inválido y expectativa de temperatura). En la misma selección previa fueron126 aprobadas/5 fallidas; no se atribuyen a este cambio ni se declara suite completa verde. El respaldo ante401/403 se limita a la política institucional de rutas explícitamente aprobadas, conservando el comportamiento del módulo anterior.

## Ensayo real de audio e imagen

El titular confirmó el envío desde su chat de prueba. Entraron una nota de8s y una imagen a las21:14 Bogotá; el chat estaba en IA y no se cambió su control. Una primera operación sobre la nota quedó obsoleta al llegar la imagen; el turno posterior se confirmó sin error. No se repitió esa operación ni se enviaron respuestas manuales.

La transcripción automática nueva está visible y recoge la preferencia por sábado en la mañana. La respuesta posterior describe la imagen como una guía de Instagram para emprendedores, recupera el objetivo previo de emprendimiento y propone G1 sábado7–12. Llegó en tres partes a las21:16, con cita sólo en la primera; las tres pasaron de Entregado a Leído en la consulta posterior. El diagnóstico nativo confirma openrouter / anthropic/claude-sonnet-4.6 / completed para la respuesta. No se cuantificó precisión OCR ni se ejecutó una batería de imágenes.

ASR está seleccionado y recargado como Flash3.8/OpenRouter, y el backend persiste proveedor/modelo efectivos con la transcripción. El visor actual sólo muestra el texto transcrito y la traza de generación; no permite comprobar por separado en la UI el modelo efectivo de ASR de este turno. No se presenta configuración como una traza observada. No hubo una nota saliente nueva de ElevenLabs en este piloto.

Las13 recuperaciones sociales observadas y el piloto real son inferencias productivas, distintas de un benchmark aislado. No se dispone de costo individual facturado para este turno. No se acredita todo el histórico atendido, precisión perfecta ni nueva aceptación comercial de P22.

Después de revisar las felicitaciones se guardó y recargó una instrucción para agradecer cuando felicitan a un tercero, sin asumir que el comentarista ganó la beca. No se reeditó ni duplicó el comentario ya publicado. La instrucción no sustituye las guardias del backend.

Sin DDL, seeds, nuevos servicios ni escrituras SIIE. P22 conserva 3/5 técnico y 0/5 comercial; P23 conserva 0/9 criterios aceptados. P24 registra el análisis de inicio/carga, con implementación0% y aceptación0/6 por instrucción del titular. Ver P24_LOAD_PERFORMANCE_ANALYSIS_20261125.md y artifacts/live/active-engine-routing-20261125.json.
