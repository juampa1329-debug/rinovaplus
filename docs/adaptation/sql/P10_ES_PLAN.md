# P10: inteligencia y entrenamiento institucional

Unidad autorizada por el propietario el 2026-10-28. Entradas: checkpoint P9 congelado, contratos de `training`, `ml_service` e `intelligence` de Scentra y criterios P10 originales. El ZIP privado conserva 1660 preimágenes públicas; las copias anteriores no se migran.

1. Revisar fuente/grafos y fijar contrato de datos, permisos, finalidad, métricas y reversión.
2. Añadir paquete SQL2019 propio, diario y perfil sobre respaldo nativo nuevo de P9. Compilar con rollback antes de congelar el paquete y ensayar fallos, repetición y drift. No DDL de arranque ni acceso académico.
3. Integrar packs/versiones, autorizaciones por finalidad, muestras revisadas/correcciones, datasets temporales, artefactos, evaluación por segmento, inferencia sombra, deriva, promoción humana y reversión.
4. Integrar Inteligencia en el preview acumulado 4178, conservar P9 y probar API/roles/CSRF, SQL, restauración, navegador, persistencia y reproducción.
5. Actualizar grafo incremental, memoria y ledger con pesos fijos; verificar preimágenes P9 y etapas anteriores. El cierre P10.close.m4 conserva su dependencia de P8/P9; no sustituir aceptación externa pendiente con datos ficticios.

## Contrato

Diez tablas propias: diario, pack, versión de pack, autorización por finalidad, muestra, dataset, artefacto, despliegue, predicción y evento. UUID y claves compuestas por institución/pack impiden referencias cruzadas. Muestras/datasets/artefactos/predicciones/eventos son append-only; permisos runtime no permiten modificar el diario ni tablas académicas. Revisiones de pack y selección de versión son CAS e idempotentes. La autorización de entrenamiento se registra por finalidad y sujeto; no se infiere del consentimiento comercial. Revocación invalida usos posteriores de datasets/modelos afectados sin borrar la evidencia.

Las cuatro tareas de Scentra son lead_scoring, churn_prediction, smart_remarketing y operational_anomaly. Las observaciones numéricas revisadas conservan procedencia conversation/campaign/admissions; admisiones usa contexto CRM, nunca consulta o modifica core SIIE. No almacenar transcripciones, nombres, teléfonos o correos en muestras ni etiquetas. FeatureAt < OutcomeAt y entrenamiento anterior al holdout con sujetos separados; features y normalización sólo de entrenamiento. No autolabel por heurística ni mezcla global de instituciones.

Scentra utiliza estimadores opcionales sklearn/lightgbm/xgboost y serialización joblib. El runtime institucional existente no contiene esas dependencias. Se adapta el contrato entrenable con regresión logística binaria determinista y JSON estricto en SQL, sin dependencias nuevas ni deserialización ejecutable. Es un modelo entrenado por optimización de pérdida; no una red neuronal adicional. Se distinguen reglas CRM, memoria/ADN, LLM, packs/rúbrica y modelo entrenado. La adaptación no afirma igualdad del estimador o de los resultados de Scentra.

Baseline constante aprendido sólo del entrenamiento; métricas accuracy, precision, recall, F1, Brier y AUC, errores por programa/etapa y cobertura. Promoción exige revisión, evaluación reproducible, mejora frente al baseline, segmentos suficientes, autorizaciones vigentes y observaciones sombra. Datos sintéticos sólo se promueven en el espacio demo, claramente identificado; no acreditan mejora institucional real ni activan mensajes/campañas/admisiones.

Reversión: seleccionar artefacto aprobado anterior con CAS, conservar datasets/evaluaciones y detener nuevos entrenamientos mediante configuración de pack. Restaurar únicamente en otra copia con perfil nuevo y selección de modelos pausada para revisión. Respaldo SQL incluye JSON de modelos; blobs P8 necesitan copia privada verificada aparte.
