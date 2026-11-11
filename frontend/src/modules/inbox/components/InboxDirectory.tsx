import { useEffect, useId, useState } from "react";
import {
  inboxOperationsApi,
  type DirectoryItem,
  type DirectoryPage,
} from "../api/inboxOperations";
import { Button, Field, Notice, SelectField } from "../../../shared/ui";
export function InboxDirectory({
  scope,
  label,
  value,
  name = "",
  onChange,
  eligible = true,
  refresh = 0,
  disabled = false,
}: {
  scope: "employees" | "members" | "agents";
  label: string;
  value: string;
  name?: string;
  onChange: (value: string, item?: DirectoryItem) => void;
  eligible?: boolean;
  refresh?: number;
  disabled?: boolean;
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify([
    query,
    offset,
    scope,
    eligible,
    refresh,
    attempt,
  ]);
  const [result, setResult] = useState<{
    key: string;
    page: DirectoryPage;
  } | null>(null);
  const [failure, setFailure] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => {
        const params = new URLSearchParams({
          scope,
          q: query,
          offset: String(offset),
          eligible: String(eligible),
        });
        void inboxOperationsApi
          .read<DirectoryPage>("/directory?" + params, controller.signal)
          .then((page) => {
            if (!controller.signal.aborted) {
              setResult({ key, page });
              setFailure("");
            }
          })
          .catch(() => {
            if (!controller.signal.aborted) setFailure(key);
          });
      },
      query ? 300 : 0,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [key, query, offset, scope, eligible]);
  const page = result?.key === key ? result.page : null;
  const options = (page?.items ?? []).map((item) => ({
    ...item,
    revision: page?.revision,
  }));
  return (
    <div className="inbox-directory">
      <Field
        id={id + "-search"}
        label={"Buscar " + label.toLowerCase()}
        value={query}
        maxLength={100}
        disabled={disabled}
        onChange={(event) => {
          setQuery(event.target.value);
          setOffset(0);
        }}
      />
      <SelectField
        id={id}
        label={label}
        value={value}
        disabled={disabled || !page}
        options={[
          { value: "", label: "Sin selección" },
          ...options.map((item) => ({
            value: String(item.id),
            label:
              (item.name || "Registro sin nombre") +
              (!item.selectable ? " · no disponible" : ""),
          })),
          ...(value && !options.some((item) => String(item.id) === value)
            ? [{ value, label: name || "Selección conservada" }]
            : []),
        ]}
        onChange={(event) =>
          onChange(
            event.target.value,
            options.find((item) => String(item.id) === event.target.value),
          )
        }
      />
      {failure === key ? (
        <Notice error>
          No se pudo cargar el directorio.{" "}
          <Button variant="quiet" onClick={() => setAttempt((n) => n + 1)}>
            Reintentar directorio
          </Button>
        </Notice>
      ) : !page ? (
        <small role="status">Consultando directorio…</small>
      ) : (
        <>
          <small>
            {page.items.length
              ? `Página ${offset / 25 + 1}`
              : "Sin registros coincidentes"}
          </small>
          <div className="actions">
            <Button
              variant="quiet"
              disabled={!offset || disabled}
              onClick={() => setOffset(Math.max(0, offset - 25))}
            >
              Anteriores
            </Button>
            <Button
              variant="quiet"
              disabled={!page.hasMore || disabled}
              onClick={() => setOffset(offset + 25)}
            >
              Más resultados
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
