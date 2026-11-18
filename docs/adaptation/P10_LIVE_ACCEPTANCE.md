# P10: aprendizaje evaluado, cierre técnico

Corte: 18 de noviembre de 2026. **P10 100%, 5/5 criterios. General 98,04%, 274/279 hitos y 54/56 criterios aceptados.** La aceptación añade P10.close/P10.close.m4 después de cerrar P5/P6/P8/P9; conserva el significado, pesos y evidencia histórica de los cuatro criterios aceptados anteriores. P11 conserva su aceptación institucional pendiente.

## Qué se probó

Se utilizó la interfaz autenticada de producción y el servicio Learning vigente, con CSRF y confirmación de identidad. Se creó exclusivamente «P10 · Validación ficticia · NO OPERATIVO · 2026-11-18», ámbito demo, objetivo priorización de prospectos. Sus 24 autorizaciones se refieren a sujetos sintéticos independientes; no son consentimientos comerciales ni autorizaciones para personas reales. Sus 24 muestras sólo contienen números ficticios y etiquetas de prueba.

El dataset congelado tiene 16 muestras anteriores y 8 posteriores al corte del 1 de septiembre de 2026 a las 05:00 UTC. Dos ejecuciones del mismo dataset produjeron artefactos con IDs diferentes e idéntico hash `f3bbefc99560c49614cdac6a72b0a882962484628780a5a3fbcb927c1020a4ef`. El modelo es la variante determinista de regresión logística `cbn_binary_logistic_gd_v1`, almacenada en JSON; no se carga código ejecutable ni se entrena Gemini.

En esta muestra separable, la exactitud fue 100% frente al 50% del baseline, AUC 1 frente a 0,5 y Brier mostrado de 0,0001 frente a 0,25. El segmento General/Nuevo tiene ocho observaciones y cero falsos positivos/negativos. Estas cifras acreditan la mecánica del ensayo, no precisión ni eficacia sobre alumnos o aspirantes reales. Las pruebas puras cubren cuatro objetivos, dos programas sintéticos, fuga temporal/de sujetos, alteración del holdout y esquemas numéricos inválidos.

El primer artefacto acumuló cuatro observaciones propias en sombra y se promovió. Un segundo candidato reproducido fue rechazado al intentar promoverlo sin sus cuatro observaciones actuales: el error explicó la causa y cómo resolverla. Tras obtenerlas se promovió el segundo y luego se revirtió al primero aprobado. Se calculó una predicción de la versión restaurada y una observación extrema produjo alerta de deriva. Ninguna inferencia tomó decisiones ni envió mensajes.

El historial conserva entrenamientos, promociones, reversión, pausa y versiones. Se detuvieron nuevos entrenamientos y se pausó la predicción; una recarga completa mantuvo el pack en versión 2, el dataset y ambos artefactos. El botón Entrenar candidato queda deshabilitado. No se borraron muestras ni se alteró un pack institucional.

## Ajuste de interfaz y validación

La confirmación nativa de promoción bloqueó el navegador del chat. El propietario indicó que había aprobado, pero la consulta en una pestaña nueva aún mostraba el candidato en sombra; no se contó como promoción exitosa. El commit `1049ad7` sustituye ese cuadro por el modal compartido de RinovaPlus, con cancelar, restauración de foco, confirmación explícita y revisión vinculada al artefacto. Se añaden modales de error con causa y siguiente paso. Los controles del servidor permanecen intactos. La cancelación y la confirmación corregidas se verificaron en producción.

Pasan 41 pruebas backend seleccionadas (24 del motor y 17 de frontera HTTP), 11 de interfaz de aprendizaje, tipos, lint de archivos modificados y build workspace. No se suman las acciones del navegador como tests únicos. Las primeras pruebas del nuevo modal necesitaron un shim de showModal en el DOM de test; después pasaron todas. El bundle mantiene su advertencia previa de tamaño. Coolify confirmó el despliegue de la interfaz corregida; el backend no cambió.

[Evidencia detallada](../../artifacts/live/p10-learning-acceptance-20261118.json) y [validación del cálculo](../../artifacts/live/p10-progress-validation-20261118.json). Se preservan las preimágenes exactas de los tres registros de progreso.

## Uso posterior y límites

Inteligencia → Crear pack → objetivo → datos institucionales autorizados o demo. Para uso institucional: documentar finalidad, revisar origen y valores numéricos, registrar resultado posterior, congelar dataset temporal, entrenar, comparar métricas/errores, evaluar en sombra y aprobar explícitamente. El consentimiento comercial no autoriza entrenamiento. No usar datos ficticios como evidencia institucional.

Editar pack permite detener nuevos entrenamientos conservando el historial; Pausar predicción detiene la inferencia. Revertir a esta versión sólo aparece para artefactos aprobados previamente. No confundir la versión seleccionada con predicción en ejecución: el estado pausado prevalece. No reactivar el pack ficticio como modelo comercial.

La prueba live cubre priorización de prospectos y General/Nuevo; los demás objetivos/segmentos tienen verificación pura, no un nuevo piloto institucional. No hay extracción automática de features históricas, entrenamiento cruzado, eficacia institucional demostrada ni red neuronal adicional. P14 conserva su planificación de mejoras. P13 conserva el piloto de programas pendiente. Esta aceptación corresponde al runtime PostgreSQL actual, sin revalidar SQL2019, SIIE ni recuperación institucional. Los veinte archivos históricos ausentes impiden afirmar un replay integral; no se reconstruyeron ni se alteraron sus checkers.
