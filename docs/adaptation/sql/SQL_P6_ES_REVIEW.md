# P6 — Conocimiento, memoria colectiva y ADN institucional

La aceptación local canónica se registra en `artifacts/p6-es/acceptance-review.json`; no equivale a aceptación de proveedores externos ni a paridad literal con todos los extras SaaS. La aplicación integrada conserva `http://127.0.0.1:4178/`, imagen `crm-cbn-workspace:p6es-r2`, base propia `CBN_P6ES_TRIAL_20261027_a6fc321d` y perfil privado `.local/p6-es/final-runtime`. Se conservan las mismas credenciales humanas.

## Contrato SQL Server 2019

Motor 15 y compatibilidad 150, TLS validado sin `TrustServerCertificate`. Release `cf32dcab88a1e0467c5ae58fa2863e16df13ce906d246a3df43ceb8eb311f5ff`: dos unidades explícitas y catálogo esperado, tres entradas congeladas. El resultado tiene 153 tablas, 249 relaciones físicas y 123 mapeos CRM; las 30 tablas académicas permanecen fuera de los permisos del runtime.

Se añaden `dbo.CRMConocimientoOperacionMigracion`, `dbo.CRMConocimientoRegistro` y `dbo.CRMConocimientoVersion`. El diario conserva STARTED/COMMITTED, hashes de release e historial padre, bloqueo exclusivo y reconciliación. Registro mantiene tipo, ámbito, vigencia, visibilidad y versión actual; Version es sólo SELECT/INSERT para el usuario de aplicación. No hay DDL de arranque, borrado físico de registros ni reescritura de versiones.

La copia parte de un respaldo nativo fresco de P5. Su contenedor detenido `crm-cbn-preview-p5-preserved`, imagen, base, perfil y volumen siguen disponibles; P4, C5, C9 y los demás checkpoints no se redirigen. La reversión de fase consiste en detener P6 y volver al contenedor P5 preservado, conservando antes la base, historial y volumen P6. No fusionar automáticamente datos posteriores ni reenviar efectos inciertos.

## Comportamiento

- PDF/TXT hasta 5 MB, extracción acotada, páginas originales, validación de contenido activo, rechazo de cifrados y aviso para PDF sin texto. Los fragmentos cuentan unidades UTF16 para `nvarchar`; el texto Unicode no se trunca para encajar.
- Carga y corrección crean borradores. Publicación explícita exige revisión, responsable, procedencia y vigencia. Los ámbitos de programa/etapa usan el catálogo CRM declarado y etapas aprobadas. La interfaz selecciona nombres, sin tratar esos datos como oferta SIIE verificada.
- La búsqueda SQL léxica filtra publicación, institución, revisión, ámbito, visibilidad y vigencia antes de leer cuerpos. Conserva ID de documento/fragmento, página y versión. Los IDs autorizados por cada perfil siguen restringiendo la recuperación del agente. La visibilidad «Sólo equipo editor» nunca entra al prompt.
- Memoria colectiva y ADN tienen versiones, corrección, revisión, archivo y recuperación de una versión publicada como versión nueva. El ADN separa misión, voz, principios, límites y derivación; no amplía permisos ni sustituye autoridad académica. Veinte memorias colectivas vigentes es el límite editorial del contexto compartido.
- La memoria privada requiere mensaje entrante de la misma conversación, cita literal y valor contenido en ella. Se vincula al contexto y su revisión. Otra conversación o una simulación genérica no puede usarla. Cambiar el contexto retira los hechos anteriores hasta una nueva revisión explícita; archivar un hecho anterior sigue permitido.
- El contexto efectivo incluye versiones de fuentes, memoria y ADN. Su cambio invalida resultados en curso; el replay confirmado también fija revisión y switches de módulos. No hay una segunda inferencia por reutilizar el mismo nonce. La carga base64 conserva confianza editorial cero, igual que el editor de texto.
- Reconstruir índices modifica sólo fragmentos y términos derivados desde páginas de versiones revisadas, con IDs deterministas. No cambia la versión efectiva ni reescribe historial. La restauración exige una versión previamente publicada y conserva los controles actuales de ámbito y vigencia.

## Evidencia ejecutada

Los informes públicos distinguen: 45 comprobaciones API, 14 de ejecución con gateway controlado, 13 negativas adicionales, 12 de almacenamiento/migraciones, cinco de recuperación nativa y cinco de replay/switches/confianza de carga. Las regresiones pasan 288 pruebas backend, 316 frontend, tipos y lint. Navegador y reinicio se registran aparte, sin sumarlos como pruebas unitarias.

Tres preguntas educativas sintéticas recuperaron su fuente esperada en posición 1. Es una comprobación reproducible de relevancia local, no una estimación de precisión institucional. Se conserva la búsqueda léxica porque esa muestra no justifica otra tecnología. La validación de respuesta limita referencias a IDs suministrados; no es una prueba automática de que toda afirmación esté respaldada semánticamente.

Recuperación nativa: 148 tablas estables y sus bytes conservados, sesiones copiadas retiradas y materiales del vault autenticados antes de habilitar el perfil. La preservación final comprueba 105 tablas de negocio heredadas y 30 académicas frente al respaldo P5, con cambios limitados a fuentes/índices nuevos y perfiles de ejemplo. Las tablas académicas españolas están vacías; no se consultó de nuevo SIIE Windows ni se afirmó completar los mapeos del DBSIIE real.

Se mantienen ocho contactos, ocho conversaciones, 26 mensajes, ocho notas, ocho tareas, tres comentarios y la jerarquía educativa de P5. Se añaden fuentes, memoria y ADN claramente ficticios para explorar P6. La pausa del agente de programa se conserva; no se activó su descendiente para completar la demostración. Los recorridos de navegador agregan fuentes de ejemplo y restauran el texto colectivo original con historial.

## Límites y continuidad

Cero llamadas a proveedores reales. No se activó el productor automático B011 ni se añadieron rutas de envío. P4 mantiene su pendiente externo por falta de dominio/apps reales. PDF/TXT no incluye URL remota, OCR, CSV, embeddings externos ni todos los subtipos/tags/aliases SaaS; las diferencias están contrastadas en `artifacts/p6-es/reference-final-review.json`. El volumen propio se comprobó con cero blobs ready; no se presenta como restauración probada de archivos poblados.

P5 se reproduce desde 1304 preimágenes públicas exactas de `.local/p6-es/public-preimages.zip`, con índice y SHA en `p6_es_input_baseline.json`, sin cambiar los verificadores precedentes. Los grafos anteriores permanecen congelados. Revisiones semánticas iniciales/finales y extracción AST están separadas de la evidencia SQL/UI ejecutada. Los pesos y 279 hitos del roadmap no se cambian para cerrar esta fase.
