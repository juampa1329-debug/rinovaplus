# SIIE: entorno único y piloto financiero PRE-ICFES — 27 de noviembre de 2026

El titular entregó la guía y los dos archivos Postman originales, confirmó que Test está preparado y eligió probar desde RinovaPlus. El paquete se conserva en `docs/contracts/siie/20261127/`, con hashes y sin claves. Se revisaron 39 operaciones y 40 scripts: las peticiones usan la variable base y los scripts no ejecutan peticiones adicionales. No se instaló ni ejecutó Postman.

## Entorno y credenciales

Todos los clientes de RinovaPlus usan exclusivamente `SIIE_BASE_URL`, con barra final. Test: `https://siieplus.online/SIIEWebPlustest/`; producción futura: `https://siieplus.online/SIIEWEBPLUS/`. Se conserva `SIIE_API_TOKEN` y la compatibilidad con la credencial original existente; no se conserva un segundo selector de URL. `SIIE_API_BASE_URL` y `SIIE_CATALOG_API_URL` dejan de elegir destinos. HTTPS y hosts aprobados siguen vigentes; no se envían credenciales a redirecciones.

Catálogos guardados, revisiones, cursores de la página, borradores e intenciones financieras llevan URL y huella del entorno. La página fija su primer entorno y exige recarga si el servidor cambia; los trabajos antiguos se pueden consultar, pero no reenviar o actualizar usando IDs del entorno nuevo. Las fuentes locales se separan por entorno y se coteja su huella completa. Los registros históricos sin entorno no se asignan automáticamente a Test o producción. Las fichas académicas aprobadas no se reemplazan al cambiar la variable.

El receptor `https://app.rinovaplus.com/hooks/siie/v1` y su firma sobre bytes originales permanecen independientes de esa URL. El contrato entrante actual no declara entorno: no se le atribuye uno sólo porque la salida esté configurada para Test. Para preparar trabajo financiero hacen falta el evento registrado, el vínculo revisado con CRM y la corroboración remota de los cuatro IDs y del documento; SIIE valida después el evento y el remitente auténtico. La recepción no equivale a vínculo aceptado, plan, pago o matrícula.

## Panel de pruebas

Admisiones → SIIE → Inscripción y webhook incorpora «PRE-ICFES · Plan y volante». Permite corroborar una inscripción recibida, crear el vínculo con el remitente WhatsApp real, consultar planes, revisar su calendario, registrar una elección expresa, asignar el plan, generar una cuota, descargar el PDF validado y consultar el estado de pago. Los trabajos se conservan cifrados y se pueden volver a abrir por ID o desde el listado guardado.

El vínculo usa la identidad del canal y una entrada real del hilo; no usa sólo el teléfono editable de CRM ni una casilla del navegador como prueba de identidad. La asignación exige un mensaje entrante de esa misma identidad/conversación y la revisión del operador de su elección; no se elige la primera opción ni se infiere consentimiento. Importes, fechas, cotización, asignación y cuota proceden de SIIE, sin recalcular precios o crear identificadores.

Cada POST tiene una intención cifrada duradera anterior a la llamada. Ante timeout o éxito de contrato inválido queda incierto, sin reenvío automático; la conciliación consulta el requestId original en `ConsultaOperacion.aspx`. Se puede renovar un vínculo vencido conservando la operación pendiente. Los fallos de permisos posteriores a la llamada conservan el recibo sin mostrar datos a una sesión ya revocada. Las llamadas de red se hacen fuera del bloqueo de escritura SQL.

La descarga es autenticada: se verifican MIME, tamaño máximo 1 MiB, longitud, inicio PDF, SHA-256 y versión frente al descriptor de SIIE; no se entrega un enlace público con token. Generar o descargar un volante no confirma un pago. La pasarela no se incorpora ni se activa. El panel no envía el PDF automáticamente a WhatsApp; ese envío requiere comprobar el caso real y utilizar el canal autorizado.

## Contrato implementado y límites

Se añaden las ocho rutas de la familia PreIcfes: Inscripcion, Conversacion, Plan GET/POST, Volante, ConsultaOperacion, VolantePdf y PagoEstado. Las operaciones existentes de registro y catálogos comparten el mismo entorno. Conservar las 39 operaciones originales en Postman no acredita que las 39 estén implementadas o hayan sido ensayadas en RinovaPlus; las rutas de pasarela siguen fuera del piloto.

Validación local: 224 pruebas backend focalizadas, 27 frontend, TypeScript, ESLint de archivos modificados, Ruff E9/F y compilación pasan. Las pruebas sintéticas cubren el flujo completo, PDF adulterado, escritura desactivada, falta de elección, configuración financiera incompleta, timeout sin segundo POST, conciliación, renovación vencida, permisos revocados y cambio Test→Producción sin tráfico al nuevo destino. Tras integrar el contribuidor, 39 comprobaciones solapadas de finanzas y cierre de seguimientos pasan. No son una suite completa verde ni una aceptación conjunta con SIIE.

