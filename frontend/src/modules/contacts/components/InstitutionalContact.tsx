import { useEffect, useRef, useState } from "react";
import type { Client } from "../../../shared/demo";
import type { Program } from "../../catalog/model";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import {
  emptyInstitutionalProfile,
  trimIdentitySpaces,
  institutionalIdentityApi,
  type IdentityCatalog,
  type IdentityLookup,
  type IdentityPage,
  type IdentitySearch,
  type InstitutionalProfile,
} from "../api/institutionalIdentity";
import { Badge, Button, Field, Notice, SelectField } from "../../../shared/ui";

const sourceLabels = {
  crm: "Contacto CRM",
  student: "Estudiante SIIE",
  applicant: "Aspirante SIIE",
};
const reasonLabels: Record<string, string> = {
  same_document_type_and_number: "Mismo tipo y número de documento",
  same_email: "Correo coincidente; puede ser compartido",
  same_phone: "Teléfono coincidente; puede ser compartido",
  name_search: "Resultado de búsqueda por nombre",
};

export function InstitutionalContact({
  client,
  onChange,
  errors,
  programs,
  onOpenContact,
}: {
  client: Client;
  onChange: (client: Client) => void;
  errors: Record<string, string>;
  programs: Program[];
  onOpenContact?: (id: string) => void;
}) {
  const profile = client.institutionalProfile ?? emptyInstitutionalProfile();
  const [catalog, setCatalog] = useState<IdentityCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void institutionalIdentityApi
      .catalog(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setCatalog(value);
          setCatalogError("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setCatalogError(
            "No se pudieron cargar los tipos de documento y períodos reales. Los datos y borradores se conservan.",
          );
      });
    return () => controller.abort();
  }, [reload]);
  function change<K extends keyof InstitutionalProfile>(
    key: K,
    value: InstitutionalProfile[K],
  ) {
    onChange({ ...client, institutionalProfile: { ...profile, [key]: value } });
  }
  const types = catalog?.documentTypes ?? [];
  const periods = catalog?.periods.items ?? [];
  return (
    <>
      <details className="scope-note" open>
        <summary>Ficha institucional informada</summary>
        <p>
          Datos declarados en CRM. No modifican SIIE ni confirman identidad
          académica. El nombre visible se conserva por separado.
        </p>
        {catalogError && <Notice error>{catalogError}</Notice>}
        {!catalog && !catalogError && (
          <p className="scope-text">Cargando catálogos institucionales…</p>
        )}
        {catalogError && (
          <Button variant="secondary" onClick={() => setReload((n) => n + 1)}>
            Reintentar catálogos institucionales
          </Button>
        )}
        <div className="form-grid">
          <Field
            id="institutional-given-names"
            label="Nombres informados"
            maxLength={100}
            value={profile.givenNames}
            error={errors.institutionalName}
            onChange={(e) => change("givenNames", e.target.value)}
          />
          <Field
            id="institutional-first-surname"
            label="Primer apellido informado"
            maxLength={30}
            value={profile.firstSurname}
            onChange={(e) => change("firstSurname", e.target.value)}
          />
          <Field
            id="institutional-second-surname"
            label="Segundo apellido informado"
            maxLength={30}
            value={profile.secondSurname}
            onChange={(e) => change("secondSurname", e.target.value)}
          />
          <SelectField
            id="institutional-document-type"
            label="Tipo de documento informado"
            value={
              profile.documentTypeId === null
                ? ""
                : String(profile.documentTypeId)
            }
            disabled={!catalog}
            options={[
              { value: "", label: "Sin especificar" },
              ...types.map((t) => ({
                value: String(t.id),
                label: `${t.code} · ${t.label}`,
              })),
              ...(profile.documentTypeId !== null &&
              !types.some((t) => t.id === profile.documentTypeId)
                ? [
                    {
                      value: String(profile.documentTypeId),
                      label: `Tipo guardado #${profile.documentTypeId} · no verificado`,
                    },
                  ]
                : []),
            ]}
            onChange={(e) =>
              change(
                "documentTypeId",
                e.target.value ? Number(e.target.value) : null,
              )
            }
          />
          <Field
            id="institutional-document"
            label="Número de documento informado"
            maxLength={16}
            value={profile.document}
            error={errors.institutionalDocument}
            hint="Texto de hasta 16 caracteres. Se conservan ceros y puntuación."
            onChange={(e) => change("document", e.target.value)}
          />
          <Field
            id="institutional-email"
            label="Correo informado"
            type="email"
            maxLength={160}
            value={profile.email}
            error={errors.institutionalEmail}
            onChange={(e) => change("email", e.target.value)}
          />
          <SelectField
            id="institutional-period"
            label="Período al que aspira"
            value={
              profile.aspirationPeriodId === null
                ? ""
                : String(profile.aspirationPeriodId)
            }
            disabled={!catalog}
            options={[
              { value: "", label: "Sin período informado" },
              ...periods.map((p) => ({
                value: String(p.id),
                label: p.label + (p.active ? " · activo en SIIE" : ""),
              })),
              ...(profile.aspirationPeriodId !== null &&
              !periods.some((p) => p.id === profile.aspirationPeriodId)
                ? [
                    {
                      value: String(profile.aspirationPeriodId),
                      label: `Período guardado #${profile.aspirationPeriodId} · no verificado`,
                    },
                  ]
                : []),
            ]}
            onChange={(e) =>
              change(
                "aspirationPeriodId",
                e.target.value ? Number(e.target.value) : null,
              )
            }
          />
        </div>
      </details>
      <IdentityCandidates
        client={client}
        catalog={catalog}
        programs={programs}
        onOpenContact={onOpenContact}
      />
    </>
  );
}

