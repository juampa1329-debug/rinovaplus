# P16 · Clave única, estudiantes y período ofrecido

Corte del consumidor: 19 de noviembre de 2026. Contrato vigente: [entrega de clave única](../contracts/siie/20261119-single-key/GUIA_API_CRM_SIIE.md), [inventario](../contracts/siie/20261119-single-key/API_INVENTORY.md). Adaptador de 12 GET desplegado saludable; clave única, aspirantes y estudiantes comprobados en el servidor real y la UI. Catálogo sigue bloqueado por metadatos de período ausentes y detalles financieros503 del productor. No hace falta otra clave: seguir [el diagnóstico y las correcciones pendientes de SIIE](P16_SIIE_PROVIDER_ISSUES_20261119.md). P16 conserva 0/5 unidades completas aceptadas.

## Una clave en Coolify

Backend RinovaPlus → Environment Variables → Production. Sólo Runtime; Build time desactivado. El propietario introduce y guarda la clave directamente allí; nunca en chat, Git, capturas, parámetros URL o logs.

| Variable | Valor / finalidad |
|---|---|
| `SIIE_API_BASE_URL` | `https://siieplus.online/SIIEWebPlus` |
| `SIIE_API_HOSTS` | `siieplus.online` |
| `SIIE_API_TOKEN` | Clave original única, al menos 32 caracteres, autorizada por SIIE. No su SHA-256. |

No se necesita otra clave de Admisiones. `SIIE_ADMISSIONS_API_TOKEN` no se utiliza en este adaptador. Sólo si `SIIE_API_TOKEN` no existe, se mantiene temporalmente `SIIE_CATALOG_API_TOKEN` como la misma credencial para todas las lecturas. Una variable principal presente, incluso vacía o incorrecta, impide volver a la anterior. Un rechazo tampoco dispara reintentos con otra clave. Tras rotar y validar, revisar con el custodio la retirada de variables antiguas; no se borran claves de otros consumidores.

Guardar la variable no cambia el proceso ya iniciado: requiere redeploy del backend. No modificar Oracle ni las claves de Meta. Académico → Abrir SIIE → Comprobar conexión configurada informa configuración/modo, nunca el secreto. El acceso sólo se acredita con lecturas satisfactorias en cada sección.

La versión nueva del productor unifica la validación en `API_Key` y conserva `API_CRM` como alias. Errores `api_credential_not_configured`, `api_credential_config_invalid` y `api_credential_config_conflict` se explican como configuración del servidor SIIE; no se corrigen alterando el CRM. La guía documenta publicación remota pendiente: comprobarla antes de atribuir un rechazo a la clave nueva.

## Consultas y período

1. Programas y finanzas → Obtener programas. Predeterminado: período ofrecido resuelto por SIIE. `GEParametros` 38 tiene prioridad; puede diferir del período académico activo. La paginación fija el período efectivo para no incorporar históricos por accidente. Una respuesta antigua sin ese período se rechaza con explicación.
2. Elegir programa y oferta `Id-nNivel`; revisar escuela, jornada, período, nivel, materias, procedencia y calidad. `duration_levels` son niveles, no meses. Programas/ofertas: 25 por página y cursor opaco.
3. Ante 422 `source_data_incomplete`, conservar `partial_offer` y `data_quality` para inspección. No guardar ni publicar en agentes una oferta no cotizable. La evidencia real anterior de 503 se conserva; no demuestra el resultado de la versión nueva.
4. Contado y `full_cost_cash_cop` de esta fuente son enseñanza del semestre/nivel, no todo el programa ni uniformes/extras. Mostrar abono, cuotas, fechas y suma almacenados sin regenerarlos. Sede y vigencias comerciales pueden ser null según el nuevo contrato de inspección. Requisitos de ingreso y condiciones financieras siguen pendientes; la guía todavía declara ofertas 422 por esos dos bloqueos.
5. Aspirantes y seguimiento → Obtener períodos; predeterminado ofrecido. Consultar históricos sólo al elegirlos. Obtener filtros oficiales, buscar, paginar y abrir ficha/historial. Conservar criterios de la búsqueda aplicada aunque se edite el borrador. `confirmadoOrigen` o estados de seguimiento no equivalen a matrícula.
6. Estudiantes y matrículas → Obtener período ofrecido, filtros, búsqueda y ficha. El estado 0 es válido; códigos sin etiqueta siguen sin etiqueta y con revisión. El estado actual del estudiante no representa el estado histórico de cada matrícula. La jornada procede de su matrícula; no suplirla por la del programa.
7. Aspirantes/estudiantes muestran teléfono, celular y correo nativos cuando existan. No normalizar país, declarar consentimiento ni fusionar personas. Mantener `idPersona`, `idAspirante`, sede o período de ingreso null cuando no hay relación confirmada. No publicar datos personales en evidencia de Git.

## Alcance y pruebas de cierre

Rutas consumidoras: `programs`, `offers`, `offer`, `periods`, `states`, `filters`, `applicants`, `applicant`, `history`, `students`, `student`, `student_filters`, más estado local. Las otras seis lecturas antiguas de Preinscripciones/Moodle y las tres escrituras del inventario no se habilitan por compartir autenticación. No ejecutar toda la colección: contiene escrituras reales.

Pendientes para aceptar P16: autenticación única/rechazo/rotación reales; período y paginación; aspirantes/estudiantes sin cruces de identidad; dos ofertas completas y revisadas; vínculo local y cambios/bajas sin sobrescribir correcciones; uso factual por Gemini y Humano; disponibilidad/recuperación/operación y aceptación institucional. La cartera personal no está en el contrato ni es el precio de un plan.

Las escrituras de seguimiento requieren antes persistencia de solicitud/comprobante, identidad reciente, autoría, revisión humana, idempotencia, revisión esperada y reconciliación de resultado incierto. No se necesita escribir en SIIE para validar la nueva clave.

## Límites y diagnóstico

`agents.manage`, sesión y módulo/SQL antes y después del IO. Sólo GET de rutas fijas, TLS, dominio permitido, sin redirecciones ni proxies del ambiente; conexión 5s, lectura 15s, respuesta máxima 512 KiB. IDs int32; estado de estudiante acepta 0; cursor 128, búsqueda 100, offset hasta un millón. Sin rastreo masivo ni reintento automático.

401/403: comprobar versión y clave original vigente. 404: referencia/período. 429: respetar Retry-After. 503: configuración/disponibilidad del productor. No exponer mensajes SQL ni el secreto. En respuesta satisfactoria, conservar correlación sólo si tiene formato seguro.

Pausa: vaciar la variable principal y redesplegar; su presencia impide volver a la clave anterior. El catálogo local revisado se conserva. Reversión: conservar y restaurar la imagen/configuración previas compatibles; el productor y otros clientes deben coordinar cualquier rotación, sin borrar sus claves. No hay DDL, seeds, matrículas, cobros ni escrituras académicas por instalar el consumidor.
