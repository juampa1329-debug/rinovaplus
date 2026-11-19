import { useEffect, useRef, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Field, Notice } from "../shared/ui";
import { useTask } from "./api";

type Row = Record<string, unknown>;
const text = (v: unknown) =>
  v === null || v === undefined ? "Sin dato" : String(v);
const rows = (v: unknown): Row[] => (Array.isArray(v) ? (v as Row[]) : []);

export function SiieContacts({ person }: { person: Row }) {
  return (
    <>
      <dl className="siie-facts">
        {Object.entries({
          telefono: "Teléfono de origen",
          celular: "Celular de origen",
          correo: "Correo de origen",
        }).map(([key, label]) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>{text(person[key])}</dd>
          </div>
        ))}
      </dl>
      <p>
        Datos de contacto de SIIE, sin validación de país ni autorización de
        campañas implícita.
      </p>
    </>
  );
}

export function SiieStudents() {
  const task = useTask();
  const epoch = useRef(0);
  const [periods, setPeriods] = useState<Row | null>(null);
  const [period, setPeriod] = useState("");
  const [filters, setFilters] = useState<Row | null>(null);
  const [program, setProgram] = useState("");
  const [shift, setShift] = useState("");
  const [state, setState] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState<Row | null>(null);
  const [applied, setApplied] = useState<Record<string, string> | null>(null);
  const [detail, setDetail] = useState<Row | null>(null);
  const [correlation, setCorrelation] = useState("");
  useEffect(
    () => () => {
      epoch.current++;
    },
    [],
  );
  const load = (
    route: string,
    values: Record<string, string>,
    done: (d: Row) => void,
  ) => {
    const ticket = ++epoch.current;
    const search = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== "") search.set(key, value);
    });
    void task.run(async () => {
      try {
        const result = await api<{ data: Row; correlation_id?: string }>(
          `/siie/${route}?${search}`,
        );
        if (ticket !== epoch.current) return;
        done(result.data);
        setCorrelation(result.correlation_id ?? "");
      } catch (failure) {
        if (ticket === epoch.current) throw failure;
      }
    }, "");
  };
  const clear = () => {
    epoch.current++;
    setPage(null);
    setDetail(null);
    setApplied(null);
    setFilters(null);
    setProgram("");
    setShift("");
    setState("");
    setCorrelation("");
  };
  const getPeriods = (history = false) =>
    load("periods", history ? { incluirHistoricos: "1" } : {}, (d) => {
      clear();
      setPeriods(d);
      setPeriod(
        d.requiereSeleccion === false && d.idPeriodoOfrecido
          ? text(d.idPeriodoOfrecido)
          : "",
      );
    });
  const search = (
    offset = "0",
    criteria: Record<string, string> = {
      idPeriodo: period,
      idPrograma: program,
      idJornada: shift,
      idEstadoMatricula: state,
      q: query,
    },
  ) => {
    setDetail(null);
    load("students", { ...criteria, offset }, (d) => {
      setPage(d);
      setApplied(criteria);
    });
  };
  const person = (detail?.estudiante ?? {}) as Row;
  return (
    <section aria-label="Estudiantes de SIIE">
      <h3>Estudiantes y matrículas</h3>
      <p>
        Consulta registros nativos del período ofrecido. Los estados actuales
        del estudiante se muestran separados de la matrícula histórica.
      </p>
      {task.notices}
      <fieldset disabled={task.busy} aria-busy={task.busy}>
        <div className="siie-pagination">
          <Button type="button" onClick={() => getPeriods()}>
            Obtener período ofrecido de estudiantes
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => getPeriods(true)}
          >
            Consultar períodos históricos de estudiantes
          </Button>
        </div>
        {periods && (
          <>
            <label>
              Período de estudiantes
              <select
                value={period}
                onChange={(e) => {
                  clear();
                  setPeriod(e.target.value);
                }}
              >
                <option value="">Seleccionar período</option>
                {rows(periods.items).map((p) => (
                  <option key={text(p.id)} value={text(p.id)}>
                    {text(p.nombre)}
                    {text(p.id) === text(periods.idPeriodoOfrecido)
                      ? " · Ofrecido"
                      : ""}
                    {p.activo === true ? " · Académico activo" : ""}
                  </option>
                ))}
              </select>
            </label>
            <Button
              type="button"
              variant="secondary"
              disabled={!period}
              onClick={() =>
                load("student_filters", { idPeriodo: period }, setFilters)
              }
            >
              Obtener filtros de estudiantes
            </Button>
            <div className="siie-filter-row">
              <label>
                Programa de estudiantes
                <select
                  value={program}
                  onChange={(e) => setProgram(e.target.value)}
                >
                  <option value="">Todos</option>
                  {rows(filters?.programas)
                    .filter((p) => (p.idPrograma ?? p.id) != null)
                    .map((p) => (
                      <option
                        key={text(p.idPrograma ?? p.id)}
                        value={text(p.idPrograma ?? p.id)}
                      >
                        {text(p.programa ?? p.nombre)}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Jornada de matrícula
                <select
                  value={shift}
                  onChange={(e) => setShift(e.target.value)}
                >
                  <option value="">Todas</option>
                  {rows(filters?.jornadas)
                    .filter((p) => (p.idJornada ?? p.id) != null)
                    .map((p) => (
                      <option
                        key={text(p.idJornada ?? p.id)}
                        value={text(p.idJornada ?? p.id)}
                      >
                        {text(p.jornada ?? p.nombre)}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Estado actual del estudiante
                <select
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                >
                  <option value="">Todos</option>
                  {rows(filters?.estadosMatricula)
                    .filter((p) => (p.idEstadoMatricula ?? p.id) != null)
                    .map((p) => (
                      <option
                        key={text(p.idEstadoMatricula ?? p.id)}
                        value={text(p.idEstadoMatricula ?? p.id)}
                      >
                        {text(p.estadoMatricula ?? p.nombre)}
                        {p.requiereRevision === true ? " · Revisar" : ""}
                      </option>
                    ))}
                </select>
              </label>
              <Field
                id="siie-student-search"
                label="Buscar estudiante"
                value={query}
                maxLength={100}
                onChange={(e) => setQuery(e.target.value)}
              />
              <Button type="button" disabled={!period} onClick={() => search()}>
                Buscar estudiantes en SIIE
              </Button>
            </div>
          </>
        )}
        {page && (
          <div className="siie-split">
            <div>
              <h4>Estudiantes del período consultado</h4>
              <ul className="siie-list">
                {rows(page.items).map((p) => (
                  <li key={`${text(p.idEstudiante)}:${text(p.idMatricula)}`}>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        setDetail(null);
                        load(
                          "student",
                          {
                            idEstudiante: text(p.idEstudiante),
                            idPeriodo: applied!.idPeriodo,
                          },
                          setDetail,
                        );
                      }}
                    >
                      <strong>{text(p.nombre)}</strong>
                      <span>
                        {text(p.programa)} · {text(p.jornada)}
                      </span>
                      <span>
                        {text(p.estadoMatricula)}
                        {p.requiereRevisionEstado === true
                          ? " · Requiere revisión"
                          : ""}
                      </span>
                      <span>
                        Matrícula {text(p.idMatricula)} · Nivel {text(p.nivel)}
                      </span>
                    </Button>
                  </li>
                ))}
              </ul>
              {!rows(page.items).length && (
                <p>No hay estudiantes para estos filtros.</p>
              )}
              <div className="siie-pagination">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={Number(page.offset) === 0}
                  onClick={() =>
                    search(
                      String(Math.max(0, Number(page.offset) - 25)),
                      applied!,
                    )
                  }
                >
                  Estudiantes anteriores
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={page.hasMore !== true}
                  onClick={() =>
                    search(String(Number(page.offset) + 25), applied!)
                  }
                >
                  Más estudiantes
                </Button>
              </div>
            </div>
            <div>
              {detail && (
                <article aria-label="Ficha de estudiante SIIE">
                  <h4>{text(person.nombre)}</h4>
                  <p>
                    Estado actual: {text(person.estadoMatricula)}
                    {person.requiereRevisionEstado === true
                      ? " · Requiere revisión de origen"
                      : ""}
                    .
                  </p>
                  <SiieContacts person={person} />
                  <h4>Matrículas del período</h4>
                  {rows(detail.matriculas).map((m, i) => (
                    <dl className="siie-facts" key={text(m.idMatricula) + i}>
                      {Object.entries({
                        idMatricula: "Matrícula",
                        periodo: "Período de matrícula",
                        periodoOferta: "Período de la oferta",
                        programa: "Programa",
                        escuela: "Escuela",
                        modalidad: "Modalidad",
                        jornada: "Jornada de matrícula",
                        nivel: "Nivel",
                        fechaMatricula: "Fecha de matrícula",
                      }).map(([key, label]) => (
                        <div key={key}>
                          <dt>{label}</dt>
                          <dd>{text(m[key])}</dd>
                        </div>
                      ))}
                    </dl>
                  ))}
                  <Notice>
                    La fuente no acredita un vínculo con aspirantes ni una
                    identidad de persona común. La ficha no consulta cartera,
                    notas ni asistencia.
                  </Notice>
                </article>
              )}
            </div>
          </div>
        )}
      </fieldset>
      {task.busy && <p role="status">Consultando estudiantes…</p>}
      {correlation && <small>Referencia de consulta: {correlation}</small>}
    </section>
  );
}
