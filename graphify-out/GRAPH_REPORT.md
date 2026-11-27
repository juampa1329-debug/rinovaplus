# Grafo de continuidad de RinovaPlus

Vista específica de continuidad compilada el 27 de noviembre de 2026. Conserva los cortes históricos 24–26 y las fechas propias de nuevas fuentes; el AST refleja el checkout al construir. No equivale por sí sola a una lectura productiva en vivo ni a un inventario completo del repositorio o sus conversaciones.

Esta vista específica complementa el grafo general histórico en `graphify-out/live-project-20261126/`; no lo sustituye ni lo modifica.

## Alcance y procedencia

48 fuentes documentales/JSON agregados con lectura completa hasta EOF y SHA-256, más 33 archivos de código por AST. La vista dirigida contiene 802 nodos y 1360 aristas en 44 comunidades. No incluye fichas nominales, teléfonos ni conversaciones privadas. El número de nodos no mide implementación ni aceptación.

Candidatos fechados presentes pero fuera de la selección semántica: []. Su aparición se informa; no se finge haberlos extraído.

## Integridad y límites

La extracción AST aporta 424 nodos y 1293 aristas. Se excluyen de la vista 388 aristas con extremo ausente. Sus afirmaciones originales se conservan en raw-extraction.json y sus detalles en integrity.json. Son referencias/importaciones fuera del ámbito o destinos no resueltos; no se han inventado nodos para completarlas.

También se excluyen explícitamente 1 autobucle(s) emitido(s) por el AST. Los originales permanecen en integrity.json y raw-extraction.json: un autobucle del extractor no acredita por sí mismo recursión funcional. Esta separación hace visible lo que Graphify descartaría internamente al construir la vista.

Hay 1 par(es) dirigido(s) con varias afirmaciones (1 arista(s) compactada(s)). Una identidad AST puede agrupar referencias de distintas líneas: no equivale a dos implementaciones distintas en este grafo. parallel_assertions preserva las procedencias en graph.json; el original completo permanece en raw-extraction.json.

Pares compactados y ubicaciones: [{"source": "backend_app_institutional_commercial_followup", "target": "backend_app_institutional_commercial_followup_apply", "locations": [{"source_file": "backend/app/institutional/commercial_followup.py", "source_location": "L525"}, {"source_file": "backend/app/institutional/commercial_followup.py", "source_location": "L552"}]}].

Enlaces documento→código: 19, exclusivamente por rutas literales presentes en las fuentes. Dirección conservada mediante DiGraph. Graphify agrupa comunidades sobre una proyección no dirigida internamente; esto no cambia la dirección de las aristas exportadas.

## Seguimientos: lectura correcta

El avance comercial, la etapa CRM, el consentimiento y los recibos de entrega son conceptos distintos. Los cortes documentan formulario enviado, interés confirmado y casos por aclarar; una respuesta no equivale a matrícula. Los avances excluyen la reactivación general y orientan el próximo seguimiento. Los borradores de flujos no prueban activación ni aprobación de Meta. Consultar las fuentes y fechas de cada nodo antes de usarlo para actuar.

P23 conserva 0/9 aceptaciones: la recepción real SIIE no equivale al evento sintético, a vínculo de identidad aceptado ni a PDF/pagos finalizados. P24 sigue como diagnóstico: 0% de implementación y 0/6 aceptaciones. Las propuestas de rendimiento no se presentan como cambios publicados. Los errores y cortes históricos permanecen diferenciados del estado actual.

## Comunidades y cohesión

La cohesión es el resultado numérico de Graphify, sin umbral de aprobación.

