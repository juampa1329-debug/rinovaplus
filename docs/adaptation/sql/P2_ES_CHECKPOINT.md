# Continuidad de P2 sobre esquema español

Estado vigente: **P2 cerrada al 100,00% en administración local SQL Server 2019**. Preview limpio en el puerto 4177, perfil final `CBN_P2ES_TRIAL_20261026_13f95607`; conservar todas las copias anteriores. Ver `SQL_P2_ES_REVIEW.md`, `p2_es_validation.json`, `../../../tasks/p2-es-progress.json` y el roadmap vigente. Los pendientes descritos debajo pertenecen al historial anterior al cierre.

Comprobación offline: `python -B backend/tools/check_p2_es_checkpoint.py --self-test`; no ejecutar preparadores ni alterar las 14 entradas del release comprometido.

## Historial de implementación antes del cierre


Estado: implementación y calificación en curso; **P2 aún no aceptada**.

Petición vigente: cerrar los cinco criterios de P2 con SQL Server 2019 real, perfil independiente, usuarios, permisos, ajustes y UI. Conservar SIIE y todas las copias y previews anteriores. El porcentaje principal cuenta hitos parciales con evidencia; el cierre es una columna distinta.

## Evidencia preservada

- 872 preimágenes públicas: `p2_es_input_baseline.json`; archivo privado `.local/p2-es/public-preimages.zip`. No sobrescribirlo.
- P1 cerrada: release SHA `5457c8da43a9c303c5b7032cff625a3d7ae112c876187c61fdb31e7a8948e2d3` y prueba `artifacts/p1-es/connected-result.json`. Su código/checkpoint debe reproducirse desde las preimágenes; no debilitar su comprobador para aceptar cambios P2.
- Candidata P2 R2 comprometida: release SHA `1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4`, 14 entradas, dos unidades. **No editar entradas ya comprometidas ni reescribir diario.** La candidata R1 anterior quedó archivada sin aplicación.
- Referencia `CBN_P2ES_REF_20261026_e8dacbac`; principal `CBN_P2ES_TRIAL_20261026_dc85a69e`. 39 tablas nuevas +99 anteriores =138. Aplicación de dos unidades y repetición NOOP aprobadas. Perfil TLS propio con las 30 tablas académicas denegadas.
- Revisiones semánticas Graphify en `artifacts/p2-es/*review.json` y fragmentos nuevos `docs/adaptation/fragments/p2-es-*.draft.json`. No sustituyen aceptación SQL/UI.
- Estado privado en `/var/lib/cbn-p2/p2-es-v1` del volumen `crm-cbn-p2-private-work`. Los perfiles y secretos nunca se imprimen ni se incorporan a artefactos públicos.

## Trabajo actual

El backend utiliza 108 mapeos cerrados, diario/WAL ligados al destino y semilla, detección de drift de esquema/datos requeridos, autoridad única de modelos y endpoints, controles SQL/rol/CSRF y sesiones revocables. La interfaz independiente conserva el estilo Glass y elimina las etiquetas de desarrollo de la navegación de producto. Tiene entrada `institution.html`, compilación `vite.institution.config.ts` y Docker propios; puerto previsto4177, backend interno8004. Las interfaces anteriores no se redirigen.

Los runners explícitos `tools.qualify_p2_spanish` y `tools.qualify_p2_migrations` ejecutan pruebas sólo en nuevas copias. No se invocan al iniciar la aplicación. Sus reportes incrementales están en el volumen privado y sólo se publicarán tras retirar secretos y verificar su alcance. El runner HTTP puede crear otra copia ante un fallo de prueba; no limpiar/restablecer datos de copias existentes.

La prueba conectada detectó un problema real al reconocer routers incluidos de FastAPI. La frontera ahora utiliza patrones fijos del catálogo OpenAPI generado localmente, sin exponer documentación y sin registrar IDs/consultas. También autoriza el permiso CRM antes de validar el DTO; el repositorio vuelve a autorizar dentro de la transacción. La selección de proveedor IA recompone sus proyecciones desde Models en la misma transacción, conservando IDs como campos de sólo lectura.

## Cierre pendiente

1. Terminar SQL/HTTP y fallos/reconciliación/concurrencia; repetir pruebas puras del backend.
2. Completar pruebas de interfaz y comprobar escritorio/móvil sobre una imagen propia, con navegación y roles reales.
3. Backup/restore **poblado**, invalidación de credenciales antiguas tras restaurar, conservación de cuentas/auditoría/cifrado y prueba de versión anterior de la aplicación compatible.
4. Reinicio/persistencia y comparación de las seis fuentes Windows y las 56 copias SQL2019 capturadas antes de P2. No ampliar retrospectivamente esa lista con copias nuevas.
5. Grafo aceptado independiente, checkpoint actual con reproducción de P1, memoria y ledger de279 hitos/56 criterios. Sólo entonces P2=100%.

No habilitar proveedores, OAuth real, envíos, workers o webhooks públicos como parte de P2. No inferir que el cierre de administración implica cierre de Canales, Inbox avanzado, IA, marketing o seguridad institucional de producción.
