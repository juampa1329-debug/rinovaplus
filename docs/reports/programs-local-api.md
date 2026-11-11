# Programas filtrados: APIs y pantalla verificadas con DBSIIE

**Fecha:** 2026-10-14, America/Bogota. **Estado:** A-025/P-037 completados exclusivamente para programas filtrados; **228 programas reales** verificados, conservando los tres catálogos anteriores. **Autorización:** «Adelante con programas filtrados por escuela y modalidad. Amplía crm_catalog_reader solo con los permisos de lectura necesarios y prueba las APIs y la pantalla con datos reales, sin modificar tablas ni datos.» El corte se limita a GET `/api/v1/catalog/programs` y su pantalla, sin tablas/datos modificados.

DTO mínimo exacto: `id`, `label` nullable, `schoolId`, `modalityId`, desde Id_Programa/NombrePrograma/Id_Escuela/Id_Modalidad. A diferencia del Program de la propuesta original más amplia, este corte excluye CodigoPrograma, Id_Jornada, fechas y Semestres; no se consultan ni conceden permisos para esos campos. Nombre NULL/vacío se conserva en el contrato y se presenta solo visualmente como `ID n · Sin nombre`; nombres presentes como `ID n · nombre`, sin modificar el dato fuente.

Filtros opcionales schoolId/modalityId: SQL int32 firmado, incluido cero y negativos; combinados mediante AND. Ausencia → NULL, valor válido inexistente → lista vacía sin consulta de existencia. Query desconocida/duplicada/no entera/inyección/fuera de rango → 422 antes de SQL; las otras tres rutas siguen rechazando estos filtros. Consulta estática CAST de parámetros nullable, seis valores ligados, orden por ID, límite+1, sin conteos/procedimientos o disponibilidad inferida. Guard exige cuatro columnas nuevas, flags 13 y scope PROGRAM sin SELECT completo; PK solo por tipo/parent aprobado.

React incorpora Programas al selector finito y filtros por ID con «Todas» como ausencia. «Cargar filtros» obtiene escuelas y modalidades secuencialmente, con páginas de 25 y máximo 1.000 opciones por fuente: desbordamiento/deriva falla, nunca trunca silenciosamente. Cargar programas es manual; filtro nuevo cancela/limpia y vuelve a offset cero; paginar conserva filtros. Opciones/clave solo en memoria; cambio de clave/recurso descarta opciones y respuestas obsoletas. Sin configuración/dependencias adicionales.

**Pruebas locales finales:** Ruff formato/check y **139 pruebas backend** aprobados; `npm run check` completo con **83 pruebas frontend**, formato/lint/tipos/build aprobados. El primer pase frontend tenía 82; la regresión de nombres duplicados añadió una. Primer pase de tests backend nuevos detectó imports retirados prematuramente por normalización antes de añadir los casos; se restablecieron y el pase final aprobó sin cambiar reglas de producto. Baseline de la unidad anterior preservado antes de editar.

**Corrección UI comprobada:** IAB con datos reales detectó nombres de programa repetidos y opciones visualmente indistinguibles pese a IDs diferentes. Una regresión reprodujo el fallo antes de corregirlo. Las opciones ahora muestran ID al principio, incluso con etiquetas largas; DTO/filtros/selección no cambian. Check frontend completo posterior: **83 pruebas** aprobadas. IAB final verificó IDs visibles y selección correcta en escritorio/móvil. Los ocho hashes backend permanecen idénticos; sus 139 pruebas y evidencia SQL/HTTP siguen vigentes, sin repetir suites o concesiones tras este ajuste.

## Permisos y aceptación real

El coordinador añadió exclusivamente cuatro permisos de columna al lector existente, mediante una concesión en transacción confirmada:

```sql
GRANT SELECT ON OBJECT::dbo.ACProgramas
    (Id_Programa, NombrePrograma, Id_Escuela, Id_Modalidad)
TO crm_catalog_reader;
```

