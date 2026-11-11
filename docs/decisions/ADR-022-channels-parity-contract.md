# ADR-022 · Contrato de paridad Canales y SQL Server 2019

Fecha: 2026-10-25. Decisión de diseño dentro de SQL-C10, solicitada por el propietario. No autoriza DDL, runtime, credenciales o proveedores.

## Problema

El ensayo C9 sólo admite diez campos de configuración y una cuenta B011 por canal. Scentra solicita más campos y acciones para OAuth, secretos, números/PIN, TikTok y Webhooks. Deben conservarse, manteniendo CBN y SQL Server. La UI de tarjetas de Scentra se interpretó en C9 como prueba de varias integraciones WhatsApp; su DDL/upsert muestra una sola por tenant/proveedor/canal. Varias cuentas WhatsApp es ahora un requisito humano explícito para CBN.

## Decisión

Definir un contrato declarativo SQL2019/150 en esquema nuevo `crm_channels2`, sin modificar B011, foundation ni SIIE. Veinticuatro tablas propuestas, cinco unidades nuevas, correspondencias explícitas y perfiles/tickets propios en un ensayo futuro. No añadir columnas a las tablas protegidas para que un guard antiguo acepte el modelo nuevo.

La referencia de UI es un inventario versionado campo/acción: 115 contextos de campos/salidas y 83 instancias de acciones, con DTO y destino SQL/transitorio. PIN y contraseña se mantienen efímeros; tokens/secretos se cifran con owner y versión; Verify token conserva generación/exposición única. No se sustituye la interfaz completa por el subconjunto actual CBN.

Aplicaciones, integraciones y snapshots OAuth son entidades distintas. El secreto de la aplicación se pinnea; activos y credenciales provisionales quedan ligados a sesión/actor/cuenta. Webhook autentica un endpoint/aplicación y enruta por binding exacto; no recorre credenciales ni elige una integración reciente. TikTok conserva campos/modos/flags y quotas con reserva transaccional. B015 y el control/epoch de conversación preceden al transporte.

Se conservan los flujos funcionales de Scentra y se corrigen tolerancias observadas: expiración/replay OAuth sin validación, GET con escrituras/suscripción, fallback plaintext/JWT, firma opcional, selección LIMIT1 y cuota sin reserva. No se copian por ser parte de la implementación fuente. Los principales y la autenticación futura deben cumplir las invariantes existentes.

## Alternativas y límites

Ampliar Account(Channel) y reutilizar tickets C9 no representa la cardinalidad ni aísla cambios de catálogo; queda descartado. Rehacer o borrar las tablas anteriores para crear otras perdería trazabilidad y queda descartado. El esquema nuevo conserva el legado y permite una transición comprobable, con el coste explícito de mapear/copiar y recifrar credenciales en otra restauración.

El diseño no demuestra compilación, SQL2019 institucional, entrega real o paridad UI implementada. La extensión multi-WhatsApp se documenta como requisito CBN, sin afirmar que funciona así en el backend Scentra. La operación real sigue separada de schema/DTO y requiere sus puertas P2, seguridad y proveedor.

## Verificación y continuación

Contrato y negativos offline, revisión independiente por dominios, huellas de C9/Scentra y grafos/memoria. SQL-C11 propuesto implementará el release versionado y su mapeo en otra restauración, con backup/CHECKDB, diarios y reversión. No ejecutar los scripts SQL históricos de manera directa.

[Contrato](../adaptation/sql/SQL_C10_CONTRACT.md) · [Modelo](../adaptation/sql/channels-parity-contract.json) · [Campos](../adaptation/sql/SQL_C10_FIELD_MATRIX.md) · [Validación](../adaptation/sql/sql_c10_validation.json).
