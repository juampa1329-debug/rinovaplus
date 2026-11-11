# ADR-023 · Release físico de Canales en restauración independiente

Fecha: 2026-10-25. Estado: aceptado para el ensayo local SQL-C11 solicitado por el propietario.

## Decisión

Implementar el contrato C10 mediante cinco unidades nuevas e inmutables `CBN-CHP001–005`, en `crm_channels2`. Conservar las 65 tablas anteriores y los consumidores C5/C9. El esquema nuevo no se monta en ninguna aplicación existente por inferencia.

El migrador valida destino, catálogo completo y propietarios de objetos, ACL directas/efectivas, partición exacta, datos protegidos e historia. DDL mediante un usuario WITHOUT LOGIN limitado al esquema nuevo y referencias CRM exactas; el coordinador administrativo de ensayo crea únicamente Context dentro de la primera transacción. Esa separación no convierte un principal DDL en un sandbox ante código arbitrario: sólo se ejecutan unidades pinneadas, en copias revisadas.

Preservar las siete entradas previas del diario. STARTED se confirma antes del DDL de cada unidad; COMMITTED pertenece a su transacción DDL; SuccessKey impide doble éxito. La preparación previa crea sólo el esquema/principal y su ACL, con captura propia antes de aceptar un ticket. Un ACK incierto bloquea repetición hasta reconciliar catálogo, intento/unidad y evidencia externa. Las unidades y sus prefijos deben avanzar en orden.

Los 79 predicados físicos se revisaron contra el contrato; el catálogo real de CHECK se conserva y pinnea para comparación exacta, sin una normalización que altere agrupaciones. Las reglas de servidor y de proveedor pendientes se registran en `constraint-coverage.json`: crear tablas no implementa autenticación, AEAD, OAuth, cuotas concurrentes, HMAC o entrega.

## Alcance y consecuencias

Release `CBN-channels-parity-v1`, SHA `f5200dad8a3f8295bc2bbaf71ed6feecf2c847eab5e8031fc86038c94e9c2e32`. Ensayado en SQL Server 2022 Express/160 local; la aceptación institucional en SQL2019 queda pendiente. No se modifica el modelo/documentación C10 ni las releases anteriores. La referencia inicial sin sellar se conserva como antecedente; se corrigieron diferencias de estado/nombres y la cobertura de ownership antes del release definitivo.

Se inventariaron los 23 registros B011 para la siguiente transición. No se fabrican identidades ni se descifran credenciales para rellenar tablas nuevas. La UI sigue en sus previews C5/C9; integrar una página general con capacidades propias es un hito posterior.

[Informe](../adaptation/sql/SQL_C11_REVIEW.md) · [Validación](../adaptation/sql/sql_c11_validation.json) · [Estado del producto](../ADAPTATION_STATUS.md).
