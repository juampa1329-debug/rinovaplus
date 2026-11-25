import { useEffect, useEffectEvent, useRef, useState } from "react";
import { Button, Notice, SelectField } from "../shared/ui";
import { useInstitution, useTask } from "./api";

type Values = Record<string, unknown>;
type Preparation = {
  webhook_secret_configured: boolean;
  webhook_enabled: boolean;
  stage_key: string;
  stages: { key: string; label: string }[];
};
const types: Record<string, string> = {
  "pre_registration.created": "Preinscripción nueva",
  "pre_registration.updated": "Preinscripción actualizada",
  "applicant.created": "Aspirante nuevo",
  "registration.created": "Inscripción nueva",
  "registration.updated": "Inscripción actualizada",
  "documents.updated": "Documentos actualizados",
};
const projections: Record<string, string> = {
  created: "Contacto creado en CRM",
  linked: "Vínculo actualizado",
  stale_ignored: "Evento anterior conservado",
  review_required: "Vínculo por revisar",
};
const text = (v: unknown) => (v == null ? "" : String(v));
const date = (v?: string) => {
  if (!v || !Number.isFinite(Date.parse(v))) return "Sin fecha disponible";
  return new Date(v).toLocaleString("es-CO", { timeZone: "America/Bogota" });
};

export function SiieWebhookReadiness({ status }: { status: Preparation }) {
  const stage = status.stages.find((v) => v.key === status.stage_key);
  return (
    <section
      className="siie-webhook-readiness"
      aria-label="Preparación de la prueba conjunta"
    >
      <h4>Preparación de la prueba conjunta</h4>
      <p>
        Este estado usa la configuración guardada. La prueba con el emisor de
        SIIE se verifica cuando llegue su primer evento firmado.
      </p>
      <dl className="siie-webhook-checks">
        <div>
          <dt>Firma entrante</dt>
          <dd>
            {status.webhook_secret_configured
              ? "Secreto configurado en el backend"
              : "Pendiente de configurar el secreto compartido"}
          </dd>
        </div>
        <div>
          <dt>Etapa de entrada</dt>
          <dd>
            {stage ? stage.label : "Pendiente de seleccionar una etapa activa"}
          </dd>
        </div>
        <div>
          <dt>Recepción</dt>
          <dd>
            {status.webhook_enabled && stage && status.webhook_secret_configured
              ? "Habilitada · lista para recibir el piloto"
              : status.webhook_enabled
                ? "Requiere revisar firma o etapa antes del piloto"
                : "Desactivada · en preparación"}
          </dd>
        </div>
        <div>
          <dt>Volante y PDF de PRE-ICFES</dt>
          <dd>Contrato de pagos pendiente de SIIE</dd>
        </div>
      </dl>
      <p>
        El recorrido previsto es confirmar inscripción y vínculo con el chat,
        obtener la elección de contado o financiado y solicitar el volante a
        SIIE. La generación y el envío del PDF estarán disponibles después de
        integrar y probar ese contrato.
      </p>
    </section>
  );
}

type Row = {
  id: string;
  event_type?: string;
  projection?: string;
  updated_at?: string;
};
type Review = {
  revision: number;
  state: string;
  registered: boolean;
  contact_id?: string | null;
  snapshot: Values;
};
type Candidate = { id: string; name: string; phone: string };
type Detail = {
  event: Values;
  candidates: Candidate[];
  link_review?: Review | null;
};

