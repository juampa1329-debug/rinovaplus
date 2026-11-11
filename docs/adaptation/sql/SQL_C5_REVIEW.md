# SQL-C5 · CRM, Inbox y mini CRM conectados a la restauración

2026-10-25, America/Bogota. **Interfaz aceptada en el preview local sobre la copia restaurada** `CBN_C3_TRIAL_20261024_ac8505b8`, conservando el contrato B000+B001+B006 de C3/C4. [ADR-017](../../decisions/ADR-017-foundation-ui-capabilities.md), [evidencia](sql_c5_validation.json), [pruebas de navegador](../../../artifacts/sql-c5/browser-checks.json).

## Comportamiento comprobado

El preview de 4173 usa ahora `local_foundation`. Conserva Azul noche · Glass, tipografía, tokens, navegación y edición existentes. El manifiesto se valida antes de montar React: fallo de carga o perfil inconsistente muestra un reintento y no dispara consultas de módulos desconocidos.

Clientes permite crear/editar contactos con etapas, etiquetas y campos B006. Inbox consulta y pagina B001, guarda mensajes locales y permite estado/prioridad humanos. Su mini CRM muestra una sola ficha editable compartida; se retiraron el bloque de lectura y el encabezado duplicados en foundation. Los controles de estado quedan desplegables debajo de la ficha. Los borradores se conservan al navegar entre ambas vistas y la confirmación queda persistida tras recargar.

Ajustes presenta el mismo catálogo CRM, sin un segundo almacén de definiciones. Se probaron una etapa, una etiqueta y un campo de ensayo nuevos, conservando los anteriores. En el navegador se comprobó también validación de ficha incompleta, foco del campo inválido, creación de contacto, texto local, cambios desde Inbox visibles en Clientes, borrador compartido, estado/prioridad, recarga, páginas 25+2 y carga de mensajes anteriores.

Las funciones no instaladas quedan deshabilitadas y sus rutas directas explican que requieren otra integración. No se montan catálogos o perfiles académicos, análisis/churn, evaluación, asignaciones/SLA, unificación/actividad avanzada, comentarios, medios, agentes, campañas o proveedores. No se presenta un resultado vacío como si esos módulos estuvieran operando. El contrato Inbox admite `operation=null` y campos avanzados ausentes; no se fabrican DTO de operación.

## Seguridad y preservación

Se reutiliza el perfil cifrado C4 con su ticket, login y ACL existentes. Se montó de sólo lectura en una ruta privada distinta del código y del frontend. `CRM_FOUNDATION_PROFILE_DIR` requiere modo foundation explícito; el cargador no toma credenciales SA/selector ni cambia el destino por variables SQL heredadas. El overlay elimina también las credenciales de proveedores del entorno del servicio.

Se mantuvieron ODBC18, `Encrypt=Yes`, `TrustServerCertificate=No`, nombre certificado validado, identidad/SID, permisos efectivos, forma e historial. El arranque no conecta para crear objetos, ni ejecuta migraciones o herramientas administrativas. El usuario SQL no obtuvo permisos nuevos. No se modificó `.env` ni el perfil del selector de inspección.

Se corrigió una protección local heredada que había dejado archivos de la clave cifrada sin una ACE efectiva para su propietario: directorios reciben herencia de propietario y los archivos permiso F explícito del propietario, sin flags de contenedor en archivos. No cambió ningún byte de credencial ni se regeneró una contraseña. La lectura se verificó también desde el montaje de sólo lectura del contenedor.

[Antes](sql_c5_before_result.json) y [después](sql_c5_after_result.json) se compararon metadatos, ACL anteriores y representaciones binarias SQL completas de las 50 tablas/44.180 filas académicas, en HORARIOSSIIE y en la restauración. Se conservan exactos el diario de 5 filas y la forma congelada de 7 tablas. La fuente original permanece sin esquemas CRM. Las firmas y el contexto de identidad quedan privados; no se publican datos ni hashes de fila/tabla.

