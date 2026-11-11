# SQL-C12 · Correspondencias B011 y API independiente

Aceptada únicamente en ensayo local aislado. La copia final es `CBN_C12_TRIAL_20261025_7a309d11`; se restauró desde un respaldo nuevo COPY_ONLY/CHECKSUM de C11, con VERIFYONLY y CHECKDB. El catálogo C11 se reautenticó antes y después del respaldo bajo los locks de esquema y escritura. No se ejecutaron migraciones del esquema ni se redirigieron C5/C9.

## Resultado

- Los 23 registros de las ocho tablas B011 tienen correspondencias deterministas en `LegacyBinding`. Las fuentes permanecen intactas. Dos aplicaciones y dos integraciones se importaron como borradores desconectados, sin verificación de proveedor heredada.
- La cuenta TikTok carece de ID externo: se conserva NULL. La etapa inicial se convierte desde la etiqueta activa única de B006 a su clave, con SHA256 del documento canónico y su revisión. Los IDs mantienen ceros, mayúsculas y alcance por producto; Instagram conserva su página padre cuando corresponde.
- Los dos secretos WhatsApp se descifraron sólo tras verificar la clave original por SHA completo y cada KeyId. Se recifraron con otra clave AES256-GCM, nonce nuevo, propietario/versión AAD de C10 y fingerprint HMAC. Permanecen staged. El runtime no recibe claves ni permisos para leer ciphertext, nonce o cuerpos crudos.
- El recibo heredado se conserva cifrado con una clave distinta de la bóveda y queda `legacy_unverified/quarantined`. No se inventa una firma ni un evento normalizado. La cola antigua no tiene IdentityId/MessageId completos: su correspondencia apunta a una auditoría de cuarentena; no se crea un SendJob ficticio.
- El importador WITHOUT LOGIN sólo tiene lectura de fuentes/B006 y SELECT/INSERT en los destinos necesarios: 39 GRANT y siete DENY dbo. Importa en una transacción SERIALIZABLE con ambos locks. Dos fallos antes del COMMIT revierten todas las filas nuevas; repetir devuelve NOOP sin duplicados. El diario DDL conserva sus 17 filas: ésta es una importación DML trazada por unidad `CBN-CHMAP001`, bindings y auditoría, no una migración de esquema.
- El login SQL y perfil cifrado C12 son propios: 68 GRANT, incluidos SELECT por columna, y siete DENY dbo. El guard comprueba identidad, SID, catálogo completo, propietarios, ACL efectiva, contexto institucional y diario; permite las escrituras locales previstas sin firmar datos CRM mutables como si fueran inmutables.

## Repositorios y API

La composición nueva está en `backend/app/parity_channels/`; no se monta en C5/C9. Se probó con TestClient y SQL real en Docker. No hay un servidor nuevo escuchando ni una página en4176; ese host sólo identifica el ensayo ASGI.

Una capacidad privada local, con vencimiento, requiere loopback, Host/Origin permitidos y cabecera local antes de consultar SQL. No sustituye usuarios/roles P2. La API ofrece aplicaciones/integraciones en borrador, lecturas explícitas de identidades, mensajes, comentarios, recibos, trabajos, bindings y presencia de secretos. Todas las consultas fijan InstitutionId; IDs de recurso son explícitos y la paginación está acotada.

Los cambios de configuración usan revisión rowversion, Idempotency-Key y digest HMAC. Configuración, resultado de operación y auditoría se confirman en la misma transacción. Un reintento idéntico devuelve el resultado guardado; otra carga o una revisión obsoleta producen conflicto. Existe consulta de operación para reconciliar un resultado incierto. No se implementa ni se declara ensayada una pérdida real de red durante COMMIT.

Los campos de identidad de proveedor, el vínculo de aplicación, la etapa adoptada y los estados verificados no son editables por esta API. Se rechazan campos adicionales y errores de validación no devuelven el cuerpo de entrada. El NOOP comprueba fuentes, claves, targets deterministas y sus snapshots inmutables; sólo permite que cambien los campos locales expresamente editables de Application/Integration. Los SHA TargetRow de Account son snapshots iniciales, no una exigencia de congelar su DisplayName/ApiVersion.

## Evidencia

| Comprobación | Resultado |
|---|---|
| Nuevas pruebas offline C12 | 42 aprobadas |
| Regresiones focalizadas C5/C8/C9/C11 | 200 aprobadas;242 en conjunto |
| SQL/API real | 47 comprobaciones aprobadas |
| Fallos, drift y recuperación | 15 escenarios aprobados, más dos rollbacks de importación |
| Restauración de reversión independiente | `CBN_C12_FAULT_20261025_df5cbd53`, idéntica al respaldo C11 |
| Datos protegidos en C12 | 65 tablas anteriores con firmas binarias intactas; diario17 |
| Fuentes protegidas | SIIE, C5, C9 y C11: catálogo y datos idénticos antes/después |
| Partición física | 89 tablas:50 académicas,15 CRM anteriores y24 del contrato C10 |
| Filas anteriores | 44.180 académicas,203 foundation y23 B011; no incluyen el diario |
| Filas nuevas finales | 59, incluidas fixtures locales, bindings y contexto; no son59 capacidades |
| Estática | AST y Ruff E/F/I aprobados; cadena histórica y preimágenes comprobadas offline |

Los intentos previos y sus restauraciones se conservaron. Se corrigieron Hint demasiado largo, clasificación de cola sin ruta, un nombre académico supuesto y la distinción SQL229/230 del comprobador. No se borraron filas para repetir ni se modificaron releases anteriores. La aceptación corresponde al código y la copia finales, no a aquellos intentos.

[Resultado conectado](../../../artifacts/sql-c12/connected-result.json) · [Preservación](../../../artifacts/sql-c12/preservation.json) · [Pruebas offline](../../../artifacts/sql-c12/offline-checks.json) · [Validación](sql_c12_validation.json) · [Progreso](../../../tasks/sql-c12-progress.json).

## Progreso y límites

Se añade un contrato de medición solicitado por el propietario:44 unidades canónicas más12 cierres, con peso1 y crédito sólo al criterio completamente aceptado. P0=5/5 (100%); P1=3/5 (60%); P2–P11 todavía no tienen un criterio completo cerrado. Sus avances parciales se conservan y se muestran. Estos porcentajes miden cierres verificables, no horas ni porcentaje de funciones implementadas. No se calcula un promedio global.

El motor ensayado sigue siendo SQL2022 Express16/compat160; SQL2019 institucional queda pendiente. También quedan P2, UI completa Scentra, edición/rotación operativa de secretos, confirmación de contraseña, OAuth, verificaciones reales de números, HMAC de entrada pública, cuotas, workers, envíos, métricas B013 y aceptación integral. Las claves y perfiles sólo se preservan en almacenamiento privado; no se exportan secretos ni cuerpos a los informes.

Siguiente unidad propuesta SQL-C13: definir e integrar una composición general nueva con permisos y perfiles propios para reunir los subconjuntos aceptados y mostrar pendientes de cada sección. Mantener los campos/acciones de referencia Scentra y sus gates; no ampliar C5/C9 ni habilitar proveedores antes de P2 y sus ensayos específicos.