Publicación inicial: implementación `2845605`, integrada con los cambios remotos hasta `e8b9085` en `21d91bb`, push a `deploy/coolify-rinovaplus`; main no modificado. Runtime `SIIE_BASE_URL` Test guardado desde Coolify, sin cambiar secretos. Ver la evidencia agregada para los recibos finales de despliegue y consultas reales.

## Aceptación real pendiente

El formulario público de SIIE Test abrió, pero su carga inicial mostró «No pudimos completar el registro» antes de introducir datos; se hizo un reintento de lectura. No se atribuye aún una causa sin la consulta del backend. No se creó una inscripción nueva ni se usó el teléfono real del titular durante ese corte.

El ensayo completo requiere una inscripción ficticia recibida realmente por webhook, vínculo revisado con el chat de prueba, elección real recibida por WhatsApp y planes/configuración válidos de Test. El titular autorizó usar el teléfono terminado en 44 sólo para el ensayo Test. Aún no se transmitió porque el formulario público no terminó de cargar. Se mantienen las escrituras desactivadas hasta la operación puntual revisada, sin pagos, matrícula académica, cambios de fichas, DDL, seeds, servicios o modelos nuevos. P23 conserva 0/9 aceptaciones hasta completar sus criterios; P13/P19/P21 iniciales, P22 técnico 3/5 y comercial 0/5, P24 0/6 sin cambios.

## Comprobación nativa final

El backend inicial `21d91bb` terminó en Coolify (`mhdffdtdmohxiutdc99vsldc`, Finished, 4m37). El panel mostró la base Test, firma configurada, recepción habilitada y envíos finales desactivados. La consulta real de períodos devolvió «2027-A · Ofrecido» (referencia `72ea8fc87b934d589f80e27d900c307b`); programas/jornadas respondió (referencia `2e46cf7b88c14e9bb9016c6adba93613`). La selección de programas de inscripción devolvió 22 entradas para el contexto ofrecido consultado, sin PRE-ICFES en esa lista. Eso no acredita ausencia del programa en todos los períodos de Test.

Se abrió un borrador anterior y se comprobó la advertencia de otro entorno, campos y envío desactivados, sin consultar sus catálogos en el entorno nuevo. Un indicador histórico engañoso del período se corrigió para no atribuir al servidor una negativa que no se consultó. La referencia del mismo evento/chat se normaliza antes de identificar el trabajo financiero, sin duplicarlo por mayúsculas de UUID.

El titular autorizó usar su teléfono terminado en 44 en SIIE Test. No se transmitió: el formulario público siguió fallando antes de mostrar campos, tanto al abrirlo como tras un único reintento de lectura. La navegación directa al archivo JavaScript de ese formulario fue bloqueada por el navegador; no se eludió ni se atribuyó a ese bloqueo la causa de la carga inicial. No se capturó el cuerpo HTTP del fallo público, por lo que su causa exacta requiere revisión en SIIE. No se creó una inscripción nueva, no se fabricó un evento ni se vinculó un recibo de otra persona.

Para el equipo SIIE: revisar la carga de `https://siieplus.online/SIIEWebPlustest/PreIcfes/Inscripcion.html`, confirmar el período/ofertas/grupos PRE-ICFES de Test y su configuración financiera, y volver a enviar un evento real de esa inscripción de prueba con firma y timestamp actuales. El secreto actual se conserva. Cuando el formulario funcione, se podrá completar el caso ficticio autorizado y obtener la elección expresa por WhatsApp para asignación y PDF. No se necesita otra clave ni una recarga de OpenRouter para estos pasos.

El ajuste final de runtime es `5a9eec1`; backend `2rakd1nvc73ineoqwo3y6oai` terminó en 4m35. Frontend `wmh8acmacwdqjvo2xmrtqkus` Finished. La compilación institucional local específica de Coolify pasa: bundle1229,61kB/355,81gzip, aviso histórico de tamaño conservado; Node22local difiere del rango24 del proyecto. Los documentos y el grafo se publican en un commit posterior al runtime. No se afirma aceptación P23 ni emisión/descarga/envío real de un volante.

Implementación: `backend/app/institutional/siie_environment.py`, `backend/app/institutional/siie_preicfes.py`, `backend/app/institutional/siie_preicfes_client.py`, `backend/app/institutional/siie_registration.py`, `backend/app/institutional/siie_api.py`, `backend/app/institutional/siie_local.py`, `frontend/src/institution/SiiePreicfes.tsx` y `frontend/src/shared/siieEnvironment.ts`. El grafo actual integra esas rutas y este corte documental, sin datos CRM, secretos, inferencias comerciales ni cambios de modelos.
