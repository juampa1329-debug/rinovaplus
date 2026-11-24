# IA sin cortes internos y aviso de saldo

La alerta roja del Inbox identifica el rate limit de consultas HTTP al CRM, no saldo ni tokens del modelo. La entrada del botón de WhatsApp «Conocer el programa» no se programaba para IA; la normalización/scheduling de botones y listas quedó corregida. Se respondió al caso señalado una vez y se observó Leído; IA restaurada.

## Configuración

En Ajustes → Límites técnicos: activar «IA sin topes internos», activar el aviso de OpenRouter y guardar el umbral (inicial USD5) y cadencia (inicial15min). Se conserva la contabilidad y los topes históricos para poder desactivar la excepción después. No se desactivan límites por mensaje/contexto/voz, controles Humano ni seguridad.

Se requiere la ManagementAPIkey ya prevista en APIs y modelos → OpenRouter. La clave de inferencia no devuelve el saldo total. El monitor usa únicamente GET /api/v1/credits, no pagos ni cambios de cuenta. Sin esa clave, rechazo o indisponibilidad, informa el estado y no interpreta saldo cero. Consulta con cadencia persistida; IO fuera de la transacción; aplica el resultado sólo si política y credencial siguen vigentes. Una alerta cifrada por administrador activo con users.manage en cada episodio de saldo bajo; recupera el aviso después de subir el saldo. El correo conserva cola, permisos, preferencias y límites SMTP existentes.

## Inbox

Las revisiones del listado de otras conversaciones ya no disparan consultas de detalle e historial del chat seleccionado. Se mantiene actualización de detalle cada15s e historial cada10s en primer plano, además de cambios del propio contacto. Un GET que recibe429 reintenta después de Retry-After aunque no sea una consulta periódica; nunca repite POST automáticamente. Mensaje de error distingue CRM de proveedores.

## Validación

104tests backend de presupuesto/monitor/cuentas/correo/recuperación/respaldo y61de agentes;55frontend seleccionados (la nueva prueba de reloj se aisló del reloj global de las anteriores); tipos, ESLint focalizado, Ruff y build institucional pasan. tzdata sólo en entorno local de pruebas Windows. Advertencia de bundle histórico conservada.

La recuperación inicial publicada falló al consultar con LEN sobre PostgreSQL (42883); reemplazado por comparación de texto compatible y regresión añadida. No hubo IO de proveedor en esa consulta fallida. Revisión de destinatarios, recuperación efectiva y activación de ajustes en producción pendientes en este corte. No se acredita alerta real sin consulta y entrega verificadas.

## Verificación nativa

Presupuesto revisión4 guardado y persistido tras recarga: excepción de gasto/tokens y alerta activas; umbralUSD5 y15min. Monitor devuelve management_key_required. La clave de administración sigue pendiente del titular; no se ha probado un correo real de saldo bajo ni leído un saldo global. Función lista para usar al guardar esa clave. No se cambió el correo de acceso de ningún administrador.

Ocho entradas originales recuperadas mediante una revisión explícita: siete consultas obtuvieron34partes,24entregadas y10leídas según recibos nativos. Una solicitud de baja terminó enHumano sin salida; se añade exclusión determinista previa al modelo y a la recuperación, compartida con campañas. No se reenviaron mensajes del historial ni operaciones inciertas. El caso inicial se respondió una vez (Leído), se devolvió aIA y luego hubo respuestas automáticas reales a nuevas preguntas.

El rate limitHTTP120 se conserva. Navegar muy deprisa entre siete fichas con varias pestañas puede volver a alcanzarlo; se observó durante la verificación. Esto no detuvo las generaciones recuperadas. La revisión reduce refrescos por cambios de otros chats y reintenta consultasGET trasRetry-After; no se afirma eliminación universal de429.

107tests de presupuesto/correo/proveedores/respaldo,61de agentes,230focalizados de canales y58de campañas, con solapamientos;55frontend. Pruebas adicionales de optout/tipos se verifican en corte posterior. El despliegue final se registra en artifacts/live/ai-unlimited-balance-20261123.json.
