# P11: operación local y entrega verificable

Fecha: 2026-10-28. Fuente: solicitud humana de P11 y respuesta que difiere la URL y la puesta online a una fase adicional. Destino autorizado: una nueva copia Docker SQL Server 2019 del checkpoint P10 válido. SIIE, C5/C9 y todas las copias anteriores se conservan.

## Alcance y condiciones de cierre

El sprint local debe demostrar: perfil cerrado propio sin DDL de aplicación; permisos efectivos de las rutas actuales; supervisión real del worker y de SQL; errores y cargas visibles sin confundir datos de diferentes vistas; recorrido integrado con teclado, móvil y temas; respaldo SQL y archivos autenticados; restauración aislada, pausa y reversión; manuales de operación; pruebas, grafos y memoria reproducibles. Cada recibo distinguirá pruebas puras, SQL, API, navegador y revisión estática. Un menú visible no demuestra datos cargados; liveness no demuestra disponibilidad de SQL o workers. Ningún fallo se convierte en aprobación por reintentar sin conservarlo.

No se ejecutan envíos, OAuth, gasto, entrenamiento institucional, escrituras SIIE ni despliegue público. El perfil mantiene las 185 tablas y el historial P10; los nuevos permisos administrativos reutilizan acciones existentes. No se modifica el lector de catálogo ni releases/checkers anteriores. Una restauración conserva evidencias y efectos inciertos y retira la autoridad de ejecución copiada.

## Secuencia

1. Congelar las preimágenes P10 y extraer grafo e inventario estático.
2. Definir contrato operativo y crear perfil, identidad y copia P11 separados.
3. Instrumentar supervisión y panel administrativo de lectura; resolver cargas y estados de interfaz.
4. Verificar límites de permisos, módulos, fallos, concurrencia y continuidad con SQL real.
5. Respaldar/restaurar SQL y blobs; ensayar reinicio y reversión preservando los checkpoints.
6. Ejecutar recorrido integrado, actualizar grafos/memoria y sellar evidencia con replay P10.

## Contabilidad

Se conserva la definición canónica de 56 criterios y 279 hitos, SHA256 `3ada201775c4955cb88796252ad684e257d64733598a6d4bae238529867d101a`. Punto inicial: general 90,23%; P11 25%. El avance parcial se otorga sólo con evidencia del hito correspondiente. El sprint local se informa por separado de la fase original; no se declara P11 original al 100% mientras existan puertas institucionales.

La nueva P12 agrupa ejecución online pendiente: no añade peso ni duplica crédito. Véase `SQL_P12_ONLINE_PLAN.md`. La fecha o disponibilidad de una URL no equivale a aprobación de producción.