| Tabla CRM | Antes | Después |
|---|---:|---:|
| Contact | 26 | 27 |
| Conversation | 26 | 27 |
| Message | 52 | 53 |
| Operation | 81 | 87 |
| Configuration | 1 | 1 |
| Configuration Operation | 1 | 4 |
| MigrationJournal | 5 | 5 |

Los incrementos corresponden exclusivamente al contacto/mensaje sintéticos, sus ediciones y tres cambios de catálogo realizados desde la interfaz. No se borraron semillas anteriores ni se reiniciaron identidades. En C5 no hubo DDL, migraciones, tablas académicas inventadas, cambios de permisos SQL, workers, inferencia o envíos externos.

## Pruebas y límites de la evidencia

| Verificación | Resultado |
|---|---|
| Backend focalizado: once archivos, incluyendo perfil/capacidades C5 y núcleo C4 | 280 pasan, 1 omitida por plataforma; 11 pruebas C5 nuevas |
| Frontend: siete archivos de CRM/Inbox/configuración/identidad/unificación/responsivo | 43 pasan; 11 pruebas C5 nuevas |
| Navegador real | 25 comprobaciones registradas, escritorio 1440×900 y móvil 390×844 |
| Móvil | ancho de contenido 375 y scrollWidth375; una ficha de notas, cero programa académico/medios; navegación lista/conversación/ficha y consola sin errores en pestaña nueva |
| TypeScript, ESLint de archivos modificados, Ruff de archivos nuevos/reorganizados | Aprobados |
| Build Vite | Aprobado; aviso de bundle principal mayor que500kB, sin aceptación de rendimiento adicional |
| Continuidad | Cadena C4→C5, SHA anterior, baseline y transiciones explícitas; C3/19SQL/9runners/Scentra conservados |

Se conservaron avisos de `act(...)` del fixture legacy de unificación; la corrida terminó sin errores no manejados. No se repitió la suite general fallida ni se declara verde: las 41 regresiones previas de IA y stubs de canales/webhooks siguen documentadas en C4. El `health/ready` general continúa503 porque el resto de integraciones está pendiente; `health/live` confirma el modo foundation. Este corte no certifica SQL2019: el motor local sigue siendo SQL2022 Express/compat160.

Capturas del resultado real, con datos sintéticos: [escritorio](../../../artifacts/sql-c5/inbox-desktop.png) y [móvil](../../../artifacts/sql-c5/inbox-mobile.png). La emulación temporal se restableció y la pestaña adicional se cerró; el preview quedó en la conversación de ensayo.

## Operación y siguiente unidad

Arranque local explícito con el mismo proyecto Compose conservado:

```powershell
$env:CRM_SQL_PUBLIC_CERT_FILE = (Resolve-Path -LiteralPath '.local/sql-l1/tls/sql-local-public.pem').Path
docker compose --project-name crm-cbn-integration-20261014 -f compose.yaml -f compose.local-sql.yaml -f compose.foundation.yaml up -d --no-build preview
```

El directorio privado `.local/sql-c5/runtime` contiene únicamente la pareja cifrada runtime y el ticket copiados desde C4. No incluirlos en Git ni en un build; su ausencia debe bloquear el arranque. El selector original no es un fallback del perfil de ejecución. Recargar la página después de cambiar de composición.

El helper `backend/tools/rehearse_foundation_ui.py` conecta SQL sólo por invocación explícita y produce evidencia de lectura antes/después. No crea ni limpia datos. Los comandos C4 `prepare/verify` no son apropiados sobre el CRM ya poblado y su `audit` anterior contiene aserciones de los viejos conteos26/52; no ejecutarlos para forzar este corte. El check rutinario de memoria/grafos es `python -B backend/tools/adaptation_graphs.py --check`, completamente offline.

SQL-C6 propuesto: definir el siguiente release CRM y su partición explícita respecto de las tablas académicas, revisar dependencias del siguiente paquete y su secuencia de ensayo. El guard foundation actual es deliberadamente de siete tablas; no añadir otros esquemas ni cambiar hashes C3 para evitar drift. La ampliación necesita un contrato nuevo que preserve estos checkpoints y mantenga bloqueadas las dependencias SIIE que faltan. No se inicia por inferencia de este cierre.