Los cuatro permisos DTO están en 1; SELECT completo de ACProgramas en 0; CodigoPrograma/fecha/Semestres/Id_Jornada y DML/ALTER/CONTROL/EXECUTE en 0. Sin roles nuevos, identidades nuevas o rotación de contraseña. SID, nueve DENY, PUBLIC servidor/base y esquema de negocio intactos. Secreto DPAPI CurrentUser existente conservado, sin texto plano persistido; no secretos, stacks o filas completas en informes.

| Capa | Evidencia final |
|---|---|
| SQL/driver | 228 programas, 32 períodos, 12 escuelas y 2 modalidades; etiquetas fuente preservadas. TLS/certificado validados con ODBC 18, cifrado TRUE por Shared memory. Guard de 13 flags y cuatro columnas PROGRAM comprobado. |
| Guard | Catorce casos CASE en SQL Server y seis negativos de permisos: tabla completa, columnas ajenas, escritura, OTHER y EXECUTE rechazados. |
| HTTP/filtros | 31 casos HTTP y diez escenarios de filtro aprobados; listas, paginación, vacío y validación/errores. Tres GET finales adicionales 200: general 25, AND coincidente 10 y AND vacío 0. |
| Navegador | Opciones de filtro 12/2 cargadas manualmente; general páginas 25+25 y modalidad sola página 2 conserva filtro. Cambiar filtro limpia sin autoquery; escuela sola 10, Salud/Presencial 10 en última página y Salud/Virtual vacío. IDs visibles únicos distinguen nombres duplicados. |
| Acceso/recuperación | Salir y volver borra clave; clave corta deshabilita, inválida se rechaza y la correcta recupera carga. Sin fallback ficticio. |
| Móvil | 390×844 sin desbordamiento, incluso programa largo con ID visible al principio. Capturas escritorio/móvil/vacío; no acredita dispositivo físico. |
| Inmutabilidad | 42/42 hashes del freeze final intactos y 8/8 backend idénticos al freeze SQL/HTTP anterior. Solo documentación cambia en este cierre. |

La muestra real tiene **cero nombres NULL y cero vacíos**. Su preservación, validación y fallback se comprobaron mediante pruebas sintéticas, no como casos observados en los 228 programas.

Evidencias ignoradas: `.local/programs/live-qa.json`, `final-qa.json`, `final-source-freeze.json`, `runtime-qa.json` y `browser/qa.json`; capturas `browser/programs-desktop.png`, `programs-mobile.png` y `programs-empty.png`. Entrega en `http://127.0.0.1:5193/#/knowledge`, backend propio 8013; propiedad de procesos/puertos comprobada, sin reutilizar PIDs anteriores. La evidencia SQL/HTTP anterior se reutiliza porque los bytes backend coinciden; frontend final tiene sus propios checks/IAB.

## Intentos preservados y límites

El primer harness real falló al ejecutar runtime después de confirmar la ampliación de seguridad; se conservó el resultado saneado y se retomó verificando el estado propio, **sin repetir los GRANT**. En la comprobación final posterior hubo un HTTPError genérico sin status conservado en `final-qa-attempt-one.json`, mientras había actividad IAB: la causa no quedó verificada. Una única repetición terminó con los tres GET 200, sin cambios de seguridad, fuente o reinicios. No atribuir aquel error a capacidad/concurrencia sin prueba.

P-035/P-036 conservan sus cierres históricos; estado actual: cuatro catálogos verificados. Permanecen propuestas tres rutas: ofertas, jornadas y jornadas por oferta. Cada una necesita aprobación/contrato/permisos propios. IAM empresarial, fase 1 completa, datos personales, escrituras, producción y publicación siguen pendientes; no se aprueban por este cierre.

Si se autoriza revertir únicamente esta ampliación, retirar solo los cuatro permisos de columna añadidos y revalidar el corte anterior de aplicación. Conservar identidad/contraseña, nueve DENY y demás permisos existentes; no cambiar PUBLIC ni eliminar tablas/datos.