| Comunidad | Nodos | Cohesión |
|---|---:|---:|
| workspace.py | 70 | 0.058385093167701865 |
| Gestión de campañas | 69 | 0.10912190963341858 |
| Seguimiento por tiempo y lista | 47 | 0.06382978723404255 |
| Espacio institucional | 46 | 0.07729468599033816 |
| Auditoría integral de fichas y | 38 | 0.05689900426742532 |
| Seguimiento comercial | 37 | 0.1066066066066066 |
| Avance comercial y exclusiones | 32 | 0.08064516129032258 |
| Precios recuperados, comentarios y escala | 32 | 0.06451612903225806 |
| Eventos y recibos entrantes | 30 | 0.12873563218390804 |
| Formularios, orientación de pago y | 25 | 0.11333333333333333 |
| Panel de campañas y seguimiento | 25 | 0.10333333333333333 |
| Panel de mensajería masiva | 22 | 0.09090909090909091 |
| Becas opcionales y valor de | 21 | 0.1380952380952381 |
| program commercial.py | 21 | 0.14285714285714285 |
| Guardado concurrente y baja expresa | 21 | 0.12857142857142856 |
| Importación de prospectos | 20 | 0.1368421052631579 |
| broadcast dispatch.py | 19 | 0.14035087719298245 |
| admissions prompt.py | 19 | 0.14619883040935672 |
| Tres seguimientos por avance activados | 18 | 0.1568627450980392 |
| Seguimiento y preferencias | 16 | 0.16666666666666666 |
| Memoria comercial | 16 | 0.26666666666666666 |
| Contrato y límites SIIE | 16 | 0.14166666666666666 |
| Importación del lote 2026 | 12 | 0.16666666666666666 |
| Políticas de campañas | 11 | 0.2727272727272727 |
| Motores por etapa | 10 | 0.2222222222222222 |
| Campaña PRE-ICFES y destinos | 9 | 0.2222222222222222 |
| Piloto y recepción SIIE | 9 | 0.2222222222222222 |
| Diagnóstico de listas | 9 | 0.2222222222222222 |
| Informe y consultas agregadas | 8 | 0.25 |
| Horarios y costes | 8 | 0.25 |
| Panel de mensajería masiva | 7 | 0.2857142857142857 |
| Respuesta y entrada al Inbox | 6 | 0.3333333333333333 |
| Ediciones y remitentes | 6 | 0.3333333333333333 |
| Prospectos y promoción PRE-ICFES | 6 | 0.3333333333333333 |
| Campañas por programa | 6 | 0.3333333333333333 |
| Espera interna y continuidad | 5 | 0.5 |
| Recuperación de respuestas | 5 | 0.4 |
| Política de abono inicial | 4 | 0.5 |
| Contención de almacenamiento | 4 | 0.5 |
| Intereses en clases abiertas | 4 | 0.5 |
| Preparación del receptor SIIE | 4 | 0.6666666666666666 |
| BroadcastProspectSetup.tsx | 4 | 0.5 |
| Métricas de campañas | 3 | 0.6666666666666666 |
| Promoción y bandeja entrante | 2 | 1.0 |

## Nodos centrales

```json
[
  {
    "id": "docs_adaptation_followup_sequence_policy_20261127_document",
    "label": "Seguimiento por tiempo y lista No contactar —27Nov2026",
    "degree": 29
  },
  {
    "id": "backend_app_institutional_workspace_rows",
    "label": "rows()",
    "degree": 28
  },
  {
    "id": "backend_app_institutional_workspace_workspace",
    "label": "Workspace",
    "degree": 23
  },
  {
    "id": "backend_app_institutional_campaigns_campaigns",
    "label": "Campaigns",
    "degree": 19
  },
  {
    "id": "crm_contact_save_20261127_report_document",
    "label": "Guardado concurrente y baja expresa —27Nov2026",
    "degree": 19
  }
]
```

## Conexiones entre comunidades

```json
[
  {
    "source": "CRM FOLLOWUPS 20261124",
    "target": "crm-followups-20261124",
    "source_files": [
      "docs/adaptation/CRM_FOLLOWUPS_20261124.md",
      "artifacts/live/crm-followups-20261124.json"
    ],
    "confidence": "INFERRED",
    "relation": "conceptually_related_to",
    "why": "inferred connection - not explicitly stated in source; crosses file types (doc ↔ code); connects across different repos/directories"
  },
  {
    "source": "Tres seguimientos por avance activados —27Nov2026",
    "target": "Evidencia agregada de activación de tres seguimientos —27Nov2026",
    "source_files": [
      "docs/adaptation/ADVANCED_FOLLOWUP_ACTIVATION_20261127.md",
      "artifacts/live/advanced-followup-activation-20261127.json"
    ],
    "confidence": "INFERRED",
    "relation": "conceptually_related_to",
    "why": "inferred connection - not explicitly stated in source; crosses file types (doc ↔ code); connects across different repos/directories"
  },
  {
    "source": "Formularios, orientación de pago y cierre a siete días —27Nov2026",
    "target": "Evidencia agregada de formularios, pago y cierre de siete días",
    "source_files": [
      "docs/adaptation/FORM_PAYMENT_CLOSURE_FOLLOWUP_20261127.md",
      "artifacts/live/form-payment-closure-followup-20261127.json"
    ],
    "confidence": "INFERRED",
    "relation": "conceptually_related_to",
    "why": "inferred connection - not explicitly stated in source; crosses file types (doc ↔ code); connects across different repos/directories"
  },
  {
    "source": "Cierre vigente de siete días sustituye duración final anterior",
    "target": "Cierre a siete días conserva los pasos de ocho, treinta y seis y sesenta horas",
    "source_files": [
      "artifacts/live/form-payment-closure-followup-20261127.json",
      "docs/adaptation/FORM_PAYMENT_CLOSURE_FOLLOWUP_20261127.md"
    ],
    "confidence": "EXTRACTED",
    "relation": "references",
    "why": "crosses file types (code ↔ doc); connects across different repos/directories; bridges separate communities"
  },
  {
    "source": "Becas opcionales y valor de la formación en mensajería —27Nov2026",
    "target": "Evidencia agregada de valor de programas y borradores —27Nov2026",
    "source_files": [
      "docs/adaptation/PROGRAM_VALUE_MESSAGING_20261127.md",
      "artifacts/live/program-value-messaging-20261127.json"
    ],
    "confidence": "INFERRED",
    "relation": "conceptually_related_to",
    "why": "inferred connection - not explicitly stated in source; crosses file types (doc ↔ code); connects across different repos/directories"
  }
]
```

