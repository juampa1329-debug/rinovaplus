# Repositorio privado Rinova Plus

11 de noviembre de 2026. El propietario indicó continuar la publicación del CRM CBN en GitHub, cuenta juampa1329-debug, repositorio rinovaplus, rama main. Esta importación reúne el código y la documentación del proyecto de trabajo en un commit inicial. Las referencias al repositorio anterior registran la historia del proyecto. Coolify y el perfil público de P12 se gestionan según su [plan](adaptation/sql/P12_DNS_HANDOFF.md).

[Repositorio Rinova Plus](https://github.com/juampa1329-debug/rinovaplus)

# GitHub: trazabilidad y controles previstos

## Publicación vigente — integración, 2026-10-15

El propietario autorizó commit y push de toda la integración en `codex/integracion-coolify` y continuar exclusivamente desde esa rama. **Estado: publicación confirmada el 2026-10-15, America/Bogota.** El commit de integración [b92660a999b79f59c0d56e472463f02b80a33443](https://github.com/Jhon-Steven-dev/CRM_CBN/commit/b92660a999b79f59c0d56e472463f02b80a33443) contiene 176 archivos. `git push -u origin codex/integracion-coolify` creó la rama remota correctamente; una consulta independiente `git ls-remote origin refs/heads/codex/integracion-coolify` confirmó el mismo SHA que HEAD. Upstream `origin/codex/integracion-coolify`, divergencia ahead/behind 0/0 y árbol limpio comprobados después de ese push. Este SHA identifica la integración; el cierre documental de esta comprobación puede tener un commit posterior. No se autorizaron merge a `main`, eliminación de ramas, PR ni despliegue por esta instrucción.

La evidencia existente se reutiliza: 1514 pruebas backend, 196 frontend, 39 comprobaciones Docker/HTTP y aceptación de navegador local. Permanecen intactos 121/122 hashes del cierre Docker; la única diferencia es `.gitignore`, que excluye `.atl/`, un registro/caché de herramientas con rutas propias de este equipo. No cambió código ni configuración ejecutable. Esta preparación modifica documentación y esa exclusión local; no presenta las comprobaciones previas como una ejecución nueva.

## Publicación histórica — base inicial, 2026-10-14

**Estado — 2026-10-14, America/Bogota:** proyecto publicado por autorización expresa del propietario en `main` de [Jhon-Steven-dev/CRM_CBN](https://github.com/Jhon-Steven-dev/CRM_CBN). `origin` conserva la URL solicitada. El commit remoto inicial `9098d554755288ae9001efa5b7007ab4e29ef482` se conservó como padre de [c7a03e464bfea031f312b00770443862122778c5](https://github.com/Jhon-Steven-dev/CRM_CBN/commit/c7a03e464bfea031f312b00770443862122778c5), `feat: add local CRM demo and design docs`, con 129 archivos publicados. `git push -u origin main` terminó correctamente, sin force push; `git ls-remote origin refs/heads/main` confirmó el mismo hash. Seguimiento `origin/main` y árbol limpio comprobados después de ese push. Esta evidencia corresponde a ese corte, antes de actualizar estos documentos. **P-009** queda parcialmente cumplido: publicación completada; visibilidad/licencia, protecciones, Actions y secrets no fueron inspeccionados ni configurados. Publicar código no acredita despliegue, CI ni funcionamiento conectado.

## Flujo propuesto

1. Pendiente con aceptación → issue cuando exista repo; sin información personal, secretos o configuración privada.
2. Para el trabajo vigente, continuar exclusivamente desde `codex/integracion-coolify`, según la instrucción del propietario. Crear otras ramas o cambiar este flujo requiere una nueva decisión; no se aplica automáticamente el esquema anterior de ramas cortas desde `main`.
3. Commits convencionales `feat:`, `fix:`, `docs:`; paths explícitos, sin atribución IA/`Co-Authored-By`. No commits automáticos por concluir una tarea.
4. PR usa [plantilla local](../.github/PULL_REQUEST_TEMPLATE.md), enlaza issue, acceptance/evidencia y riesgos; revisión técnica/DBA/UX según superficie.
5. Merge/push/release solo por persona autorizada y política real del repo. Actualizar [avance](progress.md) y [pendientes](pending.md) con URLs verificadas.

## Protección por configurar al existir repo

- `main` sin force push/borrado ni cambios directos ordinarios; PR y revisión requerida. Definir mantenedores y excepción de emergencia auditada, no un bypass automático.
- Checks obligatorios solo con nombres de jobs reales que corrieron; configuración según capacidades del plan GitHub y evidencia de rechazo de merge fallido. No declarar enforcement por tener YAML.
- Escaneo de secretos/dependencias y mínimo privilegio de Actions; sin credenciales productivas en PRs o runners. Revisar permisos de forks y secretos de ambiente; deployments con aprobación.
- Ownership/revisores y política de revisión DBA para migraciones/core; CODEOWNERS se crea al asignar usuarios/equipos reales. Revisar licencia, dependencias y logs antes de publicar.

## CI propuesta, todavía sin workflow ejecutable

| Capa | Comprobaciones por aceptar en P-004 |
|---|---|
| Backend | Formato/lint/tipos, unitarias y contratos; integración SQL Server con datos test y pruebas transacción/idempotencia/RBAC. |
| Frontend | Formato/lint/typecheck/build, componentes y E2E sandbox; teclado/responsive/estados handoff. |
| Datos | Migraciones solo en SQL Server test; revisión de impacto/rollback. SQLite/mock no sustituyen prueba SQL Server. |
| Repositorio | Diff sin whitespace/secretos, dependencias fijadas, enlaces docs y trazabilidad issue/PR. |

No incluir comandos que aparenten funcionar sin scaffold. Tras acordar stack/lockfiles, implementar los mismos comandos verificables local y CI, registrar versiones/ambiente y probar un fallo controlado. CI green no prueba Meta real, producción, dispositivo o cumplimiento.

## Releases

Versionado, changelog, checklist, backup/recovery cuando aplique y reversión documentados; staging primero. Publicación/despliegue independientes del merge. No contratar servicios ni activar automatizaciones sin consentimiento del propietario.
