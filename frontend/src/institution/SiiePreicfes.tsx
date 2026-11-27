import { useRef, useState } from "react";
import { Button, Field, Notice } from "../shared/ui";
import { institutionHeaders } from "../shared/institutionSession";
import { siieHeaders, type SiieEnvironment } from "../shared/siieEnvironment";
import { useInstitution, useTask } from "./api";

type Installment = {
  installmentId: number;
  concept: string;
  dueDate: string;
  amountCop: number;
};
type Option = {
  planId: number;
  mode: string;
  quoteRevisionId: string;
  amountCop: number;
  expiresAtUtc: string;
  installments: Omit<Installment, "installmentId">[];
};
type Flow = {
  id: string;
  revision: number;
  state: string;
  environment: SiieEnvironment;
  environment_current: boolean;
  binding_expired?: boolean;
  writes_enabled: boolean;
  pending?: string;
  registration?: {
    studentName: string;
    programName: string;
    periodLabel: string;
  };
  binding?: { bindingId: string; expiresAtUtc: string };
  plans?: { options: Option[] };
  assignment?: { plan: { installments: Installment[] } };
  order?: { orderId: string };
  payment?: { state: string };
};
const prefix = "siie-registration/preicfes";
const money = (value: number) =>
  new Intl.NumberFormat("es-CO").format(value) + " pesos";

