# Precios recuperados, comentarios y escala del Dashboard — 26Nov2026

## Correcciones publicadas

- b9292d6/b5abe62: la recuperación usa el interés comercial actual y los nombres canónicos de sus candidatos. Cuando Inglés coincide con dos jornadas se conservan ambas; no se descarta el programa por no haber una jornada única. La consulta de borrador usa esos mismos candidatos sin inventar un mensaje del cliente ni asignarle una oferta.
- e45f412: se conservan completas las fuentes y se elimina únicamente la copia exacta de políticas centrales repetida en el prompt del operador. Precio por semestre, banco/tarjeta, exclusión de Addi/Sistecrédito, franja diurna 07–18, último semestre generalmente nocturno por prácticas y hechos revisados de prácticas se comparten con orientador y especialistas de todos los motores.
- El titular declara prácticas meritorias, más de600convenios y8de10estudiantes **aptos que realizan prácticas** que quedan trabajando. Es información institucional declarada, sin período estadístico suministrado ni garantía individual. La remuneración se comunica según la modalidad/norma aplicable, sin inventar salarios o equiparar todas las prácticas a contrato de aprendizaje. No se extrapola a Inglés/PRE.
- e45f412: acuse público automático sólo después de que el privado automático del mismo comentario/cuenta tenga aceptación durable e ID externo. Se revalidan fuente, hash del comentario, modoIA, configuración y ausencia de otra salida pública; comentario borrado/editado, Humano y envíos inciertos no se repiten. Los privados anteriores no se reproducen por instalarlo. El nuevo par automático completo requiere una entrada natural posterior para aceptación end-to-end; las pruebas aisladas no sustituyen ese recibo.
- 02af0ee: recuperación acotada del GET `workspace/inbox` ante503 `general_storage_unavailable`, dos reintentos adicionales con1s/3s y coalescencia por petición. Otras lecturas conservan su contrato;401/403 y escrituras nunca se repiten automáticamente. Error persistente permanece visible.
- be9c433: gráfica de260px de alto con pasos adaptativos1/2/5×potencia10 y mínimo200, máximo6marcas. Para2033enviados se usa500ytecho2500; no crece la altura con los mensajes. Tooltip, teclado y tabla accesible conservados.
- be9c433: envolvente del **ensayo manual institucional**80000caracteres (no tokens), tras medir36795de sistema+28798de evidencia/16fuentes que superaban60000. Ruta genérica40000, validación de capacidad del modelo, salida4000 y presupuestos efectivos conservados. No se recortaron cuotas o hechos para que cupiera.
- e97fbe6/c562e37: contrato manual explícito (answer texto≤4000, handoff booleano,≤5referencias), esquema de Claude sin restricciones de longitud/items no soportadas y validación backend estricta conservada. Diagnóstico sólo categorías/campos permitidos, sin respuesta ni claves adicionales arbitrarias. Fuente de compatibilidad: [documentación oficial de Claude](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

## Resultado operativo nativo

Se revisaron las peticiones de precios posteriores a18hBogotá mediante listado paginado y búsquedas de botones/precio/costo/valor. La bandeja cambia de orden con la actividad y no constituye un snapshot exhaustivo de todo el histórico. Se enviaron nuevas orientaciones a27conversaciones en esta ronda; se conciliaron recibos sin repetir tras esperas de la interfaz.25chats restaurados aIA; dos ya estaban enHumano y conservaron ese modo. Los recibos varían entre Enviado, Entregado y Leído; Enviado no equivale a entrega. Nombres/recibos detallados permanecen sólo en el registro local privado.

Patry recibió Turismo+PRE, Danna el plan de Cocina y las formas de pago, Estefany la corrección930000+3×340000 y requisitos, Robinson la duración vigente3semestres. Las correcciones no multiplican el precio por semestres para prometer el costo de toda la carrera. No se contactaron bajas ni se reenviaron salidas antiguas inciertas.

Se comprobaron seis privados Meta ya aceptados por proveedor y se añadieron seis acuses públicos; **los seis figuran Publicado en Meta** tras sincronizar. No se enviaron otros privados a esas personas. Un comentario del19Nov queda fuera de la ventana de siete días: conserva respuesta pública previa y no se intenta eludir esa ventana. Aceptación privada no acredita lectura/entrega.

Prueba automática nueva observada: una solicitud de plan de Inglés recibió abono440000, dos cuotas430000, total1300000, contado1250000, fechas y libro adicional260000 sujeto a ajuste2027; partes Leídas. Otro turno real de Cocina recibió ambos planes correctos y fechas; partes Leídas. Esto acredita esos turnos, no todos los especialistas/casos posibles.

## Incidencias observadas sin ocultar

El503de la búsquedaPatry fue a04:07:07UTC27Nov, dentro del cambio de contenedor cuyo rollout terminó04:07:08; el cuerpo de esa respuesta no se capturó. La coincidencia temporal no prueba su causa exacta. Tras02afla búsqueda nativa encuentraPatrysin alerta. Persisten consultas lentas del listado (~4,3–5,3sde sentencia,6–7sde transacción observadas), sin p95/carga representativa ni SLA acreditados. No se implantó una optimizaciónSQL/DDL en esta ronda.

Dos esperas al cambiar IA/Humano se conciliaron leyendo el estado actual antes de repetir. Hubo una navegación mientras el borrador dePatry seguía conservado: se verificó ausencia de nueva salida y diagnóstico sin intento, se retomó el mismo borrador desde la UI y sólo un mensaje nuevo quedó Enviado. No se usaron APIs autenticadas ni accesosDB alternativos.

El ensayo manual amplio deCocina primero falló antes del proveedor por60000caracteres. Después llamó al modelo y rechazó su contrato de salida (20648tokens entrada/554salida; no era truncamiento acreditado). El contenido no se conservó y no se puede atribuir retroactivamente a un campo concreto. Tras c562e37, el mismo caso pasó validación: respondió prácticas meritorias/remuneradas/>600convenios/8de10aptos, franja07–18 y último semestre generalmente nocturno, usando el historial para no repetir los pagos ya contestados. Borrador manual no enviado, sin escrituraCRM. Se añadió pauta para expresar el resultado como información deCBN sin narrar al aspirante su procedencia interna; la prueba detectó esa frase editorial y no se la envió al cliente. El diagnóstico seguro conserva el campo/categoría si vuelve a fallar, sin datos de respuesta.

## Pruebas y límites

Selección final conjunta: **435backend pasan/1excluida** (precios, catálogo, skills, contratos, comentarios, proveedores, colas, Humano y voz). Las selecciones anteriores se solapan y no se suman. Otra selección ampliada dio76pasan/3fallan: las tres de mapaSQLde riesgo son fallos heredados ya reproducidos/documentados en INBOX_CONTEXT_MEDIA_RECOVERY_20261125.md; después77pasan/3excluidas al incluir la nueva prueba de compatibilidad. La prueba amplia de seis programas/40000caracteres permanece fuera del scope; no se declara corregida por ampliar sólo el ensayo institucional.

30frontend focalizadas pasan (17lecturas/13dashboard), tipos, ESLint modificado, RuffE9/F y build pasan. La selección amplia frontend conserva52pasan/2fallos de fixtures previos, documentados antes de esta ronda. Bundle histórico744,72kB/219,60gzip. **No se declara suite completa verde ni cero fallos universales.**

Producción be9: backend s1f45x0wurzbrjubihorvegh rollout04:32:03UTC; frontend p8sddt3a1luq4bx9eldrip8x saludable04:28:02/rollout04:28:08. c562: backend ugnwsstovxyqtfzujzxe6sng saludable04:53:58/rollout04:54:06. El frontend actual contiene el cambio de gráfica be9; las versiones posteriores sólo añaden contratos/diagnóstico backend y documentación. La publicación final se concilia en la evidencia.

La gráfica real muestra500,1000,1500,2000,2500;260px clientHeight=scrollHeight. Vista móvil390×844: gráfico260px, sin overflow horizontal de página; viewport restablecido. Tooltip accesible muestra fecha/valor real. No se cambian métricas.

## Documentación y fases

[Datos exactos pendientes](PROGRAM_MISSING_INFORMATION_20261126.md): las24ofertas activas ya tienen precios y financiación. Faltan determinados calendarios de grupo, detalles específicos de prácticas, títulos/alcances certificados, redistribución curricular de cinco programas, uniforme, niveles superiores deInglés y aclaración15/16Dicdel abonoPRE. No confundir datos no aplicables aPRE/Inglés con faltantes técnicos.

Grafo de desarrollo actualizado en `graphify-out/live-project-20261126/`: AST de runtime+archivos de docs/tests/tools/tasks, manifiestoSHA256 y vista interactiva. No consume modelos, consulta CRM ni sustituye la memoria privada de los agentes. Referencias entre lotes pueden ser incompletas; grafos históricos congelados conservados.

P0–P11canónico100%/56criterios/279hitos, P12yP13aceptación inicial conservada; ampliaciones de esta ronda no recertifican todo el producto. P19/P21iniciales conservadas. P22técnico3/5 y comercial0/5; P23aceptados0/9; P24implementación acotada y aceptación0/6, con optimización profunda/piloto de carga pendientes. SinDDL,seeds,servicios nuevos, cambios de modelos/credenciales, síntesis de voz, activaciones de campaña o escriturasSIIE.

| Fase | Aceptación registrada (sin cambiar denominadores) |
|---|---|
| P0–P11, cada una | 100%; general canónico100%/56criterios/279hitos, alcance acordado previamente |
| P12 | 100%, puesta online inicial |
| P13 | 4/4,100% del alcance inicial; correcciones operativas no equivalen a garantía universal |
| P14 | Plan de entrenamiento/mejora pendiente; sin porcentaje nuevo |
| P15 | 7/7,100% inicial de correos/notificaciones |
| P16 | 0/5aceptados; integración académica/financiera parcial |
| P17 | TikTok diferido,0/5aceptados |
| P18 | Seguridad específica planificada,0/8aceptados; controles existentes conservados |
| P19 | 5/5,100% inicial de voces; no nueva síntesis en esta ronda |
| P20 | Llamadas planificadas,0/8aceptados |
| P21 | 4/4,100% inicial de catálogos y respaldo |
| P22 | Preparación técnica3/5(60%); aceptación comercial0/5(0%) |
| P23 | 0/9(0%)aceptados; contrato y piloto de volantePDFpendientes |
| P24 | Implementación acotada; aceptación0/6(0%), sin porcentaje artificial de implementación |

El100%canónico no es un porcentaje global de todas las ampliacionesP12–P24; éstas no añaden peso a los56criterios originales.
