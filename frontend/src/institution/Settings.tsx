import { useState } from "react";
import { useAdsResource } from "./adsResource";
import { Badge, Button, Field, Notice, SelectField } from "../shared/ui";
import { TypedFields } from "./Fields";
import { allowNavigation, useDraftGuard } from "./drafts";
import { useInstitution, useIntent, useTask } from "./api";
import type { Contract, Document, Setting } from "./api";

export const useResource = useAdsResource;
export function ResourceState({ error }: { error: string }) {
  return <Notice error={!!error}>{error || "Cargando información…"}</Notice>;
}

export function SettingPage({
  section,
  contract,
  onSaved,
}: {
  section: string;
  contract: Contract;
  onSaved?: () => Promise<unknown>;
}) {
  const data = useResource<Setting>(`settings/${section}`);
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <>
      {data.error && (
        <Notice error>
          {data.error} Tus cambios permanecen en pantalla; no se pudo actualizar
          la versión guardada.
        </Notice>
      )}
      <SettingEditor
        key={`${section}-${data.value.revision}`}
        initial={data.value}
        section={section}
        contract={contract}
        reload={data.reload}
        onSaved={onSaved}
      />
    </>
  );
}
function SettingEditor({
  initial,
  section,
  contract,
  reload,
  onSaved,
}: {
  initial: Setting;
  section: string;
  contract: Contract;
  reload: () => Promise<Setting>;
  onSaved?: () => Promise<unknown>;
}) {
  const { session, call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [draft, setDraft] = useState(initial.document),
    [history, setHistory] = useState<
      { revision: number; document: Document; updated_at: string }[]
    >([]),
    [current, setCurrent] = useState<Setting | null>(null);
  useDraftGuard(JSON.stringify(draft) !== JSON.stringify(initial.document));
  const permission = `settings.${section === "models" ? "providers" : section}.write`,
    writable = session.actions.includes(permission);
  const specs = contract.fields[section] ?? [];
  const groups = [...new Set(specs.map((spec) => spec.group))];
  return (
    <>
      <div className="institution-section-head">
        <Badge>Versión {initial.revision}</Badge>
        <Button
          variant="secondary"
          onClick={() =>
            void task.run(async () => {
              setCurrent(await call<Setting>(`settings/${section}`));
            }, "Versión guardada consultada; tu borrador permanece en pantalla.")
          }
        >
          Consultar versión guardada
        </Button>
      </div>
      {!writable && <Notice>Tu rol permite consultar estos ajustes.</Notice>}
      {section === "ai" && (
        <Notice>
          Los modelos guardados se seleccionan en APIs y modelos. Las claves de
          acceso se conservan cifradas.{" "}
          {contract.channel_operations
            ? "Los borradores de comentarios requieren un modelo, credencial y presupuesto válidos. Su envío necesita revisión humana."
            : "La ejecución de proveedores se habilitará con la integración de canales y agentes."}
        </Notice>
      )}
      {section === "budgets" && (
        <Notice>
          Los límites de solicitudes y cantidad de cuentas se aplican
          localmente.{" "}
          {contract.channel_operations
            ? "Los topes diarios controlan la cola de mensajes y las reservas de borradores de IA; cero deshabilita esa ejecución."
            : "Los topes diarios quedan guardados para la futura ejecución de proveedores; cero significa ejecución externa deshabilitada."}
        </Notice>
      )}
      {task.notices}
      {current && (
        <section className="notice">
          <strong>Versión guardada: {current.revision}.</strong>
          <p>
            {current.revision === initial.revision
              ? "El servidor conserva la misma versión que cargaste."
              : "Hay cambios de otra sesión. Copia tus cambios si necesitas conservarlos antes de cargar la versión guardada."}
          </p>
          <Button
            variant="secondary"
            onClick={() => {
              if (
                window.confirm(
                  "¿Cargar la versión guardada y descartar el borrador de este apartado?",
                )
              )
                void task.run(async () => {
                  await reload();
                });
            }}
          >
            Cargar versión guardada
          </Button>
        </section>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(async () => {
            await call(`settings/${section}`, "PUT", {
              operation_id: intent.get({
                revision: initial.revision,
                document: draft,
              }),
              revision: initial.revision,
              document: draft,
            });
            await onSaved?.();
            await reload();
          });
        }}
      >
        <fieldset disabled={task.busy || !writable}>
          {groups.map((group) => (
            <section className="panel" key={group}>
              <h3>{group}</h3>
              <TypedFields
                prefix={section}
                specs={specs.filter((spec) => spec.group === group)}
                value={draft}
                onChange={setDraft}
              />
            </section>
          ))}
          {section === "models" && (
            <ModelSelections
              contract={contract}
              value={draft}
              onChange={setDraft}
            />
          )}
          {section === "ai" && <Fallbacks value={draft} onChange={setDraft} />}
          {section === "modules" && (
            <section className="panel">
              <h3>Módulos de la institución</h3>
              <div className="institution-fields">
                {contract.modules.map((module) => (
                  <label className="institution-check" key={module.id}>
                    <input
                      type="checkbox"
                      checked={
                        (draft.enabled as Record<string, boolean>)[module.id]
                      }
                      disabled={module.id === "settings"}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          enabled: {
                            ...(draft.enabled as Document),
                            [module.id]: event.target.checked,
                          },
                        })
                      }
                    />
                    {module.label}
                  </label>
                ))}
              </div>
              <p>
                Habilitar un módulo autoriza su uso cuando la integración esté
                disponible. Ajustes permanece disponible para administrar el
                sistema.
              </p>
            </section>
          )}
          <Button type="submit" disabled={!writable || task.busy}>
            Guardar cambios
          </Button>
        </fieldset>
      </form>
      <section className="panel">
        <h3>Historial de configuración</h3>
        <Button
          variant="secondary"
          onClick={() =>
            void task.run(async () => {
              const result = await call<{ items: typeof history }>(
                `settings/${section}/history`,
              );
              setHistory(result.items);
            }, "Historial actualizado.")
          }
        >
          Consultar historial
        </Button>
        {history.map((row) => (
          <div className="institution-list-row" key={row.revision}>
            <span>Versión {row.revision}</span>
            <Button
              variant="secondary"
              disabled={
                !writable || task.busy || row.revision === initial.revision
              }
              onClick={() => {
                if (
                  window.confirm(
                    `¿Restaurar la versión ${row.revision}? Se creará una nueva versión y se conservará el historial.`,
                  )
                )
                  void task.run(async () => {
                    await call(
                      `settings/${section}/restore/${row.revision}`,
                      "POST",
                      {
                        operation_id: intent.get({
                          restore: row.revision,
                          revision: initial.revision,
                        }),
                        revision: initial.revision,
                        document: {},
                      },
                    );
                    await onSaved?.();
                    await reload();
                  });
              }}
            >
              Restaurar
            </Button>
          </div>
        ))}
      </section>
    </>
  );
}
function ModelSelections({
  value,
  onChange,
  contract,
}: {
  value: Document;
  onChange: (value: Document) => void;
  contract: Contract;
}) {
  const selections = value.selections as {
    provider: string;
    category: string;
    selected_model: string;
    display_name: string;
    voice_id: string;
  }[];
  const change = (
    provider: string,
    category: string,
    field: string,
    text: string,
  ) => {
    const current = selections.find(
      (s) => s.provider === provider && s.category === category,
    ) ?? {
      provider,
      category,
      selected_model: "",
      display_name: provider,
      voice_id: "",
    };
    onChange({
      selections: [
        ...selections.filter(
          (s) =>
            s !==
            selections.find(
              (row) => row.provider === provider && row.category === category,
            ),
        ),
        { ...current, [field]: text },
      ],
    });
  };
  return (
    <>
      <Notice>
        Escribe el identificador del modelo del proveedor. Un identificador
        guardado permanece disponible aunque el catálogo externo no esté
        conectado. Guardar no verifica credenciales ni realiza llamadas
        externas.
      </Notice>
      {Object.entries(contract.provider_categories).map(
        ([provider, categories]) => (
          <section className="panel" key={provider}>
            <h3>{provider}</h3>
            {categories.map((category) => {
              const current = selections.find(
                (row) => row.provider === provider && row.category === category,
              );
              return (
                <div className="institution-model-row" key={category}>
                  <Badge>
                    {
                      (
                        {
                          text: "Texto",
                          vision: "Visión",
                          audio: "Audio",
                          voice: "Voz",
                          search: "Búsqueda",
                        } as Record<string, string>
                      )[category]
                    }
                  </Badge>
                  <Field
                    id={`model-${provider}-${category}`}
                    label="Identificador del modelo"
                    value={current?.selected_model ?? ""}
                    maxLength={240}
                    onChange={(event) =>
                      change(
                        provider,
                        category,
                        "selected_model",
                        event.target.value,
                      )
                    }
                  />
                  <Field
                    id={`label-${provider}-${category}`}
                    label="Nombre visible"
                    value={current?.display_name ?? provider}
                    maxLength={120}
                    onChange={(event) =>
                      change(
                        provider,
                        category,
                        "display_name",
                        event.target.value,
                      )
                    }
                  />
                  {category === "voice" && (
                    <Field
                      id={`voice-${provider}`}
                      label="Identificador de voz"
                      maxLength={200}
                      value={current?.voice_id ?? ""}
                      onChange={(event) =>
                        change(
                          provider,
                          category,
                          "voice_id",
                          event.target.value,
                        )
                      }
                    />
                  )}
                </div>
              );
            })}
          </section>
        ),
      )}
    </>
  );
}
function Fallbacks({
  value,
  onChange,
}: {
  value: Document;
  onChange: (value: Document) => void;
}) {
  const entries = (value.model_fallbacks_json ?? {}) as Record<
    string,
    string[]
  >;
  return (
    <section className="panel">
      <h3>Orden de modelos de respaldo</h3>
      <p>
        Un identificador por línea, en el orden de intento. No se altera el
        orden guardado.
      </p>
      <div className="institution-fields">
        {[
          "gemini",
          "openai",
          "anthropic",
          "hermes",
          "openrouter",
          "kimi",
          "groq",
          "nvidia",
          "mistral",
          "xai",
        ].map((provider) => (
          <label className="field" key={provider}>
            {provider}
            <textarea
              aria-label={`Respaldos de ${provider}`}
              value={(entries[provider] ?? []).join("\n")}
              onChange={(event) =>
                onChange({
                  ...value,
                  model_fallbacks_json: {
                    ...entries,
                    [provider]: event.target.value.split("\n").filter(Boolean),
                  },
                })
              }
            />
          </label>
        ))}
      </div>
    </section>
  );
}

