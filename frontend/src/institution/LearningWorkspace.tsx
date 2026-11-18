import { useEffect, useRef, useState } from "react";
import { Badge, Button, Field, Notice, SelectField } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import { ResourceState } from "./Settings";
import { ErrorFeedback, OperationDialog } from "./ErrorFeedback";
import type { ErrorGuidance, OperationFailure } from "./ErrorFeedback";
import { useAdsResource as useResource } from "./adsResource";
import { allowNavigation, useDraftGuard } from "./drafts";
import "./learning.css";

type Task =
  | "lead_scoring"
  | "churn_prediction"
  | "smart_remarketing"
  | "operational_anomaly";
type PackDoc = {
  name: string;
  task: Task;
  scope: "demo" | "native";
  training_enabled: boolean;
};
type Pack = {
  id: string;
  revision: number;
  task: Task;
  scope: "demo" | "native";
  document: PackDoc;
};
type Metric = {
  n: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  brier: number;
  auc: number | null;
  false_positives: number;
  false_negatives: number;
};
type Evaluation = {
  candidate: Metric;
  baseline: Metric;
  eligible: boolean;
  segments: Record<string, { candidate: Metric; baseline: Metric }>;
  train_ids: string[];
  holdout_ids: string[];
};
type ItemDoc = {
  name?: string;
  task?: Task;
  synthetic_demo?: boolean;
  subject_id?: string;
  demo_subject?: string;
  basis?: string;
  reference?: string;
  features?: Record<string, number>;
  label?: number;
  feature_at?: string;
  outcome_at?: string;
  source_kind?: string;
  source_id?: string;
  program?: string;
  stage?: string;
  evaluation?: Evaluation;
  scope?: string;
  model?: { algorithm: string };
  cutoff?: string;
  train_ids?: string[];
  holdout_ids?: string[];
  probability?: number;
  baseline_probability?: number;
  mode?: string;
  algorithm?: string;
  drift?: { review_required: boolean; max_shift: number };
};
type Item = {
  id: string;
  document: ItemDoc;
  created_at: string;
  revision?: number;
  state?: string;
  version?: number;
  hash?: string;
  kind?: string;
  grant_id?: string;
};
type Deployment = {
  revision: number;
  state: string;
  active_id: string | null;
  shadow_id: string | null;
  document: { approved?: string[] };
};
type Detail = { pack: Pack; deployment: Deployment };
type Catalog = {
  tasks: { id: Task; features: string[]; purpose: string }[];
  programs: { id: number; name: string }[];
  stages: { id: string; name: string }[];
  contexts: { conversation_id: string; subject_id: string; label: string }[];
  campaigns: { id: string; label: string }[];
};
const titles: Record<Task, string> = {
  lead_scoring: "Priorización de prospectos",
  churn_prediction: "Riesgo de abandono",
  smart_remarketing: "Oportunidad de seguimiento",
  operational_anomaly: "Anomalías operativas",
};
const tabs = {
  artifacts: "Modelos y evaluación",
  samples: "Muestras revisadas",
  grants: "Autorizaciones",
  datasets: "Datasets",
  predictions: "Predicciones",
  versions: "Versiones",
  events: "Historial",
};
type Tab = keyof typeof tabs;
const pct = (v: number) => `${(100 * v).toFixed(1)}%`;
const labels: Record<string, string> = {
  response_time: "Tiempo de respuesta",
  message_count: "Cantidad de mensajes",
  asked_for_price: "Consulta de precio",
  engagement_score: "Interacción",
  avg_reply_speed: "Rapidez media de respuesta",
  channel_source_score: "Valor del canal",
  followup_count: "Seguimientos",
  inactivity_days: "Días de inactividad",
  negative_sentiment_ratio: "Proporción de sentimiento negativo",
  response_drop: "Caída de respuestas",
  ticket_frequency: "Frecuencia de consultas",
  engagement_decline: "Caída de interacción",
  open_rate: "Tasa de apertura",
  click_rate: "Tasa de clics",
  best_hour: "Hora de mayor respuesta",
  best_channel_score: "Valor del canal preferido",
  campaign_engagement: "Interacción en campañas",
  webhook_errors_24h: "Errores de webhooks en 24 h",
  ai_failed_24h: "Fallos de IA en 24 h",
  outbound_failed_24h: "Fallos de envío en 24 h",
  dead_letters_open: "Eventos fallidos pendientes",
  event_failure_rate: "Tasa de fallos",
};

function useLive() {
  const ref = useRef(true);
  useEffect(() => {
    ref.current = true;
    return () => {
      ref.current = false;
    };
  }, []);
  return ref;
}

