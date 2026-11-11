# Fase 4 — formulario funcional LOCAL

**2026-10-14, America/Bogota. Estado: completada al 100% del alcance LOCAL.** Código, escritorio/móvil emulado, temas y teclado comprobados; no integración ni aprobación visual humana final. Alcance autorizado por el propietario: «publícala y comienza la fase 4». La rama `feat/phase-4-local` fue publicada en `origin/feat/phase-4-local` con upstream verificado en `14d818a123118914990dc8951738ae3b8bf38bd7`, según comprobación del coordinador. Esto publica historial existente, no el código de esta fase ni Tailwind/SQL todavía sin commit. No nuevo commit, PR o despliegue.

## Qué se hizo

Formulario público `#/application`, sin shell interno, con **Completar → Revisar → Confirmar**. Se mantienen los cinco campos provisionales del skeleton: nombre ficticio, correo de ejemplo, programa/jornada del catálogo sintético y confirmación de usar datos ficticios. No se añaden identificación, documentos, menores ni requisitos legales no aprobados. Programa y jornada requieren selección explícita, sin elegir por el aspirante.

- Validación por campo: obligatorios, correo, límites 100/160 y valores dentro del catálogo demo. Errores asociados y foco en el primer inválido; al escribir no se roba el foco.
- Revisar muestra todos los valores normalizados; editar conserva datos e invalida revisión. Confirmar es una acción distinta, vuelve a validar y no puede repetirse ni saltarse la revisión.
- Confirmación temporal explícita: **no registro, API, matrícula o envío**. No inserta fichas ni mueve etapas del CRM.
- Limpiar, probar otro o cambiar escenario con datos solicitan descarte; conservar mantiene el formulario. Reset general, salir de la ruta o recargar descartan este estado; solo apariencia conserva su preferencia existente.
- Disclosure de escenarios de enlace disponible/vencido/usado/no válido, rotulados **Demo**. Los bloqueados no exponen captura; recuperación vuelve a formulario vacío. No token ni validación de identidad/vencimiento real.
- Reducer puro en `shared/application.ts`; mantiene reglas fuera de JSX. Componentes/tokens y Tailwind existentes reutilizados, sin dependencias, backend o estilos globales nuevos.

## Aceptación local

| Criterio | Estado y evidencia |
|---|---|
| Captura mínima, selecciones explícitas y errores/límites | Comprobado en pruebas de reglas/UI. |
| Revisión editable y confirmación local separada, sin doble confirmación | Comprobado en reducer/UI. |
| Escenarios bloqueados y recuperación | Comprobado en reducer/UI; solo ilustración. |
| Descarte confirmado/cancelado, reset general y remount | Comprobado en UI y navegador: recarga real, reset y salida/reentrada descartan estado; cancelación conserva datos. |
| Sin fetch ni almacenamiento de datos del formulario | Spies de prueba negativos y lectura del flujo; sin llamadas de negocio. |
| Regresiones Clientes/mini CRM/Comentarios/Asistente/apariencia | Suite completa 78 tests aprobada; navegador smoke de superficies Clientes/mini CRM/Inbox/Comentarios/Asistente, no repetición integral del pase de fase 3. |
| Desktop/móvil emulado, claro/oscuro, teclado, geometría y consola | Comprobado por coordinador en IAB escritorio/móvil emulado, claro/oscuro/teclado; sin overflow en vistas medidas y consola limpia. |
| Documentación y siguiente unidad | Actualizados; fase 4 y P-033 completados al 100% exclusivamente LOCAL; siguiente 5 local por autorización específica. |

## Evidencia de código

Node `24.20.0`, npm `11.19.0`; dependencias ya instaladas. Línea base `npm run check`: **64 tests/7 archivos**, formato/lint/tipos/build aprobados. No instalación o cambios de paquetes.

Normalización acotada antes del check final:

```powershell
Set-Location 'E:\Nuevos_Proyectos\CRM_CBN\frontend'
npm exec -- prettier --write src/features/ApplicationForm.tsx src/shared/application.ts src/shared/demo.ts src/shared/navigation.ts src/test/application.test.tsx src/test/App.test.tsx src/test/demo.test.ts
npm run check
```

Resultado final: **formato/lint/tipos, 78 tests en 8 archivos y build aprobados**. Corte nuevo: 14 pruebas; las 64 previas se mantienen con adaptación explícita del flujo de formulario y selecciones. Prueba enfocada previa: 27 tests/3 archivos aprobados. Detector Impeccable una vez, `[]`, exit 0. No revisión nativa receipt-driven: coordinador verificó modo off/default; no se fabrica aprobación.

Freeze del source normalizado: `.local/phase-4/final-source-hashes.json`, **40 archivos frontend source/config**; baseline `.local/phase-4/baseline-hashes.json` incluye cinco archivos Python. Cambiaron solo cinco archivos frontend existentes y dos nuevos; backend y manifiestos/lock/style/Tailwind/tema ajenos intactos frente a baseline. Después de las capturas se verificó igualdad **40/40 frontend y 5/5 backend**; cierre documental sin cambios de fuente ni reejecución innecesaria de checks. Hash principal `ApplicationForm.tsx`: `1F1AEA0182608BE4117AE1D2D4581EC38AEEA6A65DD9378F062C71B389FCE335`; reducer: `50175A8E8743B264FCDDEB1BBA13CA032CD065C5C3203F9DE22C04875CAF5654`. Log local ignorado: `.local/phase-4/frontend-check.txt`.