type Credential = {
  id: string;
  owner: string;
  kind: string;
  version: number;
  configured: boolean;
  hint: string;
  verified: boolean;
};
export function Credentials({
  scope,
  owner,
  kinds,
  onChanged,
}: {
  scope: "provider" | "channel" | "webhook";
  owner: string;
  kinds: { id: string; label: string }[];
  onChanged?: () => Promise<unknown>;
}) {
  const { call, session } = useInstitution(),
    data = useResource<{ items: Credential[] }>(`credentials/${scope}`),
    task = useTask(),
    intent = useIntent();
  const [values, setValues] = useState<Record<string, string>>({});
  useDraftGuard(Object.values(values).some(Boolean));
  const writable = session.actions.includes(
    `settings.${scope === "provider" ? "providers" : scope === "channel" ? "channels" : "webhooks"}.write`,
  );
  return (
    <section className="panel">
      <h3>Credenciales</h3>
      <p>
        El campo vacío conserva la clave actual. La revocación se solicita por
        separado. Las claves guardadas nunca se devuelven en pantalla.
      </p>
      {task.notices}
      {data.error && <Notice error>{data.error}</Notice>}
      {kinds.map((kind) => {
        const current = data.value?.items.find(
          (row) => row.owner === owner && row.kind === kind.id,
        );
        return (
          <div key={kind.id} className="institution-secret-row">
            <Field
              id={`secret-${owner}-${kind.id}`}
              label={kind.label}
              type="password"
              autoComplete="new-password"
              maxLength={12000}
              value={values[kind.id] ?? ""}
              disabled={!writable || task.busy}
              hint={
                data.error
                  ? "No se pudo consultar la clave guardada"
                  : !data.value
                    ? "Consultando credenciales…"
                    : current
                      ? `Guardada · versión ${current.version} · sin verificar con el proveedor`
                      : "Sin clave guardada"
              }
              onChange={(event) =>
                setValues({ ...values, [kind.id]: event.target.value })
              }
            />
            <Button
              disabled={!writable || task.busy || !values[kind.id]}
              onClick={() =>
                void task.run(async () => {
                  const body = {
                    scope,
                    owner,
                    kind: kind.id,
                    value: values[kind.id],
                  };
                  await call("credentials", "PUT", {
                    ...body,
                    operation_id: intent.get(body),
                  });
                  setValues({ ...values, [kind.id]: "" });
                  intent.clear();
                  await data.reload();
                  await onChanged?.();
                })
              }
            >
              Guardar clave
            </Button>
            <Button
              variant="secondary"
              disabled={!writable || task.busy || !current}
              onClick={() => {
                if (window.confirm(`¿Revocar ${kind.label}?`))
                  void task.run(async () => {
                    const body = { scope, owner, kind: kind.id };
                    await call("credentials/revoke", "POST", {
                      ...body,
                      operation_id: intent.get({
                        ...body,
                        revoke: current?.version,
                      }),
                    });
                    await data.reload();
                    await onChanged?.();
                  }, "Clave revocada.");
              }}
            >
              Revocar
            </Button>
          </div>
        );
      })}
    </section>
  );
}
export function ProviderKeys({ contract }: { contract: Contract }) {
  const [provider, setProvider] = useState(
    Object.keys(contract.provider_categories)[0],
  );
  return (
    <>
      <SelectField
        id="credential-provider"
        label="Proveedor de API"
        value={provider}
        options={Object.keys(contract.provider_categories).filter(
          (p) => p !== "piper",
        )}
        onChange={(event) => {
          if (allowNavigation()) setProvider(event.target.value);
        }}
      />
      <Credentials
        key={provider}
        scope="provider"
        owner={provider}
        kinds={[{ id: "api_key", label: "Clave de API" }]}
      />
    </>
  );
}