function explainLearningError(failure: OperationFailure): ErrorGuidance {
  const code = failure.code ?? "";
  let nextStep =
    "Conserva tus datos y revisa la sección correspondiente del pack antes de reintentar.";
  if (code.includes("shadow"))
    nextStep =
      "Selecciona el modelo en sombra y registra cuatro observaciones de sujetos distintos en la revisión actual antes de promoverlo.";
  else if (/authorization|purpose|subject/.test(code))
    nextStep =
      "Revisa las autorizaciones de finalidad. Si cambió una autorización o identidad, reconstruye el dataset.";
  else if (/dataset|sample|temporal|version/.test(code))
    nextStep =
      "Revisa muestras, fechas y versión del pack. Congela un dataset nuevo con entrenamiento y validación temporal separados.";
  else if (/drift|evaluation/.test(code))
    nextStep =
      "Compara el modelo con el baseline y los errores por segmento. Revisa la deriva; conserva la versión aprobada anterior.";
  else if (code.includes("paused"))
    nextStep =
      "Reanuda sólo la función que necesitas: entrenamiento desde Editar pack o predicción desde Reanudar predicción.";
  return {
    title: "No se pudo completar la operación de aprendizaje",
    detail: failure.message,
    nextStep,
  };
}

export function LearningWorkspace() {
  return (
    <ErrorFeedback explain={explainLearningError}>
      <LearningContent />
    </ErrorFeedback>
  );
}

function LearningContent() {
  const [packOffset, setPackOffset] = useState(0);
  const { session } = useInstitution(),
    catalog = useResource<Catalog>("learning/catalog"),
    packs = useResource<{ items: Pack[]; more: boolean }>(
      `learning/packs?offset=${packOffset}`,
    );
  const [selected, setSelected] = useState(""),
    [creating, setCreating] = useState(false);
  if (!catalog.value || !packs.value)
    return <ResourceState error={catalog.error || packs.error} />;
  return (
    <div className="learning-workspace">
      <header>
        <h1>Inteligencia y entrenamiento</h1>
        <p>Revisa datos, compara modelos y decide qué versión utilizar.</p>
      </header>
      <details>
        <summary>Cómo aprende la institución</summary>
        <p>
          Las reglas de CRM, la memoria colectiva y los modelos de lenguaje
          conservan sus funciones. Aquí se entrenan modelos estadísticos con
          observaciones numéricas revisadas y autorización específica. Las
          predicciones sirven de apoyo a una persona.
        </p>
        <p>
          Los ejemplos ficticios demuestran el funcionamiento. Sus métricas no
          acreditan resultados de la institución.
        </p>
      </details>
      <section className="panel learning-controls">
        <SelectField
          id="learning-pack"
          label="Pack de aprendizaje"
          value={selected}
          options={[
            { value: "", label: "Selecciona un pack" },
            ...(selected && !packs.value.items.some((p) => p.id === selected)
              ? [{ value: selected, label: "Pack seleccionado" }]
              : []),
            ...packs.value.items.map((p) => ({
              value: p.id,
              label: p.document.name,
            })),
          ]}
          onChange={(e) => {
            if (allowNavigation()) {
              setSelected(e.target.value);
              setCreating(false);
            }
          }}
        />
        <Button
          variant="secondary"
          disabled={!packOffset}
          onClick={() => {
            if (allowNavigation()) setPackOffset(Math.max(0, packOffset - 50));
          }}
        >
          Packs anteriores
        </Button>
        <Button
          variant="secondary"
          disabled={!packs.value.more}
          onClick={() => {
            if (allowNavigation()) setPackOffset(packOffset + 50);
          }}
        >
          Más packs
        </Button>
        <Button
          onClick={() => {
            if (allowNavigation()) setCreating(true);
          }}
        >
          Crear pack
        </Button>
      </section>
      {creating ? (
        <PackEditor
          key={`new:${session.csrf_token}`}
          catalog={catalog.value}
          done={async (id) => {
            setCreating(false);
            setSelected(id);
            await packs.reload();
          }}
        />
      ) : selected ? (
        <PackWorkspace
          key={`${selected}:${session.csrf_token}`}
          id={selected}
          catalog={catalog.value}
          changed={() => packs.reload()}
        />
      ) : (
        <Notice>Selecciona un ejemplo o crea un pack para comenzar.</Notice>
      )}
    </div>
  );
}