export function SiieWebhookReceipts({ refreshKey }: { refreshKey: number }) {
  const { call, session } = useInstitution();
  const editable = session.actions.includes("crm.write");
  const task = useTask();
  const [rows, setRows] = useState<Row[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [eventId, setEventId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const epoch = useRef(0);
  const close = () => {
    epoch.current++;
    setDetail(null);
    setEventId("");
    setCandidateId("");
    setReviewed(false);
  };
  const read = async (next = 0) => {
    close();
    const ticket = epoch.current;
    const page = await call<{ items: Row[]; has_more?: boolean }>(
      `siie-registration/records/se?offset=${next}`,
    );
    if (ticket !== epoch.current) return;
    setRows(page.items);
    setHasMore(page.has_more === true);
    setOffset(next);
  };
  const initialRead = useEffectEvent(() => {
    void task.run(() => read(), "");
  });
  useEffect(() => {
    initialRead();
    const current = epoch;
    return () => {
      current.current++;
    };
  }, [refreshKey]);
  const open = async (id: string) => {
    close();
    const ticket = epoch.current;
    const result = await call<Detail>(`siie-registration/records/se/${id}`);
    if (ticket !== epoch.current) return;
    setDetail(result);
    setEventId(id);
  };
  const snapshot = detail?.link_review?.snapshot ?? detail?.event;
  const person = snapshot?.persona as Values | undefined;
  return (
    <section aria-label="Recepción desde SIIE">
      <header className="siie-registration-heading">
        <h4>Recepción desde SIIE</h4>
        <Button
          variant="quiet"
          disabled={task.busy}
          onClick={() =>
            void task.run(() => read(), "Recepciones actualizadas")
          }
        >
          Actualizar recepciones
        </Button>
      </header>
      <p>
        Los inscritos quedan fuera de promociones. Las coincidencias con
        contactos existentes se conservan para revisar el vínculo. Un recibo no
        acredita un volante ni un mensaje enviado.
      </p>
      {task.notices}
      <div className="siie-registration-list">
        {rows.map((row) => (
          <Button
            key={row.id}
            variant="secondary"
            aria-pressed={eventId === row.id}
            disabled={task.busy || !editable}
            onClick={() => void task.run(() => open(row.id), "")}
          >
            <strong>{types[row.event_type ?? ""] ?? "Evento de SIIE"}</strong>
            <span>
              {projections[row.projection ?? ""] ?? "Vínculo por revisar"} ·{" "}
              {date(row.updated_at)} (Bogotá)
            </span>
            <small>Referencia: {row.id}</small>
          </Button>
        ))}
        {!rows.length && (
          <p>
            {offset
              ? "No hay más recepciones en esta página. Vuelve a la anterior o actualiza las recepciones."
              : "No se han recibido eventos verificados. El piloto con SIIE sigue pendiente."}
          </p>
        )}
      </div>
      <nav
        className="siie-registration-actions"
        aria-label="Páginas de recepciones de SIIE"
      >
        <Button
          variant="quiet"
          disabled={task.busy || offset === 0}
          onClick={() =>
            void task.run(() => read(Math.max(0, offset - 25)), "")
          }
        >
          Recepciones anteriores de la lista
        </Button>
        <span>Página {offset / 25 + 1} · hasta 25 recepciones</span>
        <Button
          variant="quiet"
          disabled={task.busy || !hasMore}
          onClick={() => void task.run(() => read(offset + 25), "")}
        >
          Más recepciones
        </Button>
      </nav>
      {!editable && (
        <p>
          Los datos personales y la revisión del vínculo requieren permisos de
          operación de Admisiones.
        </p>
      )}
      {detail && snapshot && (
        <section
          className="panel"
          aria-label="Detalle privado de recepción SIIE"
        >
          <h4>{types[text(detail.event.event_type)] ?? "Evento de SIIE"}</h4>
          <p>
            Referencia del recibo: {eventId} · Cambio en SIIE:{" "}
            {date(text(detail.event.occurred_at))} (Bogotá)
          </p>
          <p>
            {detail.link_review?.registered
              ? "Inscrito en SIIE · Sin promociones"
              : "Origen SIIE"}
          </p>
          <h5>Datos vigentes para revisar el vínculo</h5>
          <p>
            Se muestra la versión más reciente recibida para esta referencia. El
            recibo conserva el cambio original.
          </p>
          <p>
            Último cambio recibido de SIIE: {date(text(snapshot.occurred_at))}{" "}
            (Bogotá).
          </p>
          <dl className="siie-webhook-checks">
            <div>
              <dt>Nombre</dt>
              <dd>
                {[
                  person?.nombres,
                  person?.primerApellido,
                  person?.segundoApellido,
                ]
                  .map(text)
                  .filter(Boolean)
                  .join(" ") || "Sin nombre recibido"}
              </dd>
            </div>
            <div>
              <dt>Documento</dt>
              <dd>{text(snapshot.documento) || "Pendiente de corroborar"}</dd>
            </div>
            <div>
              <dt>Celular en SIIE</dt>
              <dd>{text(person?.celular) || "Sin teléfono recibido"}</dd>
            </div>
            <div>
              <dt>Correo</dt>
              <dd>{text(person?.correo) || "Sin correo recibido"}</dd>
            </div>
            <div>
              <dt>Ciudad</dt>
              <dd>{text(person?.ciudad) || "Sin ciudad recibida"}</dd>
            </div>
            <div>
              <dt>Programa y jornada</dt>
              <dd>
                {[snapshot.programa, snapshot.jornada]
                  .map(text)
                  .filter(Boolean)
                  .join(" · ") || "Sin detalle recibido"}
              </dd>
            </div>
            {[
              ["idPreinscripcion", "Preinscripción SIIE"],
              ["idEstudiante", "Estudiante SIIE"],
              ["idInscripcion", "Inscripción SIIE"],
              ["idOferta", "Oferta SIIE"],
              ["idPeriodo", "Período SIIE"],
            ].map(
              ([key, label]) =>
                snapshot[key] != null && (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>{text(snapshot[key])}</dd>
                  </div>
                ),
            )}
          </dl>
          {detail.link_review?.contact_id ? (
            <Notice>
              El vínculo con el contacto CRM ya está confirmado. La recepción no
              habilita envíos comerciales ni entrega de PDFs.
            </Notice>
          ) : detail.candidates.length > 0 ? (
            <section aria-label="Revisión del vínculo de SIIE">
              <p>
                Verifica los datos de SIIE frente al contacto. Compartir un
                teléfono o confirmar sólo el nombre no demuestra la identidad.
              </p>
              <SelectField
                id="siie-link-candidate"
                label="Contacto existente que corresponde a esta persona"
                value={candidateId}
                disabled={task.busy}
                options={[
                  { value: "", label: "Selecciona después de verificar" },
                  ...detail.candidates.map((v) => ({
                    value: v.id,
                    label: `${v.name} · ${v.phone}`,
                  })),
                ]}
                onChange={(e) => {
                  setCandidateId(e.target.value);
                  setReviewed(false);
                }}
              />
              <label>
                <input
                  type="checkbox"
                  checked={reviewed}
                  disabled={task.busy}
                  onChange={(e) => setReviewed(e.target.checked)}
                />{" "}
                Verifiqué que la inscripción y el contacto pertenecen a la misma
                persona
              </label>
              <Button
                disabled={
                  task.busy ||
                  !candidateId ||
                  !reviewed ||
                  !detail.link_review?.revision
                }
                onClick={() =>
                  void task.run(async () => {
                    await call(
                      `siie-registration/events/${eventId}/link`,
                      "POST",
                      {
                        contact_id: candidateId,
                        reviewed: true,
                        link_revision: detail.link_review!.revision,
                      },
                    );
                    await read();
                  }, "Vínculo de SIIE confirmado")
                }
              >
                Confirmar vínculo con el contacto
              </Button>
            </section>
          ) : (
            <Notice>
              Conserva este recibo para seguimiento. Si hace falta revisar la
              identidad, resuélvela con Admisiones antes de entregar información
              privada.
            </Notice>
          )}
          <div className="siie-registration-actions">
            <Button
              variant="quiet"
              disabled={task.busy}
              onClick={() =>
                void task.run(
                  () => open(eventId),
                  "Datos recibidos actualizados",
                )
              }
            >
              Actualizar datos recibidos
            </Button>
            <Button variant="quiet" disabled={task.busy} onClick={close}>
              Cerrar detalle del evento
            </Button>
          </div>
        </section>
      )}
    </section>
  );
}
