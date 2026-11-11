# ADR-026: fundación SQL2019 y seguimiento del trabajo parcial

Fecha: 2026-10-26. Estado: aceptada para fundación técnica P1; adopción de nombres en runtime pendiente.

El propietario aportó un esquema español para cerrar P1 y pidió contar los avances parciales. El ZIP describe una exportación validada antes en SQL2025; eso no acreditaba SQL2019 ni autorizaba a sustituir tablas académicas o perfiles actuales.

Se califican sus SQL originales en SQL2019 real con TLS validado. Se crea un release nuevo y separado, 98 tablas más diario, con aprobación de hashes externa, catálogo íntegro, historial por intento, locks, reconciliación independiente y restauración nativa previa. Las copias de fallo son nuevas; las fuentes y releases anteriores se conservan. No se activan aliases, proveedores o rutas HTTP. El [informe P1](../adaptation/sql/SQL_P1_ES_REVIEW.md) fija pruebas, recuperación y límites.

La reversión ensayada restaura el baseline en un destino nuevo mientras el par anterior de aplicación/base permanece operativo. No borra el historial del release nuevo ni los datos existentes. Una futura adopción con datos y procesos académicos requiere transición y aceptación propias; no se infiere de una creación de estructura.

Se mantienen los 56 criterios canónicos y sus dependencias. El porcentaje principal pasa a ser trabajo documentado: 279 hitos binarios con pesos fijos que suman 1 por criterio; el porcentaje de fase es el promedio de las fracciones de sus criterios. Los pesos no dependen del número de pruebas, tablas, nodos o tareas fáciles añadidas. La aceptación completa conserva su ledger y una columna distinta. El criterio sólo puede completarse al aceptar todo su alcance; un 100% de fase requiere además sus dependencias.

El trabajo legado revisado puede acreditar implementación o una prueba histórica acotada. No acredita automáticamente la composición actual, paridad Scentra, proveedores o producción. Una futura subdivisión necesita preimagen/versión/motivo y reparte exclusivamente el peso previo. Dos decimales expresan el cálculo reproducible, no una precisión de esfuerzo o funciones disponibles.

Cada entrega debe actualizar roadmap, hitos/evidencia, memoria, grafos y porcentajes P0–P11. El [checker nuevo](../../backend/tools/check_p1_es_checkpoint.py) comprueba la continuidad sin SQL; los validadores históricos permanecen inmutables.
