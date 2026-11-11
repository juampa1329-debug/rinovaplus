# ADR-027: entrenamiento institucional reproducible en SQL Server

Fecha: 2026-10-28. Estado: aceptado para el alcance P10 solicitado por el propietario; puesta en servicio institucional pendiente de P11.

Se conserva la separación de Scentra entre packs/evaluación y servicio ML. En la copia educativa se usan finalidad explícita, snapshots numéricos revisados, separación temporal y por sujeto, artefactos JSON de regresión logística y selección humana versionada. No se instalan dependencias ML nuevas, no se carga pickle/joblib externo ni se habilita entrenamiento global o mensajes automáticos. La regresión logística se entrena por optimización determinista y se identifica como tal en API/UI; reglas, memoria y LLM conservan su identificación propia.

El paquete aditivo y el perfil P10 sólo operan en copias SQL2019 nuevas. P9 y sus pruebas/releases/grafos permanecen reproducibles desde preimágenes exactas. Evidencia ficticia se identifica y queda aislada de promoción institucional. Métricas demo demuestran reproducibilidad del motor, no eficacia académica real. Los pesos del roadmap no cambian; P10.close.m4 exige cierre previo de P8/P9.