function PackEditor({
  catalog,
  current,
  done,
}: {
  catalog: Catalog;
  current?: Pack;
  done: (id: string) => Promise<void>;
}) {
  const [value, setValue] = useState<PackDoc>(
    current?.document ?? {
      name: "",
      task: "lead_scoring",
      scope: "native",
      training_enabled: true,
    },
  );
  const task = useTask(),
    intent = useIntent(),
    { call } = useInstitution(),
    live = useLive();
  const dirty =
    JSON.stringify(value) !==
    JSON.stringify(
      current?.document ?? {
        name: "",
        task: "lead_scoring",
        scope: "native",
        training_enabled: true,
      },
    );
  useDraftGuard(dirty);
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const data = { revision: current?.revision ?? 0, document: value },
            path = `learning/packs${current ? `/${current.id}` : ""}`;
          const result = await call<{ id: string }>(
            path,
            current ? "PATCH" : "POST",
            { ...data, operation_id: intent.get({ path, ...data }) },
          );
          if (!live.current) return;
          intent.clear();
          await done(result.id);
        });
      }}
    >
      <h2>{current ? "Editar pack" : "Nuevo pack"}</h2>
      <fieldset disabled={task.busy}>
        <Field
          id="learning-name"
          label="Nombre del pack"
          value={value.name}
          required
          minLength={3}
          maxLength={100}
          onChange={(e) => setValue({ ...value, name: e.target.value })}
        />
        <SelectField
          id="learning-task"
          label="Objetivo"
          value={value.task}
          disabled={!!current}
          options={catalog.tasks.map((v) => ({
            value: v.id,
            label: titles[v.id],
          }))}
          onChange={(e) => setValue({ ...value, task: e.target.value as Task })}
        />
        <SelectField
          id="learning-scope"
          label="Datos del pack"
          value={value.scope}
          disabled={!!current}
          options={[
            { value: "native", label: "Institucionales autorizados" },
            { value: "demo", label: "Demostración con datos ficticios" },
          ]}
          onChange={(e) =>
            setValue({ ...value, scope: e.target.value as PackDoc["scope"] })
          }
        />
        <label>
          <input
            type="checkbox"
            checked={value.training_enabled}
            onChange={(e) =>
              setValue({ ...value, training_enabled: e.target.checked })
            }
          />{" "}
          Permitir nuevos entrenamientos
        </label>
        <Button type="submit">Guardar pack</Button>
      </fieldset>
      {task.notices}
    </form>
  );
}

function PackWorkspace({
  id,
  catalog,
  changed,
}: {
  id: string;
  catalog: Catalog;
  changed: () => Promise<unknown>;
}) {
  const detail = useResource<Detail>(`learning/packs/${id}`),
    [tab, setTab] = useState<Tab>("artifacts"),
    [editing, setEditing] = useState(false);
  if (!detail.value) return <ResourceState error={detail.error} />;
  const pack = detail.value.pack;
  return (
    <>
      <section className="panel learning-heading">
        <h2>{pack.document.name}</h2>
        <Badge>
          {pack.scope === "demo" ? "Ejemplo ficticio" : "Institucional"}
        </Badge>
        <p>
          {titles[pack.task]} · Versión de pack {pack.revision} · Entrenamiento{" "}
          {pack.document.training_enabled ? "habilitado" : "detenido"}
        </p>
        <Button
          variant="secondary"
          onClick={() => {
            if (allowNavigation()) setEditing(!editing);
          }}
        >
          {editing ? "Cerrar edición" : "Editar pack"}
        </Button>
      </section>
      {editing && (
        <PackEditor
          key={`edit:${pack.revision}`}
          catalog={catalog}
          current={pack}
          done={async () => {
            setEditing(false);
            await Promise.all([detail.reload(), changed()]);
          }}
        />
      )}
      <nav className="learning-tabs" aria-label="Secciones de aprendizaje">
        {Object.entries(tabs).map(([key, label]) => (
          <Button
            key={key}
            variant={tab === key ? "primary" : "secondary"}
            aria-pressed={tab === key}
            onClick={() => {
              if (allowNavigation()) {
                setEditing(false);
                setTab(key as Tab);
              }
            }}
          >
            {label}
          </Button>
        ))}
      </nav>
      <Records
        key={`${id}:${tab}`}
        tab={tab}
        detail={detail.value}
        catalog={catalog}
        refreshDetail={() => detail.reload()}
      />
    </>
  );
}

