import { useEffect, useRef, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Field, Notice } from "../shared/ui";
import { useTask } from "./api";
import { ErrorFeedback } from "./ErrorFeedback";
import type { OperationFailure } from "./ErrorFeedback";
import "./siie.css";

type Row = Record<string, unknown>;
type SourceData = { data: Row; correlation_id?: string };
type Connection = {
  catalog_configured: boolean;
  admissions_configured: boolean;
};
const text = (v: unknown) =>
  v === null || v === undefined ? "Sin dato" : String(v);
const money = (v: unknown) =>
  typeof v === "number" && Number.isInteger(v)
    ? new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        maximumFractionDigits: 0,
      }).format(v)
    : "Por confirmar";
const list = (v: unknown): Row[] => (Array.isArray(v) ? (v as Row[]) : []);
const params = (values: Record<string, string>) => {
  const q = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v) q.set(k, v);
  });
  return q.toString();
};

function explainSiie(failure: OperationFailure) {
  return {
    title: "No se pudo consultar SIIE",
    detail: failure.message,
    nextStep: /configurad|clave|credencial/i.test(failure.message)
      ? "En Coolify, configura la URL HTTPS y la clave original del grupo correspondiente: Catálogo o Admisiones. Guarda las variables sólo en Runtime y redespliega el backend. No compartas la clave por el chat."
      : "Revisa el período y la referencia seleccionada. Si SIIE indica un límite, espera antes de consultar; si el aviso persiste, entrega la referencia de consulta al equipo de SIIE. Los datos locales se conservan.",
  };
}

export function SiieWorkspace() {
  return (
    <ErrorFeedback explain={explainSiie}>
      <SiieWorkspaceContent />
    </ErrorFeedback>
  );
}

