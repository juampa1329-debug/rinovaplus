import { useEffect, useRef, useState } from "react";
import { useWorkspaceState } from "../../../shared/workspaceSession";
import type { AdmissionDraft } from "../../../shared/workspaceSession";
import { Icon } from "../../../shared/Icon";
import "../../../institution/operations-design.css";
import { admissionsApi, AdmissionsError } from "../api/admissionsApi";
import type {
  AdmissionPage,
  AdmissionPeriod,
  AdmissionState,
  AdmissionFilterOption,
  Applicant,
  ApplicantDetail,
  Followup,
  FollowupInput,
} from "../api/admissionsApi";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../../shared/ui";

function Pagination({
  page,
  onChange,
  label,
}: {
  page: AdmissionPage<unknown>;
  onChange: (offset: number) => void;
  label: string;
}) {
  return (
    <nav className="admissions-pagination" aria-label={label}>
      <Button
        variant="secondary"
        disabled={page.offset === 0}
        onClick={() => onChange(Math.max(0, page.offset - page.limit))}
      >
        Anterior
      </Button>
      <span>
        Página {Math.floor(page.offset / page.limit) + 1} · {page.items.length}{" "}
        registros
      </span>
      <Button
        variant="secondary"
        disabled={!page.hasMore}
        onClick={() => onChange(page.offset + page.limit)}
      >
        Siguiente
      </Button>
    </nav>
  );
}