function Records({
  tab,
  detail,
  catalog,
  refreshDetail,
}: {
  tab: Tab;
  detail: Detail;
  catalog: Catalog;
  refreshDetail: () => Promise<unknown>;
}) {
  const pack = detail.pack,
    base = `learning/packs/${pack.id}`,
    [offset, setOffset] = useState(0),
    records = useResource<{ items: Item[]; more: boolean }>(
      `${base}/${tab}?offset=${offset}`,
    ),
    [selected, setSelected] = useState<Item | null>(null),
    [promotion, setPromotion] = useState<{
      id: string;
      revision: number;
      trigger: Element | null;
    } | null>(null);
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent(),
    live = useLive(),
    canSelect = session.actions.includes("settings.ai.write");
  const action = (
    path: string,
    body: object,
    message = "Operación completada.",
  ) =>
    void task.run(async () => {
      const result = await call<{ id: string }>(path, "POST", {
        ...body,
        operation_id: intent.get({ path, ...body }),
      });
      if (!live.current) return;
      intent.clear();
      await Promise.all([records.reload(), refreshDetail()]);
      if (live.current && result.id) setSelected(null);
    }, message);
  if (!records.value) return <ResourceState error={records.error} />;
  const deployment = detail.deployment;
  return (
    <>
      <section className="panel learning-controls">
        <span>
          Predicción:{" "}
          {deployment.state === "paused"
            ? "pausada"
            : deployment.active_id
              ? "versión aprobada"
              : "sin versión activa"}
        </span>
        {canSelect && (
          <Button
            variant="secondary"
            disabled={task.busy}
            onClick={() =>
              action(`${base}/selection`, {
                revision: deployment.revision,
                action: deployment.state === "paused" ? "resume" : "pause",
              })
            }
          >
            {deployment.state === "paused"
              ? "Reanudar predicción"
              : "Pausar predicción"}
          </Button>
        )}
      </section>
      {task.notices}
      {promotion && (
        <OperationDialog
          success
          guidance={{
            title: "Aprobar versión de apoyo",
            detail: `Modelo ${promotion.id.slice(0, 8)} · ${pack.scope === "demo" ? "Ejemplo ficticio" : "Datos institucionales autorizados"}. Revisa las métricas y las observaciones en sombra. Esta operación no envía mensajes ni toma decisiones sobre personas.`,
            nextStep:
              "El servidor comprobará evaluación, autorizaciones, deriva y la revisión actual antes de promoverlo.",
          }}
          trigger={promotion.trigger}
          dismiss={() => setPromotion(null)}
          dismissLabel="Cancelar promoción"
          confirm={{
            label: "Confirmar promoción",
            run: () =>
              action(
                `${base}/selection`,
                {
                  revision: promotion.revision,
                  artifact_id: promotion.id,
                  action: "promote",
                },
                "Versión aprobada para predicciones de apoyo.",
              ),
          }}
        />
      )}
      {tab === "grants" && (
        <GrantEditor
          key={`${offset}:${selected?.id ?? "new"}`}
          pack={pack}
          catalog={catalog}
          current={selected ?? undefined}
          done={async () => {
            setSelected(null);
            await records.reload();
          }}
        />
      )}
      {tab === "samples" && (
        <SampleEditor
          key={`${offset}:${selected?.id ?? "new"}`}
          pack={pack}
          catalog={catalog}
          current={selected ?? undefined}
          done={async () => {
            setSelected(null);
            await records.reload();
          }}
        />
      )}
      {tab === "datasets" && (
        <DatasetEditor base={base} done={() => records.reload()} />
      )}
      {tab === "predictions" && (
        <InferenceEditor
          pack={pack}
          catalog={catalog}
          done={() => records.reload()}
        />
      )}
      <div className="learning-records">
        {records.value.items.map((item) => (
          <article className="panel" key={item.id}>
            {tab === "artifacts" && item.document.evaluation ? (
              <>
                <h3>Modelo {item.id.slice(0, 8)}</h3>
                <p>
                  Regresión logística entrenada ·{" "}
                  {item.document.scope === "demo"
                    ? "Ejemplo ficticio"
                    : "Institucional"}
                </p>
                <Badge>
                  {deployment.active_id === item.id
                    ? "Versión activa"
                    : deployment.shadow_id === item.id
                      ? "En sombra"
                      : "Candidato"}
                </Badge>
                <EvaluationView
                  value={item.document.evaluation}
                  catalog={catalog}
                />
                {canSelect && (
                  <div className="learning-controls">
                    <Button
                      disabled={task.busy}
                      onClick={() =>
                        action(`${base}/selection`, {
                          revision: deployment.revision,
                          artifact_id: item.id,
                          action: "shadow",
                        })
                      }
                    >
                      Evaluar en sombra
                    </Button>
                    <Button
                      disabled={
                        task.busy ||
                        !item.document.evaluation.eligible ||
                        deployment.shadow_id !== item.id
                      }
                      onClick={() =>
                        setPromotion({
                          id: item.id,
                          revision: deployment.revision,
                          trigger: document.activeElement,
                        })
                      }
                    >
                      Promover versión
                    </Button>
                    {deployment.document.approved?.includes(item.id) &&
                      deployment.active_id !== item.id && (
                        <Button
                          variant="secondary"
                          disabled={task.busy}
                          onClick={() =>
                            action(`${base}/selection`, {
                              revision: deployment.revision,
                              artifact_id: item.id,
                              action: "rollback",
                            })
                          }
                        >
                          Revertir a esta versión
                        </Button>
                      )}
                  </div>
                )}
              </>
            ) : tab === "datasets" ? (
              <>
                <h3>Dataset {item.id.slice(0, 8)}</h3>
                <p>
                  {item.document.train_ids?.length} muestras de entrenamiento ·{" "}
                  {item.document.holdout_ids?.length} de validación
                </p>
                <p>Corte temporal: {item.document.cutoff}</p>
                <Button
                  disabled={task.busy || !pack.document.training_enabled}
                  onClick={() =>
                    action(
                      `${base}/train`,
                      { dataset_id: item.id },
                      "Modelo entrenado y evaluado. Revisa sus métricas en Modelos y evaluación.",
                    )
                  }
                >
                  Entrenar candidato
                </Button>
              </>
            ) : tab === "predictions" ? (
              <>
                <h3>
                  Predicción{" "}
                  {item.document.mode === "shadow"
                    ? "en sombra"
                    : "de versión aprobada"}
                </h3>
                <p>
                  Modelo: {pct(item.document.probability ?? 0)} · Baseline:{" "}
                  {pct(item.document.baseline_probability ?? 0)}
                </p>
                <p>
                  {item.document.drift?.review_required
                    ? "Deriva detectada: requiere revisión"
                    : "Sin alerta de deriva en esta observación"}
                </p>
                <small>No ejecuta decisiones ni envíos.</small>
              </>
            ) : tab === "grants" ? (
              <>
                <h3>{item.document.reference}</h3>
                <Badge>
                  {item.state === "active" ? "Autorizada" : "Revocada"}
                </Badge>
                <p>Finalidad: {titles[pack.task]}</p>
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (allowNavigation()) setSelected(item);
                  }}
                >
                  Revisar autorización
                </Button>
              </>
            ) : tab === "samples" ? (
              <>
                <h3>Muestra {item.id.slice(0, 8)}</h3>
                <p>
                  Resultado revisado:{" "}
                  {item.document.label === 1 ? "Positivo" : "Negativo"} ·{" "}
                  {item.document.synthetic_demo
                    ? "Ficticia"
                    : "Observación humana"}
                </p>
                <p>
                  {item.document.stage} · {item.document.feature_at}
                </p>
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (allowNavigation()) setSelected(item);
                  }}
                >
                  Corregir etiqueta
                </Button>
              </>
            ) : (
              <>
                <h3>{item.kind ?? `Versión ${item.version ?? ""}`}</h3>
                <p>{new Date(item.created_at).toLocaleString()}</p>
              </>
            )}
            <details>
              <summary>Identificación y trazabilidad</summary>
              <small className="learning-hash">
                ID: {item.id}
                {item.hash ? ` · SHA256: ${item.hash}` : ""}
              </small>
            </details>
          </article>
        ))}
      </div>
      {records.value.items.length === 0 && (
        <Notice>Todavía no hay registros en esta sección.</Notice>
      )}
      <div className="learning-controls">
        <Button
          variant="secondary"
          disabled={task.busy || !offset}
          onClick={() => {
            if (allowNavigation()) {
              setOffset(Math.max(0, offset - 50));
              setSelected(null);
            }
          }}
        >
          Anterior
        </Button>
        <span>
          {offset + 1}–{offset + records.value.items.length}
        </span>
        <Button
          variant="secondary"
          disabled={task.busy || !records.value.more}
          onClick={() => {
            if (allowNavigation()) {
              setOffset(offset + 50);
              setSelected(null);
            }
          }}
        >
          Siguiente
        </Button>
      </div>
    </>
  );
}

