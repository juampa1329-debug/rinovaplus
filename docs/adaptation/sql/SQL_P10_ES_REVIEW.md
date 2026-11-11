# P10: inteligencia y entrenamiento evaluado

Fecha: 2026-10-28. Estado: implementación operativa local; cierre de fase pendiente de las dependencias P8/P9. La aplicación acumulada sigue en **http://127.0.0.1:4178/#/intelligence**.

## Entorno y preservación

La imagen `crm-cbn-workspace:p10es-r2` usa la base nueva `CBN_P10ES_TRIAL_20261028_014cc86f`, el perfil privado `.local/p10-es/final-v2-runtime` y el volumen `crm-cbn-p10-media`. SQL Server tiene motor 15, compatibilidad 150 y TLS validado con ODBC 18. Hay **185 tablas, 330 claves foráneas, 155 mapeos CRM y 30 tablas académicas protegidas**. El paquete `cbn_learning_operations_v1` añade nueve tablas de dominio y su diario; su release congelada es `831c4a3f667aa67a94d2b2ae9465be0bbc000388b8b8d40cbd21ec6b4747c67c`.

P9 R9 queda detenido como `crm-cbn-preview-p9-preserved`, conservando imagen, base, perfil y volumen. P8 y las copias anteriores siguen intactas. La huella de negocio de P9 coincide con el respaldo fresco y las 30 tablas académicas de esa copia permanecen iguales. No se consulta ni modifica Windows SIIE ni se afirma disponer del esquema completo de DBSIIE.

## Datos y aprendizaje

Se adaptan los contratos de packs, datasets, evaluación, artefactos, inferencia y deriva de Scentra. Se distinguen reglas de CRM, memoria/ADN, modelos de lenguaje, packs/rúbricas y modelos estadísticos entrenados. La variante institucional usa **regresión logística binaria determinista**, identificada en API/UI, con JSON en SQL; no utiliza el estimador HistGradientBoosting de Scentra ni afirma equivalencia de sus resultados. No se instalan dependencias ML nuevas, no se carga pickle/joblib ni se añade una red neuronal.

Las cuatro tareas son priorización de prospectos, riesgo de abandono, oportunidad de seguimiento y anomalías operativas. Las muestras son **observaciones numéricas humanas revisadas**, vinculadas a conversación, campaña o contexto CRM de admisiones; no se reconstruyen automáticamente los valores históricos del origen. Se verifican existencia, sujeto y fecha del registro; no se leen tablas académicas para capturar muestras. La autorización tiene finalidad específica y referencia documental; el consentimiento comercial no la sustituye.

Muestras, correcciones, datasets, artefactos, predicciones y eventos conservan evidencia append-only. Una corrección añade otra muestra y deja obsoleto el dataset afectado. Se valida `FeatureAt < OutcomeAt`; el entrenamiento termina antes del corte y la validación utiliza sujetos distintos después del corte. La normalización sólo usa entrenamiento. Las muestras verifican el vínculo de grupo con su autorización y se revalidan autorizaciones antes y después del cálculo fuera del lock SQL.

La evaluación compara accuracy, precision, recall, F1, Brier y AUC contra una probabilidad constante obtenida del entrenamiento. Incluye falsos positivos/negativos por programa y etapa disponibles. Promoción exige mejora y cobertura por segmento, autoridad reciente, cuatro sujetos distintos en sombra de la revisión vigente y autorizaciones/bindings actuales. Observaciones revocadas o de una selección anterior no cuentan. La reversión conserva evidencia y permite volver a una versión aprobada aunque se hayan detenido nuevos entrenamientos; no reactiva el entrenamiento.

Las predicciones registran artefacto/hash, versión, finalidad, baseline y deriva. Son apoyo humano y no generan mensajes, inscripciones, campañas ni decisiones académicas. No hay entrenamiento global o entre instituciones.

## Datos visibles

