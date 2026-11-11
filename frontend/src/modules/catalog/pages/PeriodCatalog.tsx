import { useEffect, useRef, useState } from "react";
import { fetchCatalog, fetchProgramFilterOptions } from "../api/catalog";
import type {
  CatalogPage,
  CatalogResource,
  Period,
  School,
  Modality,
} from "../api/catalog";
import { Button, Field, Notice, SelectField } from "../../../shared/ui";

export function PeriodCatalog() {
  const [token, setToken] = useState("");
  const [page, setPage] = useState<CatalogPage | null>(null);
  const [resource, setResource] = useState<CatalogResource>("periods");
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [schools, setSchools] = useState<School[]>([]);
  const [modalities, setModalities] = useState<Modality[]>([]);
  const [schoolId, setSchoolId] = useState("");
  const [modalityId, setModalityId] = useState("");
  const [loadingFilters, setLoadingFilters] = useState(false);
  const request = useRef<AbortController | null>(null);
  const copy = {
    periods: {
      heading: "Períodos académicos",
      label: "Período académico",
      plural: "períodos",
      singular: "un período",
    },
    schools: {
      heading: "Escuelas",
      label: "Escuela",
      plural: "escuelas",
      singular: "una escuela",
    },
    modalities: {
      heading: "Modalidades",
      label: "Modalidad",
      plural: "modalidades",
      singular: "una modalidad",
    },
    programs: {
      heading: "Programas",
      label: "Programa",
      plural: "programas",
      singular: "un programa",
    },
  }[resource];
  useEffect(
    () => () => {
      request.current?.abort();
      request.current = null;
    },
    [],
  );

  function changeToken(value: string) {
    request.current?.abort();
    request.current = null;
    setToken(value);
    setPage(null);
    setSelected("");
    setLoading(false);
    setError("");
    clearFilters();
  }
  function changeResource(value: CatalogResource) {
    request.current?.abort();
    request.current = null;
    setResource(value);
    setPage(null);
    setSelected("");
    setLoading(false);
    setError("");
    clearFilters();
  }
  function clearFilters() {
    setSchools([]);
    setModalities([]);
    setSchoolId("");
    setModalityId("");
    setLoadingFilters(false);
  }
  function changeFilter(kind: "school" | "modality", value: string) {
    request.current?.abort();
    request.current = null;
    if (kind === "school") setSchoolId(value);
    else setModalityId(value);
    setPage(null);
    setSelected("");
    setLoading(false);
    setError("");
  }
  async function loadFilters() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoadingFilters(true);
    setError("");
    setPage(null);
    setSelected("");
    setSchools([]);
    setModalities([]);
    setSchoolId("");
    setModalityId("");
    const timeout = window.setTimeout(() => {
      if (request.current !== controller) return;
      controller.abort();
      request.current = null;
      setLoadingFilters(false);
      setError("El catálogo no está disponible. Intente nuevamente.");
    }, 10000);
    try {
      const result = await fetchProgramFilterOptions(token, controller.signal);
      if (request.current !== controller || controller.signal.aborted) return;
      setSchools(result.schools);
      setModalities(result.modalities);
    } catch (failure) {
      if (request.current !== controller || controller.signal.aborted) return;
      setError(
        failure instanceof Error &&
          failure.message === "Revise la clave de acceso temporal."
          ? failure.message
          : "El catálogo no está disponible. Intente nuevamente.",
      );
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller && !controller.signal.aborted)
        setLoadingFilters(false);
    }
  }
  async function load(offset: number) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    setSelected("");
    const timeout = window.setTimeout(() => {
      if (request.current !== controller) return;
      controller.abort();
      request.current = null;
      setLoading(false);
      setPage(null);
      setError("El catálogo no está disponible. Intente nuevamente.");
    }, 10000);
    try {
      const result = await fetchCatalog(
        resource,
        token,
        offset,
        controller.signal,
        {
          schoolId: schoolId === "" ? undefined : Number(schoolId),
          modalityId: modalityId === "" ? undefined : Number(modalityId),
        },
      );
      if (request.current !== controller || controller.signal.aborted) return;
      setPage(result);
    } catch (failure) {
      if (request.current !== controller || controller.signal.aborted) return;
      setPage(null);
      setError(
        failure instanceof Error &&
          failure.message === "Revise la clave de acceso temporal."
          ? failure.message
          : "El catálogo no está disponible. Intente nuevamente.",
      );
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller && !controller.signal.aborted)
        setLoading(false);
    }
  }
  const entry = page?.items.find((item) => String(item.id) === selected);
  const period =
    resource === "periods" ? (entry as Period | undefined) : undefined;
  return (
    <section className="panel" aria-label="Catálogos académicos locales">
      <h2>{copy.heading}</h2>
      <Notice>
        Consulte las opciones disponibles para cada período académico.
      </Notice>
      <SelectField
        id="catalog-resource"
        label="Catálogo académico"
        value={resource}
        options={[
          { value: "periods", label: "Períodos" },
          { value: "schools", label: "Escuelas" },
          { value: "modalities", label: "Modalidades" },
          { value: "programs", label: "Programas" },
        ]}
        onChange={(event) =>
          changeResource(event.target.value as CatalogResource)
        }
      />
      {resource === "programs" && (
        <>
          <Button
            variant="secondary"
            disabled={loading || loadingFilters}
            onClick={() => void loadFilters()}
          >
            Cargar filtros
          </Button>
          <SelectField
            id="program-school"
            label="Filtrar por escuela"
            value={schoolId}
            disabled={loadingFilters}
            options={[
              { value: "", label: "Todas las escuelas" },
              ...schools.map((item) => ({
                value: String(item.id),
                label: item.label,
              })),
            ]}
            onChange={(event) => changeFilter("school", event.target.value)}
          />
          <SelectField
            id="program-modality"
            label="Filtrar por modalidad"
            value={modalityId}
            disabled={loadingFilters}
            options={[
              { value: "", label: "Todas las modalidades" },
              ...modalities.map((item) => ({
                value: String(item.id),
                label: item.label,
              })),
            ]}
            onChange={(event) => changeFilter("modality", event.target.value)}
          />
          {loadingFilters && <Notice>Cargando filtros…</Notice>}
        </>
      )}
      <Field
        id="catalog-access"
        label="Clave de acceso temporal"
        type="password"
        autoComplete="off"
        value={token}
        onChange={(event) => changeToken(event.target.value)}
        hint="Solo requerida para el modo de catálogo restringido."
      />
      <Button disabled={loading || loadingFilters} onClick={() => void load(0)}>
        {error ? "Reintentar catálogo" : `Cargar ${copy.plural}`}
      </Button>
      {loading && <Notice>Cargando {copy.plural}…</Notice>}
      {error && <Notice error>{error}</Notice>}
      {page && !loading && (
        <>
          {page.items.length === 0 ? (
            <Notice>No hay {copy.plural} en esta página.</Notice>
          ) : (
            <SelectField
              id="catalog-period"
              label={copy.label}
              value={selected}
              options={[
                { value: "", label: `Seleccione ${copy.singular}` },
                ...page.items.map((item) => ({
                  value: String(item.id),
                  label:
                    resource === "programs"
                      ? `ID ${item.id} · ${item.label === null || item.label.trim() === "" ? "Sin nombre" : item.label}`
                      : item.label === null || item.label.trim() === ""
                        ? `Sin nombre (ID ${item.id})`
                        : item.label,
                })),
              ]}
              onChange={(event) => setSelected(event.target.value)}
            />
          )}
          {period && (
            <p>
              Inicio: {period.startDate} · Fin: {period.endDate} · Estado de
              origen: {String(period.sourceState)}
            </p>
          )}
          <p>Página {Math.floor(page.page.offset / 25) + 1}</p>
          <div className="actions">
            <Button
              variant="secondary"
              disabled={page.page.offset === 0}
              onClick={() => void load(Math.max(0, page.page.offset - 25))}
            >
              Anterior
            </Button>
            <Button
              variant="secondary"
              disabled={!page.page.hasMore || page.page.offset >= 10000}
              onClick={() => void load(page.page.offset + 25)}
            >
              Siguiente
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
