# ADR-012 — Perfil SQL independiente del modo operativo

Fecha: 2026-10-24. Estado: aceptado en el alcance de implementación offline autorizado por el propietario para P1.2. No autoriza conexión, DDL ni operación institucional.

## Contexto

P1.1 encontró 19 migraciones con destino local fijo y nueve runners. La institución utiliza SQL Server 2019 existente; la aplicación funcionará en Linux/Docker y el servidor puede usar instancia predeterminada o nombrada. Los nombres reales, edición y permisos no están verificados. La aplicación conserva modos locales sin autenticación institucional aceptada.

## Decisión

Separar `CRM_SQL_ENVIRONMENT=local_copy|institutional` de `CRM_APP_MODE`. Un contrato compartido y puro valida transporte, credenciales, certificado e identidad esperada. El perfil institucional exige DNS/TCP, base, certificado, máquina, servidor, instancia explícita, login y usuario. `DEFAULT` significa exactamente instancia NULL; no es comodín. TLS y comprobación de identidad no tienen interruptor de evasión.

Validar metadatos SQL Server 2019 antes de negocio. Mantener el límite de permisos del catálogo y, en workspace, marker más forma. La selección institucional no habilita un modo productivo, workers o escrituras; todo workspace institucional falla antes de abrir transporte en P1.2. Se prepara el camino readonly sin usarlo sobre una base real.

## Consecuencias y aceptación

Una configuración incorrecta falla sin revelar secretos. Se conserva el destino local aprobado y no se deriva confianza del endpoint recién consultado. No se cambia una migración histórica ni se fuerza compatibilidad, permisos o certificados. La verificación conectada y el diseño de migraciones/imagen institucional/auth quedan para sus unidades; implementación offline y evidencia en [contrato P1.2](../adaptation/sql/P1_2_CONTRACT.md).