Se conservan 11 contactos, 11 conversaciones y 26 mensajes, además de agentes, conocimiento, memoria, ADN, ajustes, canales y borradores P7/P8/P9. El seed P10 añade cuatro packs ficticios, 256 muestras numéricas y cuatro modelos evaluados, con 48 muestras de entrenamiento y 16 de validación por tarea. Los resultados son sintéticos y no acreditan eficacia institucional real. El recorrido web añade un quinto pack ficticio vacío con entrenamiento detenido y una autorización ficticia revocada; conserva el historial y no añade consentimiento comercial.

Los selectores de packs y autorizaciones y los listados tienen paginación SQL. El catálogo inicial ofrece hasta 200 contextos CRM recientes y 200 campañas; no implica mapeo académico completo ni acceso universal a registros históricos. La captura numérica es revisada por personas, no extracción automática de transcripciones.

## Verificación

Las comprobaciones tienen alcances distintos; no se suman como pruebas únicas:

- **419 pruebas backend y 351 frontend**, tipos y lint aprobados; P10 aporta 24 pruebas puras y nueve de interfaz.
- API: 16 comprobaciones del ciclo completo; extras: 15 de correcciones, procedencia, permisos y finalidad; gates: ocho de sombra, revocación, revisión vigente y reversión con entrenamiento detenido.
- SQL: 12 comprobaciones en cuatro copias propias para fallos, reconciliación, repetición, concurrencia, drift y permisos. No DDL en el arranque.
- Recuperación poblada: ocho comprobaciones; 171 tablas estables y cuatro blobs privados preservados, secretos existentes autenticados y sesiones copiadas retiradas. Los modelos y productores quedan pausados para revisión. El respaldo corresponde al fixture y precede al seed del preview; no se afirma restaurar efectos posteriores.
- Fronteras: seis comprobaciones; reproducción de los cuatro modelos y sus evaluaciones desde SQL, rechazo de un snapshot mal vinculado y rechazo de drift real después de una comprobación válida. La copia de drift queda en cuarentena y no es el preview ni la recuperación aceptada.
- Navegador: 25 comprobaciones funcionales y cinco de apariencia, móvil y teclado. La apariencia se validó por separado después de un timeout del selector inicial; no se repitieron las mutaciones del recorrido completo para acreditarla.
- Reinicio real: 12 comprobaciones web y huellas idénticas de 182 tablas, con la misma sesión y cuatro blobs privados disponibles. El campo `stable_tables` es el contador estructurado del recibo.
- La imagen en ejecución coincide con los 222 archivos Python/JSON de aplicación de la carpeta de trabajo y conserva raíz de solo lectura, usuario 10001, capacidades retiradas y perfil/CA de solo lectura.

Las revisiones semánticas son estáticas y se conservan separadas de los recibos ejecutados. El parser SQL opcional de Graphify no está instalado; el DDL se revisa semánticamente y se contrasta con el catálogo SQL ejecutado. El uso de tokens no está medido.

## Incidencias conservadas y cierre

La primera compilación detectó un nombre de constraint repetido; se corrigió antes de congelar la release y la compilación final hizo rollback. Un intento de prueba que retiraba al último propietario fue rechazado por el contrato; se restauró el fixture y se probó un usuario de consulta separado mediante API. El generador demo inicial reutilizaba una variable de grupo: el corte temporal lo rechazó, el prototipo se conservó y se creó `final-v2` desde otro restore. Se añadió una comprobación explícita de grupo/autorización; las muestras inmutables no se repararon con UPDATE. También se corrigieron expectativas de los scripts de prueba; los fallos no se presentan como aprobación.

P10.1–P10.4 tienen evidencia local de implementación y operación. **P10.close.m4 permanece pendiente:** exige el cierre de P5/P6/P8/P9; P8/P9 dependen todavía de validaciones externas de P4/P7. No hay dominio ni aplicaciones reales de proveedor. Los porcentajes usan los 56 criterios y 279 hitos originales, contando el trabajo parcial y manteniendo separada la aceptación.

Reversión: pausar predicción y nuevos entrenamientos; seleccionar un artefacto anterior aprobado conservando muestras y evaluación. Para volver a P9, conservar primero P10/base/volumen, detener P10 e iniciar únicamente el contenedor P9 retenido en 4178. Restaurar siempre en otra base/perfil/media con revisión previa; no reejecutar seeds, preparadores o calificadores sobre copias pobladas.
