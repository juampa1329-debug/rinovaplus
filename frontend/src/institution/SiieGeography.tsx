import { useEffect, useEffectEvent, useRef, useState } from "react";
import { Button, Field, Notice, SelectField } from "../shared/ui";

export type GeographySelection = {
  idPais?: number;
  idDepartamento?: number;
  q?: string;
  offset?: number;
};
export type NativeChoice = { value: string | number; label: string };
type Page = {
  departments: NativeChoice[];
  department_values: { id: number; value: string }[];
  municipalities: NativeChoice[];
  municipal_text: NativeChoice[];
  has_more: boolean;
  next_offset: number | null;
};

export function SiieGeography({
  id,
  draftId,
  label,
  value,
  numeric,
  departmentOnly,
  countries,
  initial,
  disabled,
  call,
  onChange,
}: {
  id: string;
  draftId: string;
  label: string;
  value: string;
  numeric: boolean;
  departmentOnly: boolean;
  countries: NativeChoice[];
  initial?: GeographySelection;
  disabled: boolean;
  call: <T>(path: string) => Promise<T>;
  onChange: (value: string, selection: GeographySelection) => void;
}) {
  const [scope, setScope] = useState<GeographySelection>(initial ?? {});
  const [page, setPage] = useState<Page | null>(null);
  const [search, setSearch] = useState(initial?.q ?? "");
  const [busy, setBusy] = useState(!!initial?.idPais);
  const [error, setError] = useState("");
  const ticket = useRef(0);
  const read = async (next: GeographySelection) => {
    const revision = ++ticket.current;
    const params = new URLSearchParams({ draft_id: draftId });
    Object.entries(next).forEach(([key, v]) => {
      if (v !== undefined) params.set(key, String(v));
    });
    try {
      const result = await call<Page>(`siie-registration/catalogs?${params}`);
      if (ticket.current === revision) {
        setPage(result);
        setScope(next);
      }
    } catch {
      if (ticket.current === revision)
        setError(
          "No se pudo consultar esta ubicación en SIIE. Conserva tu borrador y vuelve a consultar; no escribas un ID manual.",
        );
    } finally {
      if (ticket.current === revision) setBusy(false);
    }
  };
  const load = (next: GeographySelection) => {
    setScope(next);
    setPage(null);
    setBusy(true);
    setError("");
    void read(next);
  };
  const initialRead = useEffectEvent(() => {
    const current = ticket.current;
    if (initial?.idPais)
      void Promise.resolve().then(() => {
        if (ticket.current === current) return read(initial);
      });
  });
  useEffect(() => {
    initialRead();
    const current = ticket;
    return () => {
      current.current++;
    };
  }, []);
  const selectScope = (next: GeographySelection, nextValue = "") => {
    setScope(next);
    setPage(null);
    onChange(nextValue, next);
    if (next.idPais) load(next);
    else {
      ticket.current++;
      setBusy(false);
    }
  };
  const choices = departmentOnly
    ? []
    : numeric
      ? (page?.municipalities ?? [])
      : (page?.municipal_text ?? []);
  return (
    <fieldset className="siie-geography" aria-label={label}>
      <legend>{label}</legend>
      <SelectField
        id={`${id}-country`}
        label={`País · ${label}`}
        value={String(scope.idPais ?? "")}
        disabled={disabled || !countries.length}
        options={[
          { value: "", label: "Selecciona un país" },
          ...countries.map((v) => ({ value: String(v.value), label: v.label })),
        ]}
        onChange={(e) => {
          setSearch("");
          selectScope(e.target.value ? { idPais: Number(e.target.value) } : {});
        }}
      />
      <SelectField
        id={`${id}-department`}
        label={`Departamento · ${label}`}
        value={String(scope.idDepartamento ?? "")}
        disabled={disabled || busy || !page?.departments.length}
        options={[
          { value: "", label: "Selecciona un departamento" },
          ...(page?.departments ?? []).map((v) => ({
            value: String(v.value),
            label: v.label,
          })),
        ]}
        onChange={(e) => {
          const chosen = Number(e.target.value);
          const next = {
            idPais: scope.idPais,
            ...(chosen ? { idDepartamento: chosen } : {}),
          };
          const department = page?.department_values.find(
            (v) => v.id === chosen,
          );
          setSearch("");
          selectScope(next, departmentOnly ? (department?.value ?? "") : "");
        }}
      />
      {!departmentOnly && (
        <>
          <Field
            id={`${id}-search`}
            label={`Buscar municipio · ${label}`}
            maxLength={80}
            value={search}
            disabled={disabled || !scope.idDepartamento}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button
            variant="quiet"
            disabled={disabled || busy || !scope.idDepartamento}
            onClick={() => {
              const next = {
                idPais: scope.idPais,
                idDepartamento: scope.idDepartamento,
                q: search,
                offset: 0,
              };
              onChange("", next);
              load(next);
            }}
          >
            Buscar municipios · {label}
          </Button>
          <SelectField
            id={id}
            label={`Municipio · ${label}`}
            value={value}
            disabled={
              disabled || busy || !scope.idDepartamento || !choices.length
            }
            options={[
              { value: "", label: "Selecciona un municipio" },
              ...(value && !choices.some((v) => String(v.value) === value)
                ? [
                    {
                      value,
                      label:
                        "Selección guardada · consulta su ubicación para validarla",
                    },
                  ]
                : []),
              ...choices.map((v) => ({
                value: String(v.value),
                label: v.label,
              })),
            ]}
            onChange={(e) => onChange(e.target.value, scope)}
          />
          {page?.has_more && (
            <Button
              variant="quiet"
              disabled={disabled || busy}
              onClick={() => {
                if (page.next_offset == null) return;
                const next = { ...scope, offset: page.next_offset };
                onChange("", next);
                load(next);
              }}
            >
              Más municipios · {label}
            </Button>
          )}
          {!!scope.offset && (
            <Button
              variant="quiet"
              disabled={disabled || busy}
              onClick={() => {
                const next = { ...scope, offset: 0 };
                onChange("", next);
                load(next);
              }}
            >
              Primeros municipios · {label}
            </Button>
          )}
        </>
      )}
      {busy && <p role="status">Consultando ubicaciones…</p>}
      {error && (
        <>
          <Notice error>{error}</Notice>
          <Button
            variant="quiet"
            disabled={disabled || busy}
            onClick={() => load(scope)}
          >
            Volver a consultar ubicación
          </Button>
        </>
      )}
    </fieldset>
  );
}