export function SiiePreicfes({
  environment,
  editable,
}: {
  environment?: SiieEnvironment | null;
  editable: boolean;
}) {
  const { call } = useInstitution();
  const task = useTask();
  const [event, setEvent] = useState("");
  const [conversation, setConversation] = useState("");
  const [resume, setResume] = useState("");
  const [work, setWork] = useState<Flow | null>(null);
  const [saved, setSaved] = useState<
    { id: string; state: string; base_url?: string }[]
  >([]);
  const [reviewed, setReviewed] = useState(false);
  const [option, setOption] = useState("");
  const [choice, setChoice] = useState("");
  const [installment, setInstallment] = useState("");
  const retained = useRef<{ signature: string; id: string } | null>(null);
  const load = async (id: string) => {
    const value = await call<Flow>(`${prefix}/${id}`);
    setWork(value);
    return value;
  };
  const mutation = async (kind: "binding" | "assign" | "order") => {
    if (!work || !reviewed) return;
    const chosen = work.plans?.options.find(
      (v) => `${v.planId}:${v.mode}:${v.quoteRevisionId}` === option,
    );
    const fields = {
      revision: work.revision,
      reviewed: true,
      ...(kind === "assign" && chosen
        ? {
            plan_id: chosen.planId,
            mode: chosen.mode,
            quote_revision_id: chosen.quoteRevisionId,
            choice_message_id: choice,
          }
        : {}),
      ...(kind === "order" ? { installment_id: Number(installment) } : {}),
    };
    const signature = JSON.stringify([work.id, kind, fields]);
    if (retained.current?.signature !== signature)
      retained.current = { signature, id: crypto.randomUUID() };
    await call(`${prefix}/${work.id}/${kind}`, "POST", {
      ...fields,
      operation_id: retained.current.id,
    });
    setReviewed(false);
    await load(work.id);
  };
  const download = async () => {
    if (!work) return;
    const response = await fetch(`/api/institution/${prefix}/${work.id}/pdf`, {
      headers: {
        "X-CRM-Local": "1",
        ...institutionHeaders(),
        ...siieHeaders(prefix),
      },
      credentials: "same-origin",
      cache: "no-store",
      signal: AbortSignal.timeout(45000),
      redirect: "error",
    });
    if (
      !response.ok ||
      !response.headers.get("Content-Type")?.startsWith("application/pdf")
    )
      throw new Error(
        "SIIE no confirmó un PDF válido para este vínculo y orden. Conserva el trabajo para revisión.",
      );
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "volante-preicfes.pdf";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const cannotWrite =
    task.busy ||
    !editable ||
    !reviewed ||
    !work?.environment_current ||
    !work?.writes_enabled;
  const blocked = cannotWrite || !!work?.pending;
  const renewExpired = work?.binding_expired === true;
  return (
    <section
      className="institution-card"
      aria-label="Plan y volante de PRE-ICFES"
    >
      <h3>PRE-ICFES · Plan y volante</h3>
      <p>
        Pasarela desactivada. Cada escritura requiere revisión; emitir un
        volante no acredita pago ni matrícula.
      </p>
      {task.notices}
      <p>
        Entorno:{" "}
        {environment?.base_url ?? "Consulta primero la conexión de SIIE"}
      </p>
      <div className="form-grid">
        <Field
          label="Evento recibido de SIIE"
          id="siie-finance-event"
          value={event}
          onChange={(e) => setEvent(e.target.value)}
        />
        <Field
          label="Conversación WhatsApp verificada"
          id="siie-finance-conversation"
          value={conversation}
          onChange={(e) => setConversation(e.target.value)}
        />
        <Field
          label="Trabajo guardado para consultar"
          id="siie-finance-resume"
          value={resume}
          onChange={(e) => setResume(e.target.value)}
        />
      </div>
      <label>
        <input
          type="checkbox"
          checked={reviewed}
          onChange={(e) => setReviewed(e.target.checked)}
        />{" "}
        He revisado el contexto y la acción. Para asignar un plan, confirmo la
        elección expresa del aspirante y su mensaje de origen.
      </label>
      <div className="button-row">
        <Button
          disabled={
            task.busy ||
            !editable ||
            !environment ||
            !reviewed ||
            !event ||
            !conversation
          }
          onClick={() =>
            void task.run(async () => {
              setWork(
                await call<Flow>(`${prefix}/prepare`, "POST", {
                  event_id: event,
                  conversation_id: conversation,
                  environment,
                  reviewed: true,
                }),
              );
              setReviewed(false);
            })
          }
        >
          Corroborar inscripción
        </Button>
        <Button
          variant="secondary"
          disabled={task.busy || !editable || !resume}
          onClick={() =>
            void task.run(async () => {
              await load(resume);
            })
          }
        >
          Consultar trabajo
        </Button>
      </div>
      <Button
        variant="quiet"
        disabled={task.busy || !editable}
        onClick={() =>
          void task.run(async () =>
            setSaved((await call<{ items: typeof saved }>(prefix)).items),
          )
        }
      >
        Ver trabajos guardados
      </Button>
      {saved.map((item) => (
        <p key={item.id}>
          <Button
            variant="quiet"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                await load(item.id);
              })
            }
          >
            {item.id} · {item.state}
          </Button>{" "}
          {item.base_url}
        </p>
      ))}
      {work && (
        <>
          <p>
            Trabajo: <code>{work.id}</code> · {work.state}
          </p>
          <p>
            {work.registration?.studentName} · {work.registration?.programName}{" "}
            · {work.registration?.periodLabel}
          </p>
          <p>Origen del trabajo: {work.environment.base_url}</p>
          {!work.environment_current && (
            <Notice>
              Este trabajo pertenece a otro entorno. Se conserva sin reenviar;
              no reutilices sus identificadores en el entorno actual.
            </Notice>
          )}
          {!work.writes_enabled && (
            <Notice>
              Escrituras desactivadas. Habilítalas sólo durante la prueba
              revisada y vuelve a desactivarlas al terminar.
            </Notice>
          )}
          {work.pending && (
            <Notice>
              Operación pendiente: {work.pending}. Consulta su resultado antes
              de realizar otra escritura.
            </Notice>
          )}
          <div className="button-row">
            <Button
              disabled={cannotWrite || (!!work.pending && !renewExpired)}
              onClick={() => void task.run(() => mutation("binding"))}
            >
              Crear o renovar vínculo
            </Button>
            <Button
              variant="secondary"
              disabled={task.busy || !work.environment_current || !work.binding}
              onClick={() =>
                void task.run(async () => {
                  setWork(await call<Flow>(`${prefix}/${work.id}/plans`));
                  setOption("");
                  setReviewed(false);
                })
              }
            >
              Consultar planes
            </Button>
            <Button
              variant="secondary"
              disabled={task.busy || !work.environment_current || !work.pending}
              onClick={() =>
                void task.run(async () => {
                  setWork(
                    await call<Flow>(`${prefix}/${work.id}/reconcile`, "POST"),
                  );
                })
              }
            >
              Consultar operación pendiente
            </Button>
          </div>
          {work.plans && (
            <>
              <div className="field">
                <label htmlFor="siie-finance-option">
                  Plan elegido por el aspirante
                </label>
                <select
                  id="siie-finance-option"
                  value={option}
                  onChange={(e) => {
                    setOption(e.target.value);
                    setReviewed(false);
                  }}
                >
                  <option value="">Selecciona una opción</option>
                  {work.plans.options.map((v) => (
                    <option
                      key={`${v.planId}:${v.mode}:${v.quoteRevisionId}`}
                      value={`${v.planId}:${v.mode}:${v.quoteRevisionId}`}
                    >
                      {v.mode} · Plan {v.planId} · {money(v.amountCop)}
                    </option>
                  ))}
                </select>
              </div>
              {work.plans.options
                .filter(
                  (v) =>
                    `${v.planId}:${v.mode}:${v.quoteRevisionId}` === option,
                )
                .map((v) => (
                  <div key={option}>
                    <p>
                      Cotización vigente hasta{" "}
                      {new Date(v.expiresAtUtc).toLocaleString("es-CO")}
                    </p>
                    <ul>
                      {v.installments.map((item, i) => (
                        <li key={i}>
                          {item.concept}: {money(item.amountCop)} ·{" "}
                          {item.dueDate}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              <Field
                label="ID del mensaje de elección expresa"
                id="siie-finance-choice"
                value={choice}
                onChange={(e) => setChoice(e.target.value)}
              />
              <Button
                disabled={blocked || !option || !choice}
                onClick={() => void task.run(() => mutation("assign"))}
              >
                Asignar plan confirmado
              </Button>
            </>
          )}
          {work.assignment && (
            <>
              <div className="field">
                <label htmlFor="siie-finance-installment">
                  Cuota para el volante
                </label>
                <select
                  id="siie-finance-installment"
                  value={installment}
                  onChange={(e) => {
                    setInstallment(e.target.value);
                    setReviewed(false);
                  }}
                >
                  <option value="">Selecciona una cuota asignada</option>
                  {work.assignment.plan.installments.map((v) => (
                    <option key={v.installmentId} value={v.installmentId}>
                      {v.concept} · {money(v.amountCop)} · {v.dueDate}
                    </option>
                  ))}
                </select>
              </div>
              <Button
                disabled={blocked || !installment}
                onClick={() => void task.run(() => mutation("order"))}
              >
                Generar volante de esa cuota
              </Button>
            </>
          )}
          {work.order && (
            <div className="button-row">
              <Button
                disabled={task.busy || !work.environment_current}
                onClick={() => void task.run(download)}
              >
                Descargar PDF validado
              </Button>
              <Button
                variant="secondary"
                disabled={task.busy || !work.environment_current}
                onClick={() =>
                  void task.run(async () =>
                    setWork(await call<Flow>(`${prefix}/${work.id}/payment`)),
                  )
                }
              >
                Consultar estado de pago
              </Button>
              {work.payment && (
                <p>Estado informado por SIIE: {work.payment.state}</p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
