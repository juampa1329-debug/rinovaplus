# Biblioteca de plantillas y asesor Juan Pablo

## Alcance autorizado

El titular pide mejorar la bienvenida de los programas sin beca, presentar al
asesor con el nombre Juan Pablo, quitar las menciones al uniforme de estos
seguimientos y retirar de la biblioteca las versiones descartadas. Las campañas
continúan en borrador: enviar textos a revisión de Meta no autoriza mensajes a
prospectos ni el inicio de campañas.

Se preparan veinte versiones con presentación personal, programa, beneficio
verificado, condiciones completas cuando se menciona un importe y una pregunta
final útil. Incluyen once carreras adicionales, una bienvenida para cursos y
masterclasses, las seis ofertas de beca y doble titulación, Inglés y PRE-ICFES.
La voz se construye desde las instrucciones explícitas del titular con las
skills copywriting y brand-voice; el perfil del personaje queda privado.

Los programas sin beca incluyen trayectoria y financiación directa de CBN,
contrastadas con sus fichas actuales. Se verificaron abono mínimo, suma de
cuotas, alcance del primer semestre de 2027 y vencimientos en once fichas;
cuatro variantes nocturnas coinciden en importes. Los cursos y masterclasses no
heredan automáticamente la financiación de una carrera. Ventas y Mercadeo
incluye dos programas obligatorios y dos diplomas según su ficha; no se presenta
como beca opcional. Inglés conserva A1-A2 juntos en un semestre y precio por
confirmar. No se altera el expediente académico.

La fundación en 1995 y la calidad institucional se respaldan en fuentes de CBN:
[Rectoría](https://cbn.edu.co/saludos-del-rector/),
[La Institución](https://cbn.edu.co/institucion/) y
[renovación ICONTEC](https://cbn.edu.co/cbn-renueva-certificacion-icontec-16-anos-de-calidad/).
No se inventa un ranking actual, una garantía laboral ni reconocimiento
internacional de cada diploma. El nombre del asesor no autoriza fingir que la
automatización es una persona humana si el prospecto pregunta por ello.

## Eliminación de biblioteca

La retirada es una operación nativa recuperable desde Papelera. No borra Meta,
el historial de versiones ni los recibos de campañas. Se registra una nueva
versión con `library_removed`, siempre en pausa. El catálogo de uso y el selector
de campañas excluyen esas versiones; la papelera muestra sólo lo retirado y
restaurar conserva la pausa. Una sincronización de Meta no las resucita ni una
petición de despausar las habilita mientras sigan eliminadas de biblioteca.

La operación usa la autoridad, CSRF, transacción, revisión CAS y replay HMAC
existentes. Requiere confirmación del comando y bloquea retirar una plantilla
que aún esté referenciada por una campaña. También bloquea guardarla como nueva
selección o someterla a Meta si permanece eliminada. Sin DDL ni nuevas tablas.

El recorrido de limpieza primero vincula cada campaña con la nueva plantilla;
después retira exclusivamente los nombres descartados, conservando los informes.
El JSON de contenido, las capturas y los recibos nominales quedan en `.local`.

## Validación

170 pruebas backend seleccionadas pasan, incluidas siete de retirada, restauración,
replay, conflicto y persistencia de la eliminación al sincronizar con Meta.
25 frontend pasan, incluidas biblioteca, papelera, restauración en pausa y
exclusión del selector. Tipos, ESLint de los módulos cambiados, Ruff de módulos
nuevos y build institucional pasan. Se conservan avisos heredados de bundle y
datetime.utcnow; no se reformatean enteros los archivos históricos.

La validación viva detectó un error no cubierto por el doble inicial de auditoría:
`details` no pertenece al contrato común. La retirada se revirtió sin persistirla.
Se sustituyó por `fields`, `version` y `reason`, y se añadió una regresión que usa
la auditoría real. La ronda de correcciones pasa 57 pruebas backend, ocho de ellas
de biblioteca. Ruff de los módulos nuevos pasa; el traductor histórico conserva
sus avisos previos de formato, sin una reformateada general.

## Despliegue

Código publicado en `eb0a0ee`. El primer despliegue
`tcvmskags6piop7fs9ziuvc8` revirtió al contenedor anterior: el override HTTP de
Coolify ejecutaba wget, ausente en la imagen. El estado Degraded ya era visible
antes de iniciar ese despliegue. El Dockerfile contiene curl y su propio
HEALTHCHECK usa la misma readiness con Python.

Se corrigió exclusivamente el override a un comando de contenedor con curl,
`--fail --max-time 25`, contra `http://127.0.0.1:4178/health/ready`.
Se conservaron intervalo 45 s, timeout 30 s, tres reintentos y arranque 240 s;
no se desactivó la comprobación ni se sustituyó readiness por liveness.
Configuración guardada y comprobada tras recarga. Segundo despliegue:
`kkrcm8vcqub0yvn0jv5p5kmn`, también revirtió por readiness 503.

Un diagnóstico acotado encontró SQLSTATE 42883: `nvarchar(integer)` no existe.
La atribución de respuestas privadas contenía `CONVERT(nvarchar(36),j.CommentId)`;
el traductor sólo admitía varchar. Se amplía esa conversión a nvarchar, manteniendo
los literales Unicode y parámetros separados. La consulta real y tres variantes
quedan cubiertas. Un ensayo de los consumidores de entrada, proyección y despacho
se ejecutó con reversión obligatoria antes de commit y antes del proveedor: con
la corrección pasan los tres, sin persistencia ni red.

`737a5df` se publicó y quedó Running en `cvlj8gxr2qtvf8e1u95p0m3f`, 4m18s.
El ajuste de auditoría `fd236e7` está publicado en ambas ramas. Redespliegue
`cfmafgsm3xivbcxkzy1znt3s` finalizado en 4m17s, Running; readiness 200/ready y
rolling update completado el 23/11/2026 a las 20:31:48 UTC.

## Catálogo y campañas reales

El titular autorizó expresamente someter las veinte nuevas versiones de Juan Pablo,
incluidas beca y sin beca. Confirmación reciente completada con la contraseña ya
guardada, vaciando el campo de código autocompletado, sin extraer credenciales.
Veinte solicitudes recibidas por Meta; tras sincronizar, veinte aprobadas.
Una interrupción de la espera se concilió contra el catálogo antes de continuar;
no se repitieron las solicitudes ya recibidas.

Veinte campañas siguen en borrador y apuntan a las versiones de Juan Pablo.
Se revisa la versión actual aprobada y se guarda sin preparar destinatarios ni
activar. Cero mensajes a prospectos, cero consentimientos nuevos y cero cargos.
Los 764 contactos importados y 201 casos de revisión mantienen su estado anterior.

Se retiraron las 32 versiones descartadas, exclusivamente de WhatsApp CBN.
Quedan veinte visibles, todas aprobadas, con Juan Pablo y sin mención al uniforme.
La Papelera contiene 32, con restauración en pausa. Una nueva sincronización con
Meta conserva veinte visibles y las 32 retiradas: no las vuelve a habilitar.
No se borró el catálogo remoto ni la evidencia de campañas históricas.

Evidencia agregada sin contactos ni textos privados:
`artifacts/live/juan-pablo-template-library-20261123.json`.
Vistas previas y recibos detallados se conservan en `.local/preinscritos-import`.

Roadmap original P0-P11 conserva 100%; fases adicionales y OPS mantienen los
estados de PENDING_PHASES.md. Esta unidad no acredita conversiones ni nuevos
envíos productivos.