## Consultas sugeridas

Usar etiquetas presentes en graph.json; la búsqueda por términos no presentes puede omitir conceptos. El recorrido demuestra acceso al grafo, no ejecución de seguimiento ni estado productivo.

- `python backend/tools/conversation_continuity_graph.py query`
- `graphify query "P23 aceptación webhook recepción" --budget 1200`

## Reproducir y comprobar vigencia

Ejecutar con el intérprete local que tenga instalado graphifyy:

```text
python backend/tools/conversation_continuity_graph.py build
python backend/tools/conversation_continuity_graph.py check
```

`build` usa únicamente AST local y fragmentos revisados; no llama modelos, SQL, HTTP, RinovaPlus ni Meta. Exporta JSON antes del HTML y del informe; respeta el bloqueo de reducción de Graphify y no usa force. `check` compara SHA-256 de fuentes, fragmentos, constructor y grafo; también detecta documentos nuevos del ámbito fechado 24–27 de noviembre. Devuelve código 2 ante cambios, faltantes o nuevas fuentes aún no incluidas.

Cada construcción también regenera `query-followup.json` y `query-followup.txt` mediante una consulta real de Graphify, limitada a conceptos semánticos del informe de seguimiento y su evidencia final, profundidad1 y hasta8.000 tokens estimados. Usa sólo términos de etiquetas, conserva la dirección y excluye anclas documentales y módulos AST para acotar el vecindario. Exige que todos los nodos encontrados se impriman, sin truncamiento. El JSON guarda contadores, ámbito, comando reproducible y SHA-256 del grafo. No ejecuta acciones en RinovaPlus.

Para ampliar el ámbito, leer íntegramente el documento nuevo y añadir un fragmento `docs/adaptation/fragments/continuity-20261127-03.json` con `nodes`, `edges`, `hyperedges`, `coverage` (líneas hasta EOF) y `source_sha256` (bytes del archivo). Usar rutas relativas con `/`, `_origin: semantic`, evidencia y confianza; no basta actualizar el hash sin renovar la extracción. El constructor descubre todos los fragmentos de ese prefijo y exige cobertura sin solapamientos. Para nuevas áreas de código, ampliar CODE_SOURCES deliberadamente y reconstruir.

No se instalaron hooks de Git, observadores, servicios ni automatización de actualización. Esto es un snapshot; no se mantiene solo. El manifiesto enumera exactamente lo incluido. Los archivos graphify-out/ se escriben en el árbol de trabajo; su publicación depende de las reglas del repositorio.

La generación del HTML es local. El visualizador estándar de Graphify carga vis-network desde un CDN cuando se abre; no se descargó esa biblioteca durante la construcción. JSON, informe y comprobación de vigencia no la necesitan.

## Coste y reproducibilidad

Cero invocaciones externas de modelos desde este constructor. La extracción semántica fue realizada por la sesión y sus subagentes; sus tokens y coste no se midieron. Los ceros heredados del protocolo no representan consumo total nulo. AST y exportación son locales. Versión Graphify: `0.9.36`. Huella de entradas: `f6d06a4e8aacc08f01459a0633e11b3f4202c50fc98912ac75e871d894bb0350`. El informe nativo de la API Graphify se conserva como graphify-analysis-native.md; este es el informe en español.