function EvaluationView({
  value,
  catalog,
}: {
  value: Evaluation;
  catalog: Catalog;
}) {
  return (
    <>
      <p>
        Entrenamiento: {value.train_ids.length} · Validación temporal:{" "}
        {value.holdout_ids.length}
      </p>
      <div className="learning-table">
        <table>
          <caption>Comparación en datos de validación</caption>
          <thead>
            <tr>
              <th>Métrica</th>
              <th>Modelo</th>
              <th>Baseline</th>
            </tr>
          </thead>
          <tbody>
            {(
              [
                ["Exactitud", "accuracy"],
                ["Precisión", "precision"],
                ["Sensibilidad", "recall"],
                ["F1", "f1"],
              ] as const
            ).map(([label, key]) => (
              <tr key={key}>
                <th>{label}</th>
                <td>{pct(value.candidate[key])}</td>
                <td>{pct(value.baseline[key])}</td>
              </tr>
            ))}
            <tr>
              <th>Error Brier · menor es mejor</th>
              <td>{value.candidate.brier.toFixed(4)}</td>
              <td>{value.baseline.brier.toFixed(4)}</td>
            </tr>
            <tr>
              <th>AUC</th>
              <td>{value.candidate.auc?.toFixed(3) ?? "Sin ambas clases"}</td>
              <td>{value.baseline.auc?.toFixed(3) ?? "Sin ambas clases"}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p>
        {value.eligible
          ? "Supera las condiciones de evaluación. Requiere revisión y observaciones en sombra para promoverse."
          : "No supera las condiciones de promoción."}
      </p>
      <details>
        <summary>Errores por programa y etapa</summary>
        {Object.entries(value.segments).map(([key, segment]) => (
          <p key={key}>
            {key.split(":")[0] === "general"
              ? "General"
              : (catalog.programs.find(
                  (p) => String(p.id) === key.split(":")[0],
                )?.name ?? key.split(":")[0])}{" "}
            ·{" "}
            {catalog.stages.find((s) => s.id === key.split(":")[1])?.name ??
              key.split(":")[1]}
            : {segment.candidate.n} observaciones · falsos positivos{" "}
            {segment.candidate.false_positives} · falsos negativos{" "}
            {segment.candidate.false_negatives}
          </p>
        ))}
      </details>
    </>
  );
}

