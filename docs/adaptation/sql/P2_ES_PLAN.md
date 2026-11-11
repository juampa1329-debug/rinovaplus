# P2: integración institucional sobre el esquema español

## Estado vigente P2-ES — 2026-10-26

P2 está cerrada al 100,00% en administración institucional local sobre SQL Server 2019. Se integraron esquema español, perfil propio, usuarios/permisos/sesiones/MFA, ajustes tipados y UI Glass independiente. El preview limpio está en `http://127.0.0.1:4177/`, sobre `CBN_P2ES_TRIAL_20261026_13f95607`; tiene una cuenta propietaria y cero fixtures. Acceso sólo en `.local/p2-es/ACCESS.txt`, protegido por ACL del usuario y SYSTEM. Sin DDL/DML académico, cambios a SIIE ni redirección de copias anteriores.

Hay 138 tablas, 108 mapeos y 221 relaciones físicas. Release P2 comprometido SHA `1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4`: 14 entradas congeladas, dos unidades y repetición NOOP. No editar sus entradas/diario ni repetir preparadores sobre destinos poblados. Reinicio, restauración poblada de nueve cuentas, MFA/anti-replay y consumidor anterior compatible pasaron. Se conservaron 6 bases Windows y 56 copias SQL Server 2019 previas. 91 pruebas backend, 72 frontend y verificaciones SQL/navegador aprobadas. Las fuentes P1 originales se reproducen desde preimágenes; su checker no se relaja para el código P2.

Los porcentajes cuentan trabajo parcial con pesos fijos: 129 hitos done/150 pending sobre 279, y 15 criterios aceptados/56. P4.3.m5 suma configuración de Canales; P4 pasa a 38,29% sin aceptar proveedores. OAuth, números/tokens externos, webhooks públicos, campañas/envíos, Ads, agentes/memoria operativos, churn y puesta en servicio institucional mantienen sus fases pendientes. No confundir P2 local con producción institucional.

| Fase | Avance técnico con trabajo parcial | Criterios aceptados |
|---|---:|---:|
| P0 | 100,00% | 5/5 |
| P1 | 100,00% | 5/5 |
| P2 | 100,00% | 5/5 |
| P3 | 34,67% | 0/5 |
| P4 | 38,29% | 0/5 |
| P5 | 45,00% | 0/4 |
| P6 | 33,90% | 0/5 |
| P7 | 38,57% | 0/5 |
| P8 | 30,83% | 0/4 |
| P9 | 6,25% | 0/4 |
| P10 | 8,00% | 0/5 |
| P11 | 25,00% | 0/4 |

Ver `docs/adaptation/sql/SQL_P2_ES_REVIEW.md`, `docs/adaptation/sql/p2_es_validation.json`, `artifacts/p2-es/acceptance-review.json`, `docs/adaptation/phase-work-progress.json`, `graphify-out/p2-es/` y `tasks/p2-es-progress.json`. Check actual sin SQL: `python -B backend/tools/check_p2_es_checkpoint.py --self-test`; reproduce P1 en copia aislada. No ejecutar el checker P1 congelado contra archivos actuales y después cambiar sus hashes para hacerlo pasar.

Siguiente fase: P3, Inbox/mini CRM/CRM, filtros antes de paginar y churn/riesgos unificados, sobre una copia propia. Comenzar por comprobaciones offline; los scripts de calificación no son comandos de arranque ni preparadores idempotentes del producto.

## Histórico anterior a este cierre

Estado: implementación autorizada, 26 de octubre de 2026. Padre aceptado: P1-ES. No es cierre ni prueba de ejecución.

Se conserva el diseño Glass y la referencia funcional Scentra. El trabajo se realiza en restauraciones SQL Server 2019 nuevas y perfiles propios; SIIE, C5/C9/C11/C12/C13, los destinos P1 y sus releases permanecen intactos.

1. Fijar las preimágenes y comprobar P1 offline antes de editar. Restaurar su respaldo nativo en otro destino. Mantener las 98 tablas y el diario, sin importar datos académicos ni deshabilitar CHECK.
2. Declarar un mapa cerrado de nombres: las 68 tablas CRM españolas existentes, las 24 dependencias nuevas de Canales y las 15 tablas de acceso institucional. Traducir los SQL de las dependencias a nombres españoles en un release nuevo, sin editar releases previos ni crear aliases. Las 30 estructuras académicas conservan sus nombres y quedan fuera de los permisos del runtime.
3. Aplicar explícitamente unidades nuevas con historial enlazado al padre, revisión de catálogo íntegro, locks, STARTED durable y reconciliación independiente ante confirmación incierta. Ensayar restauración antes de aplicar, drift, reintento, bytes incompatibles, concurrencia y rollback sin borrar cuentas/auditoría.
4. Proveer login, perfil cifrado, ticket, claves y contexto institucional propios. El adaptador de consultas sólo traduce identificadores de SQL definido por el servidor; nunca interpola parámetros del usuario. Validar identidad efectiva, TLS, catálogo, ACL, diario, partición y privilegios de cada tabla/columna.
5. Reutilizar los servicios institucionales existentes y probar cuentas humanas, roles/acciones, sesiones SQL revocables, CSRF, confirmación reciente, TOTP/recuperación, protección del último administrador, ajustes tipados y revisiones, historial, secretos cifrados y auditoría append-only. Matriz método/ruta/acción verificada por acceso directo.
6. Integrar una entrada web propia con perfiles, seguridad, usuarios, permisos, ajustes IA/proveedores/modelos, cuentas de Canales con los campos de Scentra, webhooks, módulos y cuotas técnicas. Conservar CRM/Inbox compartidos. Sin planes, WooCommerce ni rótulos internos. Una selección guardada no implica proveedor o webhook activo; su transporte pertenece a P4.
7. Aceptar SQL, HTTP y navegador escritorio/móvil, errores/conflictos/borradores, reinicio y recuperación. Comparar al terminar catálogos y datos de las fuentes anteriores. Actualizar grafo, memoria, roadmap y porcentajes a partir de la evidencia, conservando 56 criterios/279 hitos y sus pesos.

P2 sólo llega al 100% cuando P2.1–P2.4 y su cierre tienen evidencia completa y P1 sigue aceptada. La puesta en servicio institucional, datos completos DBSIIE, escrituras académicas y proveedores no se infieren del cierre P2.
