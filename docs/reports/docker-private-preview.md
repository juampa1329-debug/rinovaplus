# Docker privado: integración comprobada

**Fecha:** 2026-10-14, America/Bogota. **Rama:** `codex/integracion-coolify`. Se construyó y ejecutó una imagen Linux AMD64 del conjunto integrado: **1514 pruebas backend, 196 frontend y 39 comprobaciones Docker/HTTP aprobadas**. La [guía Coolify](../deployment/coolify.md) describe operación privada, variables y puertas pendientes. El [informe de integración anterior](branch-integration.md) conserva su evidencia y respaldos sin reinterpretarlos como pruebas Docker.

## Cambios

- Imagen multietapa: React compilado, Nginx sin privilegios y Uvicorn en loopback; wrapper que propaga terminación y detiene el contenedor si falla un proceso. Compose usa init, UID/GID 10001, capacidades eliminadas, red propia y publicación exclusiva `127.0.0.1:4173`.
- `.dockerignore` excluye todo salvo entradas explícitas del build; no se copian `.local`, `.env`, DPAPI, dependencias Windows ni datos operativos. No hay claves o token compilados en el frontend.
- Nginx valida Host antes de reescribir el upstream y conserva Origin y `X-CRM-Local`. El límite de body y los timeouts admiten el contrato existente de media; las restricciones backend permanecen activas.
- `CRM_AI_STATE_DIR` controla el directorio absoluto de ajustes y ledger; volumen nombrado preserva revisiones y reservas de voz. Linux usa claves del entorno y bloquea guardado de credenciales; Windows conserva DPAPI. La UI explica esta capacidad. Piper reconoce el ejecutable de cada plataforma, sin instalar motor/modelos.
- Catálogos frontend admiten base explícita vacía para same-origin. SQL conserva base `DBSIIE`, permisos y consultas acotadas; prepara host/puerto TCP optativos con validación, credenciales emparejadas y TLS obligatorio. Sigue deshabilitado por defecto y no se abrió ninguna conexión real.

## Evidencia nueva

| Capa | Resultado |
|---|---|
| Backend | Dependencias coherentes; Ruff formato/lint y exportación canónica aprobados. Suite completa: **1514 aprobadas en 152,81 s**. |
| Frontend | Prettier, ESLint, TypeScript, **196 pruebas en 21 archivos** y build Vite aprobados. |
| Build Docker | Imagen AMD64 construida; Node 24.20.0 y Python 3.12.14 con índices base fijados por digest. ODBC Driver 18 instalado. |
| HTTP real | UI y asset JS 200, salud viva 200, readiness 503 esperado, ajustes IA 200. Cuatro catálogos devuelven 503 deshabilitado. |
| Controles reales | Host extraño/sufijo engañoso, Origin extraño/null y cabecera ausente/incorrecta rechazados; Origin local aceptado. POST sin JSON rechazado. Guardado de claves y permiso externo en Linux devuelve 503. |
| Aislamiento | UID 10001; exactamente un Uvicorn en `127.0.0.1:8002`, proxy headers desactivados, puerto host solo loopback, red y volumen propios. Proveedores y credenciales SQL ausentes. |
| Persistencia | Ajuste sintético y una reserva de cuota sin proveedor sobreviven a recreación real del contenedor. Se restauraron los ajustes deshabilitados originales; no se borró el volumen. |
| Piper | Catálogo responde no disponible por ausencia explícita de motor/modelos; no se simula síntesis Linux. |

Las 39 comprobaciones están individualizadas en `.local/docker-integration-20261014/docker-smoke.json`. Logs separados: `backend-final.log`, `frontend-final.log`, `docker-build-final.log` y `docker-smoke-final.log`. `docker-source-freeze.json` registra hashes de código/configuración comprobados. La aceptación de navegador siguiente es evidencia independiente del coordinador sobre esta misma imagen.

### Aceptación en navegador del conjunto integrado

El coordinador comprobó mediante CUA `http://127.0.0.1:4173` en una ventana normal de **1044 × 917**, tema oscuro/sistema. Overview mostró V6; la nota sintética de Clientes sobrevivió al cambio de ruta hacia Formulario y al regreso. Se restauró el texto original sin guardar. Formulario aceptó datos completamente sintéticos, revisión y confirmación local, con indicación explícita de ausencia de registro SIIE/API.

Revisión académica mostró tres elementos y el panel «Alcance conectado pendiente», con registro SIIE deshabilitado y sin ejecutar decisiones. Asistente mostró chat y controles multimedia/búsqueda; Enviar permaneció deshabilitado por IA/modelo sin configurar. Ajustes IA mostró voz/audio/visión/búsqueda; un borrador sintético de system prompt sobrevivió al cambio Canales → IA y se restauró sin guardar. Canales conservó sus controles locales/de referencia y acciones reales deshabilitadas.

APIs explicó las credenciales administradas por entorno en Linux, con edición de claves y permiso externo deshabilitados, y mostró 154 contratos. Diagnóstico mostró la operación local de fase 6. Conocimiento mostró los cuatro catálogos y «Cargar períodos» deshabilitado sin token, sin activar consultas. Se regresó a Overview, sin warnings ni errores en consola; captura local: `.local/docker-integration-20261014/browser-overview.jpg`.

Esta aceptación no modificó ajustes backend ni reinició el contenedor. No acredita móvil/tablet, pantalla completa, proveedor/DB real ni ejecución de operaciones conectadas.

Recursos creados exclusivamente para esta unidad:

| Recurso | Identificador |
|---|---|
| Proyecto Compose | `crm-cbn-integration-20261014` |
| Contenedor conservado | `crm-cbn-integration-20261014-preview-1` |
| Imagen | `crm-cbn-integration-20261014-preview:latest` |
| Digest de imagen verificado | `sha256:d3bcf18310054f152e88f269e321fb54077b2e0d694ef650fa73274fa5c0b6b0` |
| Red | `crm-cbn-integration-20261014_preview` |
| Volumen | `crm-cbn-integration-20261014_ai-state` |
| URL privada local | `http://127.0.0.1:4173` |

## Incidencias resueltas y límites

El primer test nuevo omitía el Content-Type JSON obligatorio al crear una conversación; se corrigió la petición de prueba, no la guardia. Un ajuste inmediato de formato tuvo indentación inválida y se corrigió antes del pase final. Primer arranque Docker: Nginx intentó crear temporales FastCGI bajo un directorio sin permiso; todos sus temporales se movieron a `/tmp/nginx`, propiedad del usuario sin privilegios. El wrapper hizo fallar el contenedor completo, en lugar de dejar una preview parcialmente viva. La reconstrucción y las 39 comprobaciones posteriores aprobaron.

Al cierre Docker del 2026-10-14 no hubo commit/push ni despliegue Oracle/Coolify. El propietario autorizó la publicación de la rama integrada el 2026-10-15; su preparación y posterior verificación remota se registran por separado en el [flujo Git](../github-workflow.md). Esa autorización no incluye despliegue. No se probaron SQL remoto, proveedores reales, canales, ARM64 ni teléfono físico. Los manifiestos base incluyen ARM64; eso no prueba el paquete completo en esa arquitectura.

Se conserva una sola réplica/worker; el ledger de archivos no coordina procesos. Clientes/borradores son temporales y la IA sigue siendo banco sintético. Dominio público, identidad/RBAC, red privada SQL, confianza del certificado y aceptación conectada requieren su propia autorización/evidencia de fase 1. Preparar credenciales no sustituye esos requisitos.