function DatasetEditor({
  base,
  done,
}: {
  base: string;
  done: () => Promise<unknown>;
}) {
  const [cutoff, setCutoff] = useState(""),
    { call } = useInstitution(),
    task = useTask(),
    intent = useIntent(),
    live = useLive();
  useDraftGuard(!!cutoff);
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const body = { cutoff: new Date(cutoff).toISOString() };
          await call(`${base}/datasets`, "POST", {
            ...body,
            operation_id: intent.get(body),
          });
          if (live.current) {
            intent.clear();
            setCutoff("");
            await done();
          }
        });
      }}
    >
      <h3>Congelar dataset</h3>
      <p>
        Se necesitan al menos 16 muestras previas y 8 posteriores al corte, con
        ambas clases y sujetos separados.
      </p>
      <fieldset disabled={task.busy}>
        <Field
          id="learning-cutoff"
          label="Corte temporal"
          type="datetime-local"
          required
          value={cutoff}
          onChange={(e) => setCutoff(e.target.value)}
        />
        <Button type="submit">Crear dataset versionado</Button>
      </fieldset>
      {task.notices}
    </form>
  );
}

function GrantEditor({
  pack,
  catalog,
  current,
  done,
}: {
  pack: Pack;
  catalog: Catalog;
  current?: Item;
  done: () => Promise<void>;
}) {
  const [subject, setSubject] = useState(current?.document.subject_id ?? ""),
    [reference, setReference] = useState(current?.document.reference ?? ""),
    [approved, setApproved] = useState(current?.state !== "revoked"),
    [basis, setBasis] = useState(current?.document.basis ?? "consent");
  const task = useTask(),
    intent = useIntent(),
    { call } = useInstitution(),
    live = useLive(),
    demo = useRef(current?.document.demo_subject ?? crypto.randomUUID());
  useDraftGuard(
    !!reference &&
      (reference !== current?.document.reference ||
        approved !== (current?.state === "active")),
  );
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const body = {
            revision: current?.revision ?? 0,
            subject_id: pack.scope === "native" ? subject : null,
            demo_subject: pack.scope === "demo" ? demo.current : null,
            approved,
            basis: pack.scope === "demo" ? "synthetic_demo" : basis,
            reference,
          };
          await call(`learning/packs/${pack.id}/grants`, "POST", {
            ...body,
            operation_id: intent.get(body),
          });
          if (live.current) {
            intent.clear();
            setReference("");
            if (!current) demo.current = crypto.randomUUID();
            await done();
          }
        });
      }}
    >
      <h3>{current ? "Revisar finalidad" : "Autorizar finalidad"}</h3>
      <p>
        Esta autorización es específica para {titles[pack.task].toLowerCase()}.
        El consentimiento comercial se administra por separado.
      </p>
      <fieldset disabled={task.busy}>
        {pack.scope === "native" && (
          <>
            <SelectField
              id="learning-subject"
              label="Contacto autorizado"
              value={subject}
              required
              disabled={!!current}
              options={[
                { value: "", label: "Selecciona un contacto" },
                ...Array.from(
                  new Map(
                    catalog.contexts.map((c) => [
                      c.subject_id,
                      { value: c.subject_id, label: c.label },
                    ]),
                  ).values(),
                ),
              ]}
              onChange={(e) => setSubject(e.target.value)}
            />
            <SelectField
              id="learning-basis"
              label="Fundamento revisado"
              value={basis}
              options={[
                { value: "consent", label: "Consentimiento específico" },
                {
                  value: "institutional_authorization",
                  label: "Autorización institucional documentada",
                },
              ]}
              onChange={(e) => setBasis(e.target.value)}
            />
          </>
        )}
        <Field
          id="learning-reference"
          label="Referencia de autorización"
          value={reference}
          pattern="[A-Za-z0-9_.:/-]+"
          required
          minLength={3}
          maxLength={80}
          hint="Usa un identificador del documento; evita nombres o datos personales."
          onChange={(e) => setReference(e.target.value)}
        />
        <label>
          <input
            type="checkbox"
            checked={approved}
            onChange={(e) => setApproved(e.target.checked)}
          />{" "}
          Autorizar esta finalidad
        </label>
        <Button type="submit">Guardar autorización</Button>
      </fieldset>
      {task.notices}
    </form>
  );
}