export function Admissions() {
  const [catalog, setCatalog] = useState<{
    items: AdmissionPeriod[];
    activePeriodId: number | null;
    selectionRequired: boolean;
  } | null>(null);
  const [states, setStates] = useState<AdmissionState[]>([]);
  const [period, setPeriod] = useState("");
  const [query, setQuery] = useState("");
  const [program, setProgram] = useState("");
  const [schedule, setSchedule] = useState("");
  const [filterOptions, setFilterOptions] = useState<{
    period: string;
    items: AdmissionFilterOption[];
    error: boolean;
  } | null>(null);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Applicant | null>(null);
  const [list, setList] = useState<{
    key: string;
    page: AdmissionPage<Applicant>;
  } | null>(null);
  const [error, setError] = useState("");
  const [catalogError, setCatalogError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const key = JSON.stringify([
    period,
    query,
    program,
    schedule,
    offset,
    refresh,
  ]);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      admissionsApi.periods(controller.signal),
      admissionsApi.states(controller.signal),
    ])
      .then(([result, status]) => {
        if (controller.signal.aborted) return;
        setCatalog(result);
        setStates(status.items);
        setCatalogError("");
        setPeriod(
          (current) =>
            current ||
            (result.activePeriodId === null
              ? ""
              : String(result.activePeriodId)),
        );
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setCatalogError(
            "No se pudieron cargar los períodos y estados de SIIE.",
          );
      });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    if (!period) return;
    const controller = new AbortController();
    void admissionsApi
      .filters(Number(period), controller.signal)
      .then((result) => {
        if (!controller.signal.aborted)
          setFilterOptions({ period, items: result.items, error: false });
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setFilterOptions({ period, items: [], error: true });
      });
    return () => controller.abort();
  }, [period, refresh]);
  useEffect(() => {
    if (!period) return;
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => {
        void admissionsApi
          .applicants(Number(period), query.trim(), offset, controller.signal, {
            ...(program ? { programId: Number(program) } : {}),
            ...(schedule ? { scheduleId: Number(schedule) } : {}),
          })
          .then((result) => {
            if (!controller.signal.aborted) {
              setList({ key, page: result });
              setError("");
            }
          })
          .catch(() => {
            if (!controller.signal.aborted) {
              setList({
                key,
                page: { items: [], offset, limit: 25, hasMore: false },
              });
              setError(
                "No se pudieron consultar los aspirantes. No se muestran datos de otro período.",
              );
            }
          });
      },
      query.trim() ? 300 : 0,
    );
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [period, query, program, schedule, offset, key]);

  const ready = list?.key === key;
  const options = filterOptions?.period === period ? filterOptions.items : [];
  const programOptions = [
    ...new Map(
      options.map((item) => [
        item.programId,
        {
          value: String(item.programId),
          label: item.program || `Programa #${item.programId}`,
        },
      ]),
    ).values(),
  ];
  const scheduleOptions = [
    ...new Map(
      options
        .filter((item) => item.scheduleId !== null)
        .map((item) => [
          item.scheduleId,
          {
            value: String(item.scheduleId),
            label: item.schedule || `Jornada #${item.scheduleId}`,
          },
        ]),
    ).values(),
  ];
  function resetPage() {
    setOffset(0);
    setSelected(null);
    setError("");
  }
  function choosePeriod(value: string) {
    setPeriod(value);
    setProgram("");
    setSchedule("");
    resetPage();
  }
  return (
    <div className="admissions-workspace">
      <header className="operations-hero admissions-hero">
        <div>
          <span className="operations-eyebrow">
            DE LA PRIMERA PREGUNTA AL SIGUIENTE PASO
          </span>
          <h2>Admisiones, con contexto.</h2>
          <p>
            Encuentra al aspirante, revisa su programa y acompaña su proceso.
          </p>
        </div>
        <span className="operations-source">
          <Icon name="admissions" /> Fuente institucional · SIIE
        </span>
      </header>
      <section
        className="panel admissions-filters"
        aria-label="Filtros de admisiones"
      >
        <div className="operations-section-heading">
          <div>
            <span className="operations-eyebrow">ENCUENTRA A LA PERSONA</span>
            <h2>Explorar aspirantes</h2>
          </div>
          <span className="operations-live">Consulta por período</span>
        </div>
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            resetPage();
            setRefresh((value) => value + 1);
          }}
        >
          <SelectField
            id="admissions-period"
            label="Período al que aspira"
            value={period}
            onChange={(event) => choosePeriod(event.target.value)}
            options={[
              { value: "", label: "Seleccione un período" },
              ...(catalog?.items ?? []).map((item) => ({
                value: String(item.id),
                label: `${item.label}${item.active ? " · Activo en SIIE" : ""}`,
              })),
            ]}
          />
          <Field
            id="admissions-search"
            label="Buscar aspirante"
            placeholder="Nombre o documento"
            value={query}
            maxLength={100}
            onChange={(event) => {
              setQuery(event.target.value);
              resetPage();
            }}
          />
          <SelectField
            id="admissions-program"
            label="Programa del aspirante"
            value={program}
            disabled={!period || filterOptions?.period !== period}
            options={[
              { value: "", label: "Todos los programas" },
              ...programOptions,
            ]}
            onChange={(event) => {
              setProgram(event.target.value);
              resetPage();
            }}
          />
          <SelectField
            id="admissions-schedule"
            label="Jornada del programa"
            value={schedule}
            disabled={!period || filterOptions?.period !== period}
            options={[
              { value: "", label: "Todas las jornadas" },
              ...scheduleOptions,
            ]}
            onChange={(event) => {
              setSchedule(event.target.value);
              resetPage();
            }}
          />
          <div className="actions">
            <Button type="submit" disabled={!period}>
              Buscar
            </Button>
            <Button
              variant="quiet"
              onClick={() => {
                setQuery("");
                setProgram("");
                setSchedule("");
                setOffset(0);
                setSelected(null);
                setError("");
                setRefresh((value) => value + 1);
              }}
            >
              Restablecer filtros
            </Button>
          </div>
        </form>
        <p className="admissions-hint">
          El filtro utiliza el período registrado en el aspirante. La oferta
          académica puede pertenecer a otro período y se muestra por separado.
          La jornada corresponde al programa; no confirma una jornada asignada
          al aspirante.
        </p>
        {filterOptions?.period === period && filterOptions.error && (
          <Notice error>
            No se pudieron cargar los programas y jornadas del período.
            <Button
              variant="secondary"
              onClick={() => setRefresh((value) => value + 1)}
            >
              Reintentar filtros
            </Button>
          </Notice>
        )}
        {catalogError && (
          <Notice error>
            {catalogError}{" "}
            <Button
              variant="secondary"
              onClick={() => setRefresh((value) => value + 1)}
            >
              Reintentar catálogos
            </Button>
          </Notice>
        )}
        {catalog?.selectionRequired && !period && (
          <Notice>
            SIIE no tiene un único período activo. Seleccione el período que
            desea consultar.
          </Notice>
        )}
      </section>
      {!period && (
        <EmptyState
          title={catalog ? "Seleccione un período" : "Cargando períodos…"}
        >
          La consulta de aspirantes comienza después de elegir un período.
        </EmptyState>
      )}
      {period && (
        <div className={`admissions-grid${selected ? " has-detail" : ""}`}>
          <section
            className="panel admissions-list"
            aria-label="Aspirantes del período"
          >
            <div className="panel-heading">
              <h2>
                Aspirantes ·{" "}
                {
                  catalog?.items.find((item) => String(item.id) === period)
                    ?.label
                }
              </h2>
              <Badge>SIIE</Badge>
            </div>
            {!ready && <Notice>Consultando aspirantes…</Notice>}
            {ready && !error && (
              <p className="admissions-result-count">
                {list.page.items.length} aspirantes en esta página
                {list.page.hasMore ? " · Hay más resultados" : ""}
              </p>
            )}
            {ready && error && (
              <Notice error>
                {error}{" "}
                <Button
                  variant="secondary"
                  onClick={() => setRefresh((value) => value + 1)}
                >
                  Reintentar aspirantes
                </Button>
              </Notice>
            )}
            {ready && !error && list.page.items.length === 0 && (
              <EmptyState title="Sin resultados">
                No hay aspirantes para este período y búsqueda.
              </EmptyState>
            )}
            {ready && !error && (
              <>
                <ul className="record-list">
                  {list.page.items.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={`record${selected?.id === item.id ? " selected" : ""}`}
                        aria-pressed={selected?.id === item.id}
                        onClick={() => setSelected(item)}
                      >
                        <strong>{item.name}</strong>
                        <span>{item.program || "Sin programa asociado"}</span>
                        <small>
                          Aspirante #{item.id} · {item.period}
                          {item.offerPeriodId !== item.periodId
                            ? " · Revisar período de oferta"
                            : ""}
                        </small>
                      </button>
                    </li>
                  ))}
                </ul>
                <Pagination
                  label="Páginas de aspirantes"
                  page={list.page}
                  onChange={(value) => {
                    setOffset(value);
                    setSelected(null);
                  }}
                />
              </>
            )}
          </section>
          {selected && (
            <ApplicantPanel
              key={`${period}/${selected.id}`}
              applicant={selected}
              periodId={Number(period)}
              states={states}
              onClose={() => setSelected(null)}
            />
          )}
          {!selected && (
            <section className="panel admissions-welcome">
              <Icon name="user" />
              <span className="operations-eyebrow">CADA HISTORIA IMPORTA</span>
              <h2>Conoce a tu próximo estudiante</h2>
              <p>
                Selecciona un aspirante para ver su información, programa y
                seguimientos, sin perder el contexto de tu búsqueda.
              </p>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function ApplicantPanel({
  applicant,
  periodId,
  states,
  onClose,
}: {
  applicant: Applicant;
  periodId: number;
  states: AdmissionState[];
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<ApplicantDetail | null>(null);
  const [detailError, setDetailError] = useState("");
  const [matchOffset, setMatchOffset] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [detailKey, setDetailKey] = useState("");
  const key = `${applicant.id}/${periodId}/${matchOffset}/${historyOffset}/${reload}`;
  useEffect(() => {
    const controller = new AbortController();
    void admissionsApi
      .detail(
        applicant.id,
        periodId,
        matchOffset,
        historyOffset,
        controller.signal,
      )
      .then((result) => {
        if (!controller.signal.aborted) {
          setDetail(result);
          setDetailKey(key);
          setDetailError("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setDetailError("No se pudo cargar la ficha. Intente nuevamente.");
          setDetailKey(key);
        }
      });
    return () => controller.abort();
  }, [applicant.id, periodId, matchOffset, historyOffset, key]);
  return (
    <section
      className="panel admissions-detail"
      aria-label="Ficha del aspirante"
    >
      <div className="panel-heading">
        <div>
          <h2>{applicant.name}</h2>
          <p>Aspirante SIIE #{applicant.id}</p>
        </div>
        <Button variant="quiet" onClick={onClose}>
          Cerrar ficha
        </Button>
      </div>
      {detailKey !== key && <Notice>Cargando ficha…</Notice>}
      {detailKey === key && detailError && (
        <Notice error>
          {detailError}
          <Button
            variant="secondary"
            onClick={() => setReload((value) => value + 1)}
          >
            Reintentar ficha
          </Button>
        </Notice>
      )}
      {detailKey === key && !detailError && detail && (
        <>
          <dl className="admissions-facts">
            <div>
              <dt>Documento · tipo {detail.applicant.documentTypeId}</dt>
              <dd>{detail.applicant.document || "Sin documento"}</dd>
            </div>
            <div>
              <dt>Contacto</dt>
              <dd>
                {detail.applicant.mobile ||
                  detail.applicant.phone ||
                  "Sin teléfono"}
              </dd>
            </div>
            <div>
              <dt>Correo</dt>
              <dd>{detail.applicant.email || "Sin correo"}</dd>
            </div>
            <div>
              <dt>Período aspirado</dt>
              <dd>{detail.applicant.period}</dd>
            </div>
            <div>
              <dt>Oferta registrada</dt>
              <dd>
                {detail.applicant.offerId === null
                  ? "Sin oferta"
                  : `#${detail.applicant.offerId} · ${detail.applicant.offerPeriod || "Sin período"}`}
              </dd>
            </div>
            <div>
              <dt>Programa</dt>
              <dd>{detail.applicant.program || "Sin programa"}</dd>
            </div>
            <div>
              <dt>Jornada del programa</dt>
              <dd>
                {detail.applicant.programSchedule || "Sin jornada registrada"}
              </dd>
            </div>
            <div>
              <dt>Jornadas asociadas a la oferta</dt>
              <dd>
                {detail.schedules.length
                  ? detail.schedules.map((item) => item.label).join(", ")
                  : "Sin relaciones registradas"}
              </dd>
            </div>
          </dl>
          {detail.applicant.offerPeriodId !== periodId && (
            <Notice>
              El período de la oferta{" "}
              {detail.applicant.offerPeriod || "no está registrado"}. El filtro
              sigue utilizando {detail.applicant.period}, período del aspirante.
            </Notice>
          )}
          <section
            className="admissions-section"
            aria-label="Coincidencias de estudiantes"
          >
            <h3>Estudiantes existentes</h3>
            <p>
              Coincidencias de tipo y documento en todos los períodos. Son
              candidatos para revisión; no se fusionan personas ni se crea una
              matrícula.
            </p>
            {!detail.matchingAvailable ? (
              <Notice>
                Documento o tipo de identificación incompleto: no se buscaron
                coincidencias.
              </Notice>
            ) : detail.matches.items.length === 0 ? (
              <p>No se encontraron coincidencias exactas en esta consulta.</p>
            ) : (
              <ul className="admissions-history">
                {detail.matches.items.map((item) => (
                  <li key={item.id}>
                    <strong>{item.name}</strong>
                    <p>
                      Estudiante #{item.id} ·{" "}
                      {item.period || "Período no disponible"}
                    </p>
                    <p>
                      {item.program || "Programa no disponible"} · Oferta #
                      {item.offerId}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            {(detail.matches.hasMore || detail.matches.offset > 0) && (
              <Pagination
                label="Páginas de coincidencias"
                page={detail.matches}
                onChange={setMatchOffset}
              />
            )}
          </section>
          <section
            className="admissions-section"
            aria-label="Seguimiento histórico SIIE"
          >
            <h3>Historial SIIE</h3>
            <p>
              Registros existentes de solo lectura. Sus estados no acreditan
              matrícula académica.
            </p>
            {detail.history.items.length === 0 ? (
              <p>No hay seguimiento histórico registrado.</p>
            ) : (
              <ul className="admissions-history">
                {detail.history.items.map((item) => (
                  <li key={item.id}>
                    <strong>
                      {item.state || `Estado ${item.stateId}`} ·{" "}
                      {item.date || "Sin fecha"}
                    </strong>
                    <p className="admissions-note">{item.body}</p>
                    {item.truncated && (
                      <small>
                        Vista limitada a los primeros 4.000 caracteres.
                      </small>
                    )}
                    {item.dueDate && (
                      <small>Próximo seguimiento: {item.dueDate}</small>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {(detail.history.hasMore || detail.history.offset > 0) && (
              <Pagination
                label="Páginas de historial SIIE"
                page={detail.history}
                onChange={setHistoryOffset}
              />
            )}
          </section>
        </>
      )}
      <Followups
        applicantId={applicant.id}
        periodId={periodId}
        states={states}
      />
    </section>
  );
}

function Followups({
  applicantId,
  periodId,
  states,
}: {
  applicantId: number;
  periodId: number;
  states: AdmissionState[];
}) {
  const [page, setPage] = useState<AdmissionPage<Followup> | null>(null);
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [session, setSession] = useWorkspaceState("admissions");
  const draftKey = `${periodId}/${applicantId}`;
  const draft = session.drafts[draftKey] ?? {
    body: "",
    state: "",
    due: "",
    editing: null,
    attempt: null,
  };
  const { body, state, due, editing } = draft;
  function updateDraft(changes: Partial<AdmissionDraft>) {
    setSession((previous) => ({
      ...previous,
      drafts: {
        ...previous.drafts,
        [draftKey]: { ...draft, ...previous.drafts[draftKey], ...changes },
      },
    }));
  }
  const setBody = (value: string) => updateDraft({ body: value });
  const setState = (value: string) => updateDraft({ state: value });
  const setDue = (value: string) => updateDraft({ due: value });
  const setEditing = (value: Followup | null) =>
    updateDraft({ editing: value });
  const [busy, setBusy] = useState(false);
  const attempt = useRef<{
    key: string;
    id: string;
    input: FollowupInput;
  } | null>(draft.attempt);
  const readSequence = useRef(0);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const sequence = ++readSequence.current;
    void admissionsApi
      .followups(applicantId, periodId, offset, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && sequence === readSequence.current) {
          setPage(result);
          setError("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted && sequence === readSequence.current)
          setError("No se pudieron cargar los seguimientos CRM.");
      });
    return () => controller.abort();
  }, [applicantId, periodId, offset, reload]);
  function reset() {
    setSession((previous) => ({
      ...previous,
      drafts: {
        ...previous.drafts,
        [draftKey]: {
          body: "",
          state: "",
          due: "",
          editing: null,
          attempt: null,
        },
      },
    }));
    attempt.current = null;
  }
  async function save() {
    if (!body.trim() || !state || busy) return;
    const key = JSON.stringify([
      editing?.id,
      editing?.revision,
      body.trim(),
      state,
      due,
    ]);
    if (attempt.current?.key !== key)
      attempt.current = {
        key,
        id: editing?.id ?? crypto.randomUUID(),
        input: {
          operationId: crypto.randomUUID(),
          expectedRevision: editing?.revision ?? 0,
          body: body.trim(),
          stateId: Number(state),
          dueDate: due || null,
        },
      };
    const current = attempt.current;
    updateDraft({ attempt: current });
    readSequence.current += 1;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await admissionsApi.save(
        applicantId,
        periodId,
        current.id,
        current.input,
        !editing,
      );
      setSession((previous) => {
        const pending = previous.drafts[draftKey];
        if (
          pending?.attempt?.key !== current.key ||
          pending.body.trim() !== current.input.body ||
          Number(pending.state) !== current.input.stateId ||
          (pending.due || null) !== current.input.dueDate
        )
          return previous;
        return {
          ...previous,
          drafts: {
            ...previous.drafts,
            [draftKey]: {
              body: "",
              state: "",
              due: "",
              editing: null,
              attempt: null,
            },
          },
        };
      });
      if (!mounted.current) return;
      setPage(result);
      setOffset(0);
      reset();
      setNotice("Seguimiento confirmado.");
    } catch (failure) {
      if (mounted.current)
        setError(
          failure instanceof AdmissionsError
            ? failure.message
            : "No se confirmó el guardado. Puede reintentar; el borrador se conserva.",
        );
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <section className="admissions-section" aria-label="Seguimiento CRM">
      <div className="panel-heading">
        <div>
          <h3>Seguimiento CRM</h3>
          <p>
            Notas propias vinculadas a este aspirante. No modifican el historial
            SIIE.
          </p>
        </div>
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() => {
            setReload((value) => value + 1);
            setNotice("");
          }}
        >
          Recargar seguimiento
        </Button>
      </div>
      {error && <Notice error>{error}</Notice>}
      {notice && <Notice>{notice}</Notice>}
      {page?.items.length === 0 && <p>No hay seguimientos CRM registrados.</p>}
      {page && (
        <>
          <ul className="admissions-history">
            {page.items.map((item) => (
              <li key={item.id}>
                <strong>{item.state || `Estado ${item.stateId}`}</strong>
                <p className="admissions-note">{item.body}</p>
                {item.dueDate && <p>Próximo seguimiento: {item.dueDate}</p>}
                <small>Origen CRM · Revisión {item.revision}</small>
                <Button
                  variant="quiet"
                  disabled={busy}
                  onClick={() => {
                    setEditing(item);
                    setBody(item.body);
                    setState(String(item.stateId));
                    setDue(item.dueDate || "");
                    attempt.current = null;
                    setNotice("");
                  }}
                >
                  Editar seguimiento
                </Button>
              </li>
            ))}
          </ul>
          {(page.hasMore || page.offset > 0) && (
            <Pagination
              label="Páginas de seguimiento CRM"
              page={page}
              onChange={setOffset}
            />
          )}
        </>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <h4>{editing ? "Editar nota CRM" : "Nuevo seguimiento"}</h4>
        {editing &&
          page?.items.some(
            (item) =>
              item.id === editing.id && item.revision !== editing.revision,
          ) && (
            <Notice>
              Hay una versión más reciente de esta nota. Revise el registro
              antes de volver a guardar.
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => {
                  const latest = page.items.find(
                    (item) => item.id === editing.id,
                  );
                  if (latest) {
                    setEditing(latest);
                    attempt.current = null;
                  }
                }}
              >
                Usar versión actual y conservar borrador
              </Button>
            </Notice>
          )}
        <TextArea
          id="admissions-note"
          label="Nota de seguimiento"
          maxLength={2000}
          required
          value={body}
          disabled={busy}
          onChange={(event) => setBody(event.target.value)}
        />
        <div className="form-grid">
          <SelectField
            id="admissions-state"
            label="Estado del seguimiento"
            required
            value={state}
            disabled={busy}
            onChange={(event) => setState(event.target.value)}
            options={[
              { value: "", label: "Seleccione un estado" },
              ...states.map((item) => ({
                value: String(item.id),
                label: item.label,
              })),
            ]}
          />
          <Field
            id="admissions-due"
            type="date"
            label="Próximo seguimiento (opcional)"
            value={due}
            disabled={busy}
            onChange={(event) => setDue(event.target.value)}
          />
        </div>
        <p className="admissions-hint">
          Estados del catálogo SIIE. Elegir «Matriculado» en una nota no
          registra una matrícula.
        </p>
        <div className="actions">
          <Button
            type="submit"
            disabled={busy || !page || !body.trim() || !state}
          >
            {busy ? "Guardando…" : "Guardar seguimiento"}
          </Button>
          {editing && (
            <Button variant="secondary" disabled={busy} onClick={reset}>
              Cancelar edición
            </Button>
          )}
        </div>
      </form>
      <p className="admissions-hint">
        Confirme los cambios cuando el seguimiento esté listo.
      </p>
    </section>
  );
}