Backend no modificado; sus siete pruebas históricas no se reejecutaron. La configuración/certificado SQL local de otro trabajo y su informe del trabajo SQL se conservan, no se usan por el formulario. Build/jsdom no acreditan navegador, seguridad, DB/API, dispositivo físico o registro real.

## Evidencia de navegador y cierre

Coordinador comprobó **IAB `http://127.0.0.1:5173/#/application`**, escritorio **1440×1024** y móvil emulado **390×844**, sobre la fuente congelada; sin corrección de producto posterior.

| Flujo | Resultado observado |
|---|---|
| Público y errores | Sin sidebar interna; validar vacío muestra cinco errores y foco en `application-name`; correo inválido dirige foco a `application-email`. |
| Revisar/editar/confirmar | Selecciones explícitas y checkbox permiten revisar todos los valores normalizados. Editar invalida confirmación; corregir/revalidar/confirmar muestra aviso sin solicitud/persona/matrícula/API y elimina botón de segunda confirmación. |
| Descarte y enlaces | Probar otro conserva o descarta y vacía; Limpiar solicita descarte y conservar retiene datos. Vencido/usado/no válido ocultan captura y muestran encabezado/estado; recuperación disponible empieza vacía. Cambiar escenario desde revisión solicita descarte y deshabilita confirmar; conservar mantiene revisión, descartar bloquea y recuperación no restaura datos. |
| Reset y pérdida de estado | Cancelar reset general conserva borrador; confirmar reset o recarga real lo elimina. Salida/reentrada de ruta ejercitada; solo apariencia mantiene la preferencia existente. |
| Temas y teclado | Formulario claro, revisión móvil oscura y confirmación escritorio claros inspeccionados; Tab desde nombre llega a correo en móvil, foco visible. |
| Geometría | Contenido escritorio 1425px ≤ viewport1440; móvil 375px o390px ≤ viewport390 en vistas medidas. Sin overflow horizontal; la diferencia puede corresponder a scrollbar, no a dispositivo físico. |
| Regresión acotada | Clientes con cuatro fixtures y mini CRM; abrir Inbox con mensajes/tareas/timeline; Comentarios de tres redes y encabezados del Asistente compartido. Smoke, no repetición completa de aceptación navegador de fase 3. |
| Consola y salida | Logs consultados: errores/advertencias `[]`. Viewport emulado restablecido y formulario limpio abierto para revisión. |

Una operación de automatización intentó inicialmente el nombre adivinado **Probar enlace disponible**; el control real era **Volver al escenario disponible**. Se corrigió el locator desde la UI observada, sin cambios de source; no fue fallo funcional del producto.

### Capturas sintéticas

Tres JPEG nativos presentes e inspeccionados por el coordinador. Dimensiones de archivo comprobadas por `System.Drawing`; son capturas de página, **no resolución de teléfono físico**. No información personal real ni envío; evidencia local todavía sin commit.

| Archivo | Dimensiones del JPEG |
|---|---|
| [Confirmación escritorio](evidence/phase-4/desktop-confirmation.jpg) | 1425×1137 |
| [Revisión móvil oscura](evidence/phase-4/mobile-dark-review.jpg) | 375×1456 |
| [Formulario móvil claro](evidence/phase-4/mobile-light-form.jpg) | 375×1447 |

Readback posterior: **40/40 hashes frontend y 5/5 backend intactos**. README/roadmap/avance/P-033 e informe actualizados y enlaces relativos comprobados; no fuente normalizada alterada después del check. **Fase 4 al 100% del alcance LOCAL**, sin bloqueos locales restantes; aprobación visual humana final y aceptación conectada siguen separadas.

## Límites y reversión

Solo estado React de la vista y fixtures. Sin persistencia de negocio, auth/permisos, IA/proveedor/envío, token criptográfico, expiración/consumo atómico, rate limits, idempotencia servidor, registros/auditoría durables o matrícula/pago. Aviso legal, tratamiento de menores y campos definitivos siguen pendientes P-005; no se interpreta checkbox de demo como consentimiento. Pendiente/incertidumbre de envío reales se difieren porque no existe transporte; no se simula un envío exitoso a servidor.

Reversión acotada: restaurar desde `.local/phase-4/before` las cinco fuentes previas modificadas (`ApplicationForm.tsx`, `demo.ts`, `navigation.ts`, `App.test.tsx`, `demo.test.ts`) y retirar solo los dos archivos nuevos `application.ts`/`application.test.tsx`; revertir únicamente las adiciones documentales de esta fase. No aplicar rollback global, reset Git o archivos de Tailwind/SQL/otros trabajos. Backup ignorado preparado; no ejecutado.

## Qué prosigue

Fase 4 LOCAL cerrada. Sigue **fase 5 local — revisión académica humana con fixtures**, por autorización de alcance; revisar/observar/rechazar sin integración ni matrícula automática, conforme al roadmap. Fase 1 y contratos conectados conservan sus puertas y evidencia propia; esta fase no autoriza DB/API/producción/despliegue. Aprobación visual humana final sigue pendiente.