function NumericFields({
  keys,
  value,
  changed,
  disabled = false,
}: {
  keys: string[];
  value: Record<string, number>;
  changed: (value: Record<string, number>) => void;
  disabled?: boolean;
}) {
  return (
    <div className="learning-numbers">
      {keys.map((key) => (
        <Field
          key={key}
          id={`learning-feature-${key}`}
          label={labels[key] ?? key}
          type="number"
          min={0}
          max={1000000}
          step="any"
          required
          disabled={disabled}
          value={value[key] ?? ""}
          onChange={(e) => changed({ ...value, [key]: Number(e.target.value) })}
        />
      ))}
    </div>
  );
}

function SampleEditor({
  pack,
  catalog,
  current,
  done,
}: {
  pack: Pack;
  catalog: Catalog;
  current?: Item;
  done: () => Promise<void>;
}) {
  const task = useTask(),
    intent = useIntent(),
    { call } = useInstitution(),
    live = useLive();
  const [grant, setGrant] = useState(current?.grant_id ?? ""),
    [source, setSource] = useState(
      current?.document.source_kind ??
        (pack.scope === "demo" ? "demo" : "conversation"),
    ),
    [sourceId, setSourceId] = useState(current?.document.source_id ?? ""),
    [program, setProgram] = useState(
      current?.document.program === "general"
        ? ""
        : (current?.document.program ?? ""),
    ),
    [stage, setStage] = useState(
      current?.document.stage ?? catalog.stages[0]?.id ?? "new",
    ),
    [featureAt, setFeatureAt] = useState(current?.document.feature_at ?? ""),
    [outcomeAt, setOutcomeAt] = useState(""),
    [label, setLabel] = useState(String(current?.document.label ?? 0)),
    [values, setValues] = useState<Record<string, number>>(
      current?.document.features ?? {},
    );
  const keys = catalog.tasks.find((v) => v.id === pack.task)?.features ?? [];
  useDraftGuard(!!outcomeAt || (!current && Object.keys(values).length > 0));
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const body = {
            grant_id: grant,
            source_kind: source,
            source_id: source === "demo" ? null : sourceId,
            program_id: program ? Number(program) : null,
            stage,
            feature_at: new Date(featureAt).toISOString(),
            outcome_at: new Date(outcomeAt).toISOString(),
            features: values,
            label: Number(label),
            supersedes: current?.id ?? null,
          };
          await call(`learning/packs/${pack.id}/samples`, "POST", {
            ...body,
            operation_id: intent.get(body),
          });
          if (live.current) {
            intent.clear();
            setOutcomeAt("");
            setValues({});
            await done();
          }
        });
      }}
    >
      <h3>
        {current
          ? "Corregir etiqueta conservando la muestra anterior"
          : "Revisar observación numérica"}
      </h3>
      <p>
        Registra valores conocidos en la fecha de observación y un resultado
        verificado posterior. No copies mensajes ni datos personales en las
        muestras.
      </p>
      <fieldset disabled={task.busy}>
        <GrantPicker
          pack={pack.id}
          id="learning-sample-grant"
          label="Autorización de finalidad"
          value={grant}
          changed={setGrant}
          disabled={!!current}
        />
        {pack.scope === "native" && (
          <>
            <SelectField
              id="learning-source"
              label="Procedencia"
              value={source}
              disabled={!!current}
              options={[
                { value: "conversation", label: "Conversación" },
                { value: "campaign", label: "Campaña" },
                { value: "admissions", label: "Contexto de admisiones en CRM" },
              ]}
              onChange={(e) => {
                setSource(e.target.value);
                setSourceId("");
              }}
            />
            <SelectField
              id="learning-source-id"
              label="Registro de origen"
              value={sourceId}
              required
              disabled={!!current}
              options={[
                { value: "", label: "Selecciona el origen" },
                ...(source === "campaign"
                  ? catalog.campaigns.map((v) => ({
                      value: v.id,
                      label: v.label,
                    }))
                  : catalog.contexts.map((v) => ({
                      value: v.conversation_id,
                      label: v.label,
                    }))),
              ]}
              onChange={(e) => setSourceId(e.target.value)}
            />
          </>
        )}
        <SelectField
          id="learning-program"
          label="Programa de la muestra"
          value={program}
          options={[
            { value: "", label: "General" },
            ...catalog.programs.map((v) => ({
              value: String(v.id),
              label: v.name,
            })),
          ]}
          onChange={(e) => setProgram(e.target.value)}
        />
        <SelectField
          id="learning-stage"
          label="Etapa de la muestra"
          value={stage}
          options={
            current && !catalog.stages.some((v) => v.id === stage)
              ? [
                  stage,
                  ...catalog.stages.map((v) => ({
                    value: v.id,
                    label: v.name,
                  })),
                ]
              : catalog.stages.map((v) => ({ value: v.id, label: v.name }))
          }
          onChange={(e) => setStage(e.target.value)}
        />
        <Field
          id="learning-observed"
          label="Fecha de observación"
          type={current ? "text" : "datetime-local"}
          required
          disabled={!!current}
          value={featureAt}
          onChange={(e) => setFeatureAt(e.target.value)}
        />
        <Field
          id="learning-outcome"
          label="Fecha del resultado verificado"
          type="datetime-local"
          required
          value={outcomeAt}
          onChange={(e) => setOutcomeAt(e.target.value)}
        />
        <SelectField
          id="learning-label"
          label="Resultado revisado"
          value={label}
          options={[
            { value: "0", label: "Negativo" },
            { value: "1", label: "Positivo" },
          ]}
          onChange={(e) => setLabel(e.target.value)}
        />
        <NumericFields
          keys={keys}
          value={values}
          disabled={!!current}
          changed={setValues}
        />
        <Button type="submit">Guardar muestra revisada</Button>
      </fieldset>
      {task.notices}
    </form>
  );
}