function SiieWorkspaceContent() {
  const task = useTask();
  const epoch = useRef(0);
  const [opened, setOpened] = useState(false);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [tab, setTab] = useState("catalog");
  const [programs, setPrograms] = useState<Row | null>(null);
  const [programCursor, setProgramCursor] = useState<string[]>([""]);
  const [selectedProgram, setSelectedProgram] = useState("");
  const [offers, setOffers] = useState<Row | null>(null);
  const [offerCursor, setOfferCursor] = useState<string[]>([""]);
  const [inspection, setInspection] = useState<Row | null>(null);
  const [periods, setPeriods] = useState<Row | null>(null);
  const [period, setPeriod] = useState("");
  const [filters, setFilters] = useState<Row | null>(null);
  const [programFilter, setProgramFilter] = useState("");
  const [shift, setShift] = useState("");
  const [query, setQuery] = useState("");
  const [applied, setApplied] = useState<Record<string, string> | null>(null);
  const [applicants, setApplicants] = useState<Row | null>(null);
  const [applicant, setApplicant] = useState<Row | null>(null);
  const [history, setHistory] = useState<Row | null>(null);
  const [states, setStates] = useState<Row | null>(null);
  const [correlation, setCorrelation] = useState("");

  useEffect(
    () => () => {
      epoch.current++;
    },
    [],
  );
  const changeContext = () => {
    epoch.current++;
    setCorrelation("");
  };
  const load = (
    route: string,
    values: Record<string, string>,
    done: (row: Row) => void,
  ) => {
    const ticket = ++epoch.current;
    void task.run(async () => {
      try {
        const value = await api<SourceData>(`/siie/${route}?${params(values)}`);
        if (ticket !== epoch.current) return;
        done(value.data);
        setCorrelation(value.correlation_id ?? "");
      } catch (failure) {
        if (ticket === epoch.current) throw failure;
      }
    }, "");
  };
  const openPrograms = (cursor: string, stack: string[]) => {
    setOffers(null);
    setInspection(null);
    setSelectedProgram("");
    load("programs", { cursor }, (row) => {
      setPrograms(row);
      setProgramCursor(stack);
    });
  };
  const openOffers = (program: string, cursor = "", stack = [""]) => {
    setInspection(null);
    // Do not show the previous program's offers under the newly selected name.
    setOffers(null);
    setSelectedProgram(program);
    load("offers", { program_id: program, cursor }, (row) => {
      setOffers(row);
      setOfferCursor(stack);
    });
  };
  const search = (
    offset = "0",
    criteria: Record<string, string> = {
      idPeriodo: period,
      idPrograma: programFilter,
      idJornada: shift,
      q: query,
    },
  ) => {
    setApplicant(null);
    setHistory(null);
    load("applicants", { ...criteria, offset }, (row) => {
      setApplicants(row);
      setApplied(criteria);
    });
  };

  return (
    <section className="siie-workspace panel" aria-label="Integración SIIE">
      <div className="siie-heading">
        <div>
          <h2>SIIE</h2>
          <p>Consulta académica y financiera desde la fuente institucional.</p>
        </div>
        <Button
          type="button"
          variant="secondary"
          aria-expanded={opened}
          onClick={() => {
            changeContext();
            setOpened(!opened);
          }}
        >
          {opened ? "Ocultar SIIE" : "Abrir SIIE"}
        </Button>
      </div>
      {opened && (
        <>
          <p>
            Las consultas no matriculan, no cobran y no modifican SIIE. Los
            datos incompletos se conservan para revisión.
          </p>
          {task.notices}
          <Button
            type="button"
            disabled={task.busy}
            variant="secondary"
            onClick={() => {
              const ticket = ++epoch.current;
              void task.run(async () => {
                try {
                  const result = await api<Connection>("/siie/status");
                  if (ticket === epoch.current) setConnection(result);
                } catch (failure) {
                  if (ticket === epoch.current) throw failure;
                }
              }, "");
            }}
          >
            Comprobar conexión configurada
          </Button>
          {connection && (
            <div className="siie-connections" role="status">
              <span>
                Catálogo:{" "}
                {connection.catalog_configured
                  ? "clave configurada"
                  : "falta clave"}
              </span>
              <span>
                Admisiones:{" "}
                {connection.admissions_configured
                  ? "clave configurada"
                  : "falta clave"}
              </span>
              <p>
                Una clave configurada requiere todavía una consulta correcta
                para validar el acceso.
              </p>
            </div>
          )}
          <nav className="siie-tabs" aria-label="Datos de SIIE">
            {[
              ["catalog", "Programas y finanzas"],
              ["admissions", "Aspirantes y seguimiento"],
              ["pending", "Estudiantes y cartera"],
            ].map(([id, label]) => (
              <Button
                type="button"
                key={id}
                variant="secondary"
                aria-pressed={tab === id}
                onClick={() => {
                  changeContext();
                  setTab(id);
                }}
              >
                {label}
              </Button>
            ))}
          </nav>
          <fieldset disabled={task.busy} aria-busy={task.busy}>
            {tab === "catalog" && (
              <>
                <Button type="button" onClick={() => openPrograms("", [""])}>
                  Obtener programas de SIIE
                </Button>
                {programs && (
                  <div className="siie-split">
                    <div>
                      <h3>Programas oficiales</h3>
                      <ul className="siie-list">
                        {list(programs.items).map((p, i) => (
                          <li key={text(p.program_id) + i}>
                            <Button
                              type="button"
                              variant="secondary"
                              disabled={!p.program_id}
                              aria-pressed={
                                selectedProgram === text(p.program_id)
                              }
                              onClick={() => openOffers(text(p.program_id))}
                            >
                              <strong>{text(p.name)}</strong>
                              <span>
                                {text(p.code)} · {text(p.school)}
                              </span>
                              <span>
                                {text(p.schedule)} · {text(p.modality)} ·{" "}
                                {text(p.duration_levels)} niveles
                              </span>
                            </Button>
                          </li>
                        ))}
                      </ul>
                      {!list(programs.items).length && (
                        <p>No hay programas en esta página.</p>
                      )}
                      <div className="siie-pagination">
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={programCursor.length < 2}
                          onClick={() => {
                            const s = programCursor.slice(0, -1);
                            openPrograms(s[s.length - 1], s);
                          }}
                        >
                          Programas anteriores
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={!programs.next_cursor}
                          onClick={() =>
                            openPrograms(text(programs.next_cursor), [
                              ...programCursor,
                              text(programs.next_cursor),
                            ])
                          }
                        >
                          Más programas
                        </Button>
                      </div>
                    </div>
                    <div>
                      <h3>Ofertas por período y nivel</h3>
                      {!offers && (
                        <p>
                          Selecciona un programa para consultar sus ofertas.
                        </p>
                      )}
                      <ul className="siie-list">
                        {list(offers?.items).map((o, i) => (
                          <li key={text(o.offer_id) + i}>
                            <Button
                              type="button"
                              variant="secondary"
                              disabled={!o.offer_id}
                              onClick={() => {
                                setInspection(null);
                                load(
                                  "offer",
                                  { offer_id: text(o.offer_id) },
                                  setInspection,
                                );
                              }}
                            >
                              <strong>
                                {text(o.period_name)} · Nivel {text(o.level)}
                              </strong>
                              <span>
                                {text(o.schedule)} · Oferta {text(o.offer_id)}
                              </span>
                              <span>
                                {o.quotable === true
                                  ? "Requiere revisión"
                                  : "Cotización pendiente de completar"}
                              </span>
                            </Button>
                          </li>
                        ))}
                      </ul>
                      {offers && !list(offers.items).length && (
                        <p>Sin ofertas para este programa.</p>
                      )}
                      {offers && (
                        <div className="siie-pagination">
                          <Button
                            type="button"
                            variant="secondary"
                            disabled={offerCursor.length < 2}
                            onClick={() => {
                              const s = offerCursor.slice(0, -1);
                              openOffers(selectedProgram, s[s.length - 1], s);
                            }}
                          >
                            Ofertas anteriores
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            disabled={!offers.next_cursor}
                            onClick={() =>
                              openOffers(
                                selectedProgram,
                                text(offers.next_cursor),
                                [...offerCursor, text(offers.next_cursor)],
                              )
                            }
                          >
                            Más ofertas
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                {inspection && <OfferInspection inspection={inspection} />}
              </>
            )}
            {tab === "admissions" && (
              <>
                <Button
                  type="button"
                  onClick={() =>
                    load("periods", {}, (row) => {
                      setPeriods(row);
                      setPeriod(
                        row.requiereSeleccion === false && row.idPeriodoActivo
                          ? text(row.idPeriodoActivo)
                          : "",
                      );
                      setFilters(null);
                      setApplicants(null);
                      setApplicant(null);
                      setHistory(null);
                      setApplied(null);
                    })
                  }
                >
                  Obtener períodos de admisiones
                </Button>
                {periods && (
                  <>
                    <label>
                      Período de aspirantes
                      <select
                        value={period}
                        onChange={(e) => {
                          changeContext();
                          setPeriod(e.target.value);
                          setFilters(null);
                          setProgramFilter("");
                          setShift("");
                          setApplicants(null);
                          setApplicant(null);
                          setHistory(null);
                          setApplied(null);
                        }}
                      >
                        <option value="">Seleccionar período</option>
                        {list(periods.items).map((p) => (
                          <option key={text(p.id)} value={text(p.id)}>
                            {text(p.nombre)}
                            {p.activo === true ? " · Activo" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={!period}
                      onClick={() =>
                        load("filters", { idPeriodo: period }, setFilters)
                      }
                    >
                      Obtener programas y jornadas del período
                    </Button>
                    <div className="siie-filter-row">
                      <label>
                        Programa de aspirantes
                        <select
                          value={programFilter}
                          onChange={(e) => setProgramFilter(e.target.value)}
                        >
                          <option value="">Todos</option>
                          {Array.from(
                            new Map(
                              list(filters?.items)
                                .filter((p) => p.idPrograma)
                                .map((p) => [text(p.idPrograma), p]),
                            ).values(),
                          ).map((p) => (
                            <option
                              key={text(p.idPrograma)}
                              value={text(p.idPrograma)}
                            >
                              {text(p.programa)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Jornada del programa
                        <select
                          value={shift}
                          onChange={(e) => setShift(e.target.value)}
                        >
                          <option value="">Todas</option>
                          {Array.from(
                            new Map(
                              list(filters?.items)
                                .filter((p) => p.idJornada)
                                .map((p) => [text(p.idJornada), p]),
                            ).values(),
                          ).map((p) => (
                            <option
                              key={text(p.idJornada)}
                              value={text(p.idJornada)}
                            >
                              {text(p.jornada)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <Field
                        id="siie-search"
                        label="Buscar aspirante"
                        maxLength={100}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                      <Button
                        type="button"
                        disabled={!period}
                        onClick={() => search()}
                      >
                        Buscar en SIIE
                      </Button>
                    </div>
                  </>
                )}
                {applicants && (
                  <div className="siie-split">
                    <div>
                      <h3>Aspirantes del período consultado</h3>
                      <ul className="siie-list">
                        {list(applicants.items).map((p) => (
                          <li key={text(p.idAspirante)}>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() => {
                                setApplicant(null);
                                setHistory(null);
                                load(
                                  "applicant",
                                  {
                                    idPeriodo: text(p.idPeriodo),
                                    idAspirante: text(p.idAspirante),
                                  },
                                  setApplicant,
                                );
                              }}
                            >
                              <strong>{text(p.nombre)}</strong>
                              <span>
                                {text(p.programa)} · {text(p.jornadaPrograma)}
                              </span>
                              <span>{text(p.estadoSeguimiento)}</span>
                            </Button>
                          </li>
                        ))}
                      </ul>
                      {!list(applicants.items).length && (
                        <p>No hay aspirantes con estos filtros.</p>
                      )}
                      <div className="siie-pagination">
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={Number(applicants.offset) === 0}
                          onClick={() =>
                            search(
                              String(
                                Math.max(0, Number(applicants.offset) - 25),
                              ),
                              applied!,
                            )
                          }
                        >
                          Aspirantes anteriores
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={applicants.hasMore !== true}
                          onClick={() =>
                            search(
                              String(Number(applicants.offset) + 25),
                              applied!,
                            )
                          }
                        >
                          Más aspirantes
                        </Button>
                      </div>
                    </div>
                    <div>
                      {applicant && (
                        <>
                          <h3>{text((applicant.aspirante as Row)?.nombre)}</h3>
                          <DataFields
                            row={applicant.aspirante as Row}
                            labels={{
                              programa: "Programa",
                              periodo: "Período del aspirante",
                              periodoOferta: "Período de la oferta",
                              jornadaPrograma: "Jornada del programa",
                              estadoSeguimiento:
                                "Último resultado de seguimiento",
                              fechaRegistro: "Fecha de registro",
                            }}
                          />
                          <Notice>
                            La confirmación de origen no acredita matrícula.
                            SIIE no entrega teléfono, documento ni correo en
                            esta ficha.
                          </Notice>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() =>
                              load(
                                "history",
                                {
                                  idPeriodo: text(
                                    (applicant.aspirante as Row).idPeriodo,
                                  ),
                                  idAspirante: text(
                                    (applicant.aspirante as Row).idAspirante,
                                  ),
                                  offset: "0",
                                },
                                setHistory,
                              )
                            }
                          >
                            Consultar historial de seguimiento
                          </Button>
                        </>
                      )}
                      {history && (
                        <>
                          <h4>Historial</h4>
                          <ol>
                            {list(history.items).map((p) => (
                              <li key={text(p.idSeguimiento)}>
                                <strong>{text(p.estado)}</strong>
                                <p>{text(p.observacion)}</p>
                                <small>
                                  {text(p.fechaSeguimiento)} ·{" "}
                                  {text(p.autorCrmNombre ?? p.usuarioOrigen)}
                                  {p.observacionTruncada === true
                                    ? " · Nota recortada en origen"
                                    : ""}
                                </small>
                              </li>
                            ))}
                          </ol>
                          {!list(history.items).length && (
                            <p>Sin seguimientos en esta página.</p>
                          )}
                          <div className="siie-pagination">
                            {[-25, 25].map((step) => (
                              <Button
                                key={step}
                                type="button"
                                variant="secondary"
                                disabled={
                                  step < 0
                                    ? Number(history.offset) === 0
                                    : history.hasMore !== true
                                }
                                onClick={() =>
                                  load(
                                    "history",
                                    {
                                      idPeriodo: text(
                                        (applicant!.aspirante as Row).idPeriodo,
                                      ),
                                      idAspirante: text(
                                        (applicant!.aspirante as Row)
                                          .idAspirante,
                                      ),
                                      offset: String(
                                        Number(history.offset) + step,
                                      ),
                                    },
                                    setHistory,
                                  )
                                }
                              >
                                {step < 0
                                  ? "Seguimientos anteriores"
                                  : "Más seguimientos"}
                              </Button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => load("states", {}, setStates)}
                >
                  Consultar estados de seguimiento oficiales
                </Button>
                {states && (
                  <ul>
                    {list(states.items).map((p) => (
                      <li key={text(p.id)}>
                        {text(p.nombre)} · {text(p.id)}
                      </li>
                    ))}
                  </ul>
                )}
                <p>
                  El registro y la corrección de seguimientos en SIIE requieren
                  una revisión antes de habilitar escrituras. Los estados de
                  seguimiento no son estados de matrícula.
                </p>
              </>
            )}
            {tab === "pending" && (
              <Notice>
                La API recibida todavía no expone estudiantes matriculados,
                matrículas, recibos, pagos ni saldos individuales. Para
                habilitarlos necesitamos sus rutas, IDs estables, permisos y
                reglas de actualización. No se deducen del estado de un
                aspirante.
              </Notice>
            )}
          </fieldset>
          {task.busy && <p role="status">Consultando SIIE…</p>}
          {correlation && <small>Referencia de consulta: {correlation}</small>}
        </>
      )}
    </section>
  );
}

function DataFields({
  row,
  labels,
}: {
  row: Row;
  labels: Record<string, string>;
}) {
  return (
    <dl className="siie-facts">
      {Object.entries(labels).map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>{text(row?.[key])}</dd>
        </div>
      ))}
    </dl>
  );
}

function OfferInspection({ inspection }: { inspection: Row }) {
  const offer = inspection.offer as Row;
  const commercial = (offer.commercial ?? {}) as Row;
  return (
    <article className="siie-offer" aria-label="Revisión de oferta SIIE">
      <h3>
        {text(offer.name)} · Nivel {text(offer.level)}
      </h3>
      <Notice>
        {inspection.quotable === true
          ? "Oferta recibida para revisión humana."
          : "Oferta incompleta: no disponible para cotizar ni para publicar precios en Gemini."}{" "}
        No se ha guardado ni aplicado al catálogo de agentes.
      </Notice>
      <ul>
        {list(inspection.data_quality).map((q, i) => (
          <li key={i}>
            <strong>{text(q.field)}</strong>: {text(q.message)}
          </li>
        ))}
      </ul>
      <DataFields
        row={offer}
        labels={{
          period_name: "Período",
          school: "Escuela",
          schedule: "Jornada",
          campus_id: "Sede",
          academic_start: "Inicio académico",
          academic_end: "Fin académico",
        }}
      />
      <DataFields
        row={commercial}
        labels={{
          duration: "Duración informada",
          modality: "Modalidad",
          requirements: "Requisitos de admisión",
          syllabus: "Materias del nivel",
          price_concept: "Concepto de precio",
          price_valid_from: "Vigencia comercial desde",
          price_valid_until: "Vigencia comercial hasta",
          cost_inclusions: "Incluye",
          cost_exclusions: "No incluye",
        }}
      />
      <p>
        <strong>Enseñanza del semestre o nivel:</strong>{" "}
        {money(commercial.price_cop)}
      </p>
      <p>
        El valor ordinario y el campo de contado de esta fuente cubren la
        enseñanza del nivel. No representan el costo de todo el programa ni
        incluyen extras sin valorar.
      </p>
      <p>
        Contado informado para el nivel: {money(commercial.full_cost_cash_cop)}.
      </p>
      {list(commercial.syllabus_details).length > 0 && (
        <details>
          <summary>Detalle de materias del nivel</summary>
          <p>
            El orden por identificador no representa la secuencia curricular
            oficial.
          </p>
          <pre className="siie-source-detail">
            {JSON.stringify(commercial.syllabus_details, null, 2)}
          </pre>
        </details>
      )}
      <h4>Planes financieros de origen</h4>
      {list(commercial.financial_plans)
        .filter((p) => p && typeof p === "object")
        .map((p, i) => (
          <section key={text(p.external_id) + i}>
            <h4>{text(p.name)}</h4>
            <p>
              Abono: {money(p.initial_payment_cop)} · Fecha:{" "}
              {text(p.initial_payment_due_date)}
            </p>
            <p>
              Suma del calendario: {money(p.total_cost_cop)} · Condiciones:{" "}
              {text(p.conditions)}
            </p>
            <p>
              Calendario validado por SIIE:{" "}
              {p.schedule_valid === true
                ? "Sí"
                : p.schedule_valid === false
                  ? "No; requiere revisión"
                  : "Por confirmar"}
              . Valor de contado asociado: {money(p.cash_price_cop)}.
            </p>
            {Boolean(p.source_prices_cop) &&
              typeof p.source_prices_cop === "object" && (
                <dl className="siie-facts">
                  {Object.entries({
                    pronto_pago: "Pronto pago de origen",
                    pago_oportuno: "Pago oportuno de origen",
                    extraordinaria: "Extraordinaria de origen",
                  }).map(([key, label]) => (
                    <div key={key}>
                      <dt>{label}</dt>
                      <dd>{money((p.source_prices_cop as Row)[key])}</dd>
                    </div>
                  ))}
                </dl>
              )}
            <p>
              Fecha de pago de origen: {text(p.source_payment_date)}. Esta fecha
              no acredita vigencia comercial.
            </p>
            <div className="siie-table">
              <table>
                <caption>Cuotas almacenadas en SIIE</caption>
                <thead>
                  <tr>
                    <th>Cuota</th>
                    <th>Valor COP</th>
                    <th>Vencimiento</th>
                  </tr>
                </thead>
                <tbody>
                  {list(p.installments).map((v, j) => (
                    <tr key={j}>
                      <td>{text(v.number)}</td>
                      <td>{money(v.amount_cop)}</td>
                      <td>{text(v.due_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Vigencia: {text(p.valid_from)} — {text(p.valid_until)}. Las fechas
              históricas no se regeneran.
            </p>
            <small>
              Plan {text(p.external_id)} · Tarifa {text(p.source_tariff_id)} ·
              Tipo {text(p.source_plan_type)}
            </small>
          </section>
        ))}
      {!list(commercial.financial_plans).filter(Boolean).length && (
        <p>No hay planes completos disponibles.</p>
      )}
      <small>
        Oferta {text(offer.offer_id)} · Revisión {text(offer.source_revision)} ·
        Generado {text(offer.generated_at)}
      </small>
    </article>
  );
}
