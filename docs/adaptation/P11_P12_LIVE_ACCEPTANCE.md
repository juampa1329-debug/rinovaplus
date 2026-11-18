# P11 y P12 · Aceptación de la operación publicada

Corte: **18 de noviembre de 2026**, America/Bogota. El propietario aceptó «Aceptar ese alcance y registrar las mejoras pendientes» después de revisar las pruebas, el manual y los límites. **Roadmap original P0–P11: 100%; 279/279 hitos y 56/56 criterios aceptados.** P11 tiene 4/4 criterios. P12 es una agrupación auxiliar de los 18 hitos originales de puesta online: quedan conciliados, sin añadir criterios ni peso.

## Alcance aceptado

RinovaPlus publicado en <https://app.rinovaplus.com>, PostgreSQL 16.16 en los recursos existentes de Coolify, datos CRM actuales y recorridos acordados P1–P10. El propietario había elegido explícitamente PostgreSQL como entorno definitivo. La referencia literal SQL Server 2019 de P11.3.m2 conserva su texto, peso e historia; la aceptación nueva documenta una **modificación humana explícita del destino a PostgreSQL**, sin afirmar una nueva puesta institucional SQL2019 ni un mapeo completo de DBSIIE.

P11.1 y P11.2 conservan sus aceptaciones previas y sus límites. Se aceptan P11.3 y P11.close, y únicamente pasan a realizados los cinco hitos que seguían pendientes: P11.3.m2/m4/m5 y P11.close.m1/m4. No se vuelven a otorgar créditos por repetir la reversión histórica.

La aceptación de P12 corresponde al alcance actual PostgreSQL y Meta. SIIE académico/financiero continúa diferido a P16 y TikTok a P17 por decisión del propietario. No se registran pruebas nuevas de esos proveedores o sistemas.

## Evidencia revisada

| Recorrido | Resultado observado | Límite |
|---|---|---|
| PostgreSQL | Restauración nativa en otra base aislada; manifiestos de las 157 tablas coinciden con una única instantánea MVCC. | La base activa no fue sustituida; no es un ensayo de promoción de producción. |
| Archivos y claves | 19 archivos restaurados y comparados por nombre, tamaño y SHA-256; autenticadas 1 versión Access y 76 C10. | Los valores de claves, dump y archivos privados no se publicaron. |
| Usuarios | Usuario sintético de rol Consulta creado sin contraseña y desactivado; cero sesiones y desafíos elegibles. | No se activó ni compartió la invitación; su fila histórica queda invalidada por versión/estado. |
| Operación | Motor/version reales, ocho consumidores frescos, colas PostgreSQL, recibo HMAC fechado y HTTPS configurado. | Redis no interviene en estas colas; el recibo no es un rehash continuo ni una garantía RPO. |
| Copias | Base a las 03:00 y volumen a las 03:05 de Bogotá, primeras ejecuciones Success y conservación de copias. | Mismo servidor, agendas independientes; no prueban copia externa ni correo recibido. |
| Reversión frontend | `19866a7` abrió y regresó a `9d8d608`, ambas imágenes saludables, misma sesión y mismos totales de salida. | Backend/base/volumen no se cambiaron durante ese ensayo; no acredita recuperación total del servidor. |
| Colas | Cero envíos pending/running observados; tres inferencias históricas inciertas conservadas sin reintento automático. | No se fabrican recibos ni se reenvían efectos inciertos; el negocio siguió procesando eventos. |

Las pruebas seleccionadas de la revisión operativa fueron **117 backend y 16 frontend**, tipos, lint de archivos modificados y build workspace correctos. La advertencia previa de bundle grande permanece. No se suman los recibos SQL/UI históricos como tests nuevos ni se declara un replay histórico integral: el ledger conserva veinte rutas históricas ausentes. El inventario ampliado del registro de trabajo encuentra **25 rutas ausentes y 11 huellas diferentes**, exactamente las mismas antes y después de este cierre. El comprobador histórico completo no pasa; el comprobador nuevo verifica exclusivamente la transición aprobada, sus preimágenes y el cálculo sin ocultar ese límite ni sustituir los archivos faltantes.

La reversión autorizada terminó a las **14:52:51 de Bogotá** y el retorno a las **14:54:15**, el 18 de noviembre. El rechazo automático inicial se conserva en la historia y quedó resuelto mediante la autorización específica del propietario. Los commits posteriores de documentación conservan el mismo código de aplicación.

## Mejoras abiertas y riesgos aceptados

La aceptación del alcance actual deja pendientes **copia externa, custodia independiente de clave, objetivos institucionales RPO/RTO, supervisión de retención/espacio, entrega real de alertas y un ensayo adicional de conciliación entre cortes DB/archivos**. Las copias locales no cubren por sí solas una pérdida completa del servidor. No se promete un SLA por la duración del ensayo.

Estas mejoras tienen identificadores OPS-01 a OPS-06 en [el registro operativo](../../tasks/operations-hardening-backlog.json), con estado pendiente y referencia a P15/P18 para seguimiento. La aceptación de riesgo no cambia ese estado ni acredita configuración externa. No se habilitan nuevos envíos, campañas, cuentas o factores de acceso con este cierre.

El [manual de operación y recuperación](P11_POSTGRES_OPERATOR_RUNBOOK.md) conserva las instrucciones de aislamiento, preservación de originales, custodia, pausa antes de promover, revocación de sesiones copiadas y conciliación de efectos con Meta.

## Avance vigente

| Fase | Avance / aceptación |
|---|---|
| P0, P1, P2, P3, P4 | 100% cada una, 5/5 criterios por fase |
| P5 | 100%, 4/4 |
| P6, P7 | 100% cada una, 5/5 por fase |
| P8, P9 | 100% cada una, 4/4 por fase |
| P10 | 100%, 5/5 |
| P11 | 100%, 4/4 en el alcance PostgreSQL aceptado |
| P12 | 100% de su agrupación auxiliar en el alcance actual, peso adicional cero |
| P13 | Implementación parcial; 0/4 unidades aceptadas |
| P14 | Plan pendiente |
| P15 · Correos y notificaciones | Planificada; 0/7 unidades aceptadas |
| P16 · SIIE | Diferida; 0/5 |
| P17 · TikTok | Diferida; 0/5 |
| P18 · Seguridad y ciberseguridad | Planificada; 0/8 |

El 100% se refiere al **roadmap original de 56 criterios** y al alcance humano documentado. Las fases adicionales conservan sus estados propios y no están incluidas en ese denominador.

## Trazabilidad

- [Aceptación final por criterio y alcance](../../artifacts/live/p11-postgres-acceptance-20261118.json).
- [Revisión técnica conservada](../../artifacts/live/p11-postgres-review-20261118.json).
- [Preimágenes exactas anteriores al cierre](../../artifacts/live/history/p11-postgres-20261118/phase-progress-contract.json.before).
- [Validación del cambio de estados y cálculo](../../artifacts/live/p11-progress-validation-20261118.json).
- [Avance P11 actual](../../tasks/p11-live-progress.json) y [conciliación auxiliar P12](../../tasks/p12-online-backlog.json).

Los releases, checkers, grafos y recibos SQL anteriores permanecen sin cambios. Las cabeceras fechadas inferiores de los documentos generales son historia; este corte es la autoridad vigente para la operación aceptada.

Comprobación reproducible sin acceso SQL: `python -X utf8 -B backend/tools/check_p11_live_closure.py`. Informa por separado el cierre actual y el inventario histórico incompleto. No modifica la aplicación, las bases o los verificadores anteriores.