function InferenceEditor({
  pack,
  catalog,
  done,
}: {
  pack: Pack;
  catalog: Catalog;
  done: () => Promise<unknown>;
}) {
  const [grant, setGrant] = useState(""),
    [mode, setMode] = useState("shadow"),
    [values, setValues] = useState<Record<string, number>>({});
  const task = useTask(),
    intent = useIntent(),
    { call } = useInstitution(),
    live = useLive(),
    keys = catalog.tasks.find((v) => v.id === pack.task)?.features ?? [];
  useDraftGuard(Object.keys(values).length > 0);
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const body = { grant_id: grant, mode, features: values };
          await call(`learning/packs/${pack.id}/infer`, "POST", {
            ...body,
            operation_id: intent.get(body),
          });
          if (live.current) {
            intent.clear();
            setValues({});
            await done();
          }
        });
      }}
    >
      <h3>Comparar predicción y baseline</h3>
      <fieldset disabled={task.busy}>
        <GrantPicker
          pack={pack.id}
          id="learning-infer-grant"
          label="Autorización para predicción"
          value={grant}
          changed={setGrant}
        />
        <SelectField
          id="learning-mode"
          label="Versión para comparar"
          value={mode}
          options={[
            { value: "shadow", label: "Modelo en sombra" },
            { value: "active", label: "Modelo aprobado" },
          ]}
          onChange={(e) => setMode(e.target.value)}
        />
        <NumericFields keys={keys} value={values} changed={setValues} />
        <Button type="submit">Calcular predicción</Button>
      </fieldset>
      {task.notices}
    </form>
  );
}

function GrantPicker({
  pack,
  id,
  label,
  value,
  changed,
  disabled = false,
}: {
  pack: string;
  id: string;
  label: string;
  value: string;
  changed: (v: string) => void;
  disabled?: boolean;
}) {
  const [offset, setOffset] = useState(0),
    page = useResource<{ items: Item[]; more: boolean }>(
      `learning/packs/${pack}/grants?offset=${offset}`,
    );
  if (!page.value) return <ResourceState error={page.error} />;
  const active = page.value.items.filter((v) => v.state === "active");
  return (
    <div>
      <SelectField
        id={id}
        label={label}
        value={value}
        required
        disabled={disabled}
        options={[
          { value: "", label: "Selecciona una autorización" },
          ...(value && !active.some((v) => v.id === value)
            ? [
                {
                  value,
                  label: "Autorización seleccionada · " + value.slice(0, 8),
                },
              ]
            : []),
          ...active.map((v) => ({
            value: v.id,
            label: `${v.document.reference} · ${v.id.slice(0, 8)}`,
          })),
        ]}
        onChange={(e) => changed(e.target.value)}
      />
      <div className="learning-controls">
        <Button
          variant="secondary"
          disabled={disabled || !offset}
          onClick={() => setOffset(Math.max(0, offset - 50))}
        >
          Autorizaciones anteriores
        </Button>
        <Button
          variant="secondary"
          disabled={disabled || !page.value.more}
          onClick={() => setOffset(offset + 50)}
        >
          Más autorizaciones
        </Button>
      </div>
    </div>
  );
}