function IdentityCandidates({
  client,
  catalog,
  programs,
  onOpenContact,
}: {
  client: Client;
  catalog: IdentityCatalog | null;
  programs: Program[];
  onOpenContact?: (id: string) => void;
}) {
  const [searches, setSearches] = useWorkspaceField(
    "clients",
    "identitySearches",
  );
  const identityKey = client.id || "__new";
  const search: IdentitySearch = searches[identityKey] ?? {
    mode: "identity",
    source: "all",
    name: "",
    period: "",
    program: "",
    offset: 0,
  };
  const [open, setOpen] = useState(false);
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    page: IdentityPage;
  } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [selected, setSelected] = useState("");
  const sequence = useRef(0);
  const profile = client.institutionalProfile ?? emptyInstitutionalProfile();
  const body: IdentityLookup = {
    mode: search.mode,
    source: search.source,
    ownContactId: client.id || null,
    documentTypeId: profile.documentTypeId,
    document: trimIdentitySpaces(profile.document),
    email: trimIdentitySpaces(profile.email),
    phone: trimIdentitySpaces(client.phone),
    name: search.name.trim(),
    periodId:
      search.mode === "name" && search.period ? Number(search.period) : null,
    programId:
      search.mode === "name" && search.program ? Number(search.program) : null,
    offset: search.offset,
  };
  const key = JSON.stringify(body);
  const canSearch =
    search.mode === "name"
      ? body.name.length >= 3
      : (profile.documentTypeId !== null &&
          !!body.document &&
          body.document.length <= 16) ||
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email) ||
        body.phone.replace(/\D/g, "").length >= 5;
  useEffect(() => {
    if (!open || !canSearch) return;
    const controller = new AbortController();
    const token = ++sequence.current;
    const timer = window.setTimeout(() => {
      void institutionalIdentityApi
        .candidates(JSON.parse(key), controller.signal)
        .then((page) => {
          if (!controller.signal.aborted && token === sequence.current) {
            setResult({ key, page });
            setFailure(null);
          }
        })
        .catch(() => {
          if (!controller.signal.aborted && token === sequence.current)
            setFailure({
              key,
              message:
                "No se pudieron consultar los candidatos. Reintente; la ficha no cambió.",
            });
        });
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key, open, canSearch, retry]);
  const current = result?.key === key ? result.page : null;
  const error = failure?.key === key ? failure.message : "";
  const candidate = current?.items.find(
    (item) => item.source + ":" + item.sourceId === selected,
  );
  function change(update: Partial<IdentitySearch>) {
    setSearches((previous) => ({
      ...previous,
      [identityKey]: { ...search, ...update, offset: update.offset ?? 0 },
    }));
  }
  return (
    <details
      className="scope-note"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>Posibles duplicados y registros institucionales</summary>
      <p>
        Comparación de lectura. Una coincidencia no confirma identidad ni
        fusiona, copia o vincula registros.
      </p>
      <div className="form-grid">
        <SelectField
          id="identity-mode"
          label="Modo de búsqueda de candidatos"
          value={search.mode}
          options={[
            {
              value: "identity",
              label: "Coincidencias de identidad · todos los períodos",
            },
            { value: "name", label: "Explorar por nombre y período" },
          ]}
          onChange={(e) =>
            change({ mode: e.target.value as IdentitySearch["mode"] })
          }
        />
        <SelectField
          id="identity-source"
          label="Fuente de candidatos"
          value={search.source}
          options={[
            { value: "all", label: "Todas las fuentes" },
            { value: "crm", label: "Contactos CRM" },
            { value: "student", label: "Estudiantes SIIE" },
            { value: "applicant", label: "Aspirantes SIIE" },
          ]}
          onChange={(e) =>
            change({ source: e.target.value as IdentitySearch["source"] })
          }
        />
        {search.mode === "name" && (
          <>
            <Field
              id="identity-name"
              label="Buscar candidatos por nombre"
              value={search.name}
              maxLength={200}
              hint="Desde tres caracteres; búsqueda automática mientras escribe."
              onChange={(e) => change({ name: e.target.value })}
            />
            <SelectField
              id="identity-period-filter"
              label="Período de exploración"
              value={search.period}
              disabled={!catalog}
              options={[
                { value: "", label: "Todos los períodos" },
                ...(catalog?.periods.items ?? []).map((p) => ({
                  value: String(p.id),
                  label: p.label,
                })),
              ]}
              onChange={(e) => change({ period: e.target.value })}
            />
            <SelectField
              id="identity-program-filter"
              label="Programa de exploración"
              value={search.program}
              options={[
                { value: "", label: "Todos los programas" },
                ...programs.map((p) => ({
                  value: String(p.id),
                  label: p.label || `Programa #${p.id}`,
                })),
              ]}
              onChange={(e) => change({ program: e.target.value })}
            />
          </>
        )}
      </div>
      <p className="scope-text">
        {search.mode === "identity"
          ? "Documento con tipo exacto, correo sin distinguir mayúsculas o teléfono exacto informado. Se revisan todos los períodos y programas, sin inferir país o formato telefónico."
          : "Período aspirado en CRM/aspirantes y período de oferta en estudiantes. Cambie a coincidencias de identidad para revisar registros de otros períodos."}
      </p>
      {!canSearch && (
        <p>
          {search.mode === "name"
            ? "Escriba al menos tres caracteres para explorar."
            : "Complete tipo y documento, un correo válido o un teléfono con al menos cinco dígitos para comparar."}
        </p>
      )}
      {open && canSearch && !current && !error && (
        <p role="status">Buscando candidatos reales…</p>
      )}
      {error && (
        <Notice error>
          {error}
          <Button variant="secondary" onClick={() => setRetry((n) => n + 1)}>
            Reintentar candidatos
          </Button>
        </Notice>
      )}
      {current && (
        <>
          {!current.items.length && (
            <p>
              Sin coincidencias con los criterios actuales. Esto no certifica
              que no existan otros registros.
            </p>
          )}
          <ul className="configuration-list">
            {current.items.map((item) => (
              <li key={item.source + ":" + item.sourceId}>
                <div>
                  <strong>{item.name || "Sin nombre informado"}</strong>
                  <small>
                    {sourceLabels[item.source]} · ID {item.sourceId}
                  </small>
                  <small>
                    {item.period || "Sin período"} ·{" "}
                    {item.program || "Sin programa informado"}
                  </small>
                  {item.reasons.map((reason) => (
                    <small key={reason}>{reasonLabels[reason] ?? reason}</small>
                  ))}
                </div>
                <Button
                  variant="secondary"
                  onClick={() => setSelected(item.source + ":" + item.sourceId)}
                >
                  Comparar datos
                </Button>
                {item.contactId && onOpenContact && (
                  <Button
                    variant="quiet"
                    onClick={() => onOpenContact(item.contactId!)}
                  >
                    Abrir conversación existente
                  </Button>
                )}
              </li>
            ))}
          </ul>
          <div className="actions" aria-label="Páginas de candidatos">
            <Button
              variant="quiet"
              disabled={search.offset === 0}
              onClick={() =>
                change({ offset: Math.max(0, search.offset - 25) })
              }
            >
              Candidatos anteriores
            </Button>
            <Badge>Página {Math.floor(search.offset / 25) + 1}</Badge>
            <Button
              variant="quiet"
              disabled={!current.hasMore}
              onClick={() => change({ offset: search.offset + 25 })}
            >
              Más candidatos
            </Button>
          </div>
        </>
      )}
      {candidate && (
        <section aria-label="Comparación de identidad de lectura">
          <h4>Registro seleccionado · solo lectura</h4>
          <p>
            {sourceLabels[candidate.source]} · ID {candidate.sourceId}. El
            registro conserva su identidad y origen; no se aplican cambios desde
            esta comparación.
          </p>
          <dl className="detail-list">
            {[
              ["Nombre visible / original", client.name, candidate.name],
              ["Nombres informados", profile.givenNames, candidate.givenNames],
              ["Primer apellido", profile.firstSurname, candidate.firstSurname],
              [
                "Segundo apellido",
                profile.secondSurname,
                candidate.secondSurname,
              ],
              [
                "Tipo de documento",
                profile.documentTypeId,
                candidate.documentTypeId,
              ],
              ["Documento", profile.document, candidate.document],
              ["Correo", profile.email, candidate.email],
              ["Teléfono principal", client.phone, candidate.phone],
              ["Teléfono alternativo original", null, candidate.alternatePhone],
              [
                "Período",
                catalog?.periods.items.find(
                  (p) => p.id === profile.aspirationPeriodId,
                )?.label,
                candidate.period,
              ],
              ["Período de oferta original", null, candidate.offerPeriod],
              ["Programa", client.program, candidate.program],
            ].map(([label, own, original]) => (
              <div key={String(label)}>
                <dt>{label}</dt>
                <dd>
                  CRM: {own ?? "Sin informar"}
                  <br />
                  Original: {original || "Sin informar"}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
    </details>
  );
}
