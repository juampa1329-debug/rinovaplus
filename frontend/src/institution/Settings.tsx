import { useState } from "react";
import { useAdsResource } from "./adsResource";
import { Badge, Button, Field, Notice, SelectField } from "../shared/ui";
import { TypedFields } from "./Fields";
import { allowNavigation, useDraftGuard } from "./drafts";
import { useInstitution, useIntent, useTask } from "./api";
import type { Contract, Document, Setting } from "./api";
import {
  LiveModelSelect,
  LiveVoiceSelect,
  catalogProviders,
  providerLabel,
} from "./LiveModelSelect";

export const useResource = useAdsResource;
const categoryLabels: Record<string, string> = {
  text: "Texto",
  vision: "Visión",
  audio: "Audio",
  voice: "Voz",
  search: "Búsqueda",
};
export function ResourceState({ error }: { error: string }) {
  return <Notice error={!!error}>{error || "Cargando información…"}</Notice>;
}

export function SettingPage({
  section,
  contract,
  onSaved,
  liveModels = false,
}: {
  section: string;
  contract: Contract;
  onSaved?: () => Promise<unknown>;
  liveModels?: boolean;
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
        liveModels={liveModels}
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
  liveModels,
}: {
  initial: Setting;
  section: string;
  contract: Contract;
  reload: () => Promise<Setting>;
  onSaved?: () => Promise<unknown>;
  liveModels: boolean;
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
  const specs = (contract.fields[section] ?? []).filter(
    (spec) =>
      !(
        section === "ai" &&
        liveModels &&
        (spec.path.startsWith("media.") || spec.path === "voice_name")
      ),
  );
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
            ? liveModels
              ? "La atención automática sigue las instrucciones del agente, el modo IA/Humano y los permisos de cada canal. Requiere un modelo, credencial y presupuesto válidos."
              : "Los borradores de comentarios requieren un modelo, credencial y presupuesto válidos. Su envío necesita revisión humana."
            : "La ejecución de proveedores se habilitará con la integración de canales y agentes."}
        </Notice>
      )}
      {section === "ai" && liveModels && (
        <section className="panel">
          <h3>Voz y audios · ElevenLabs</h3>
          <p>
            Las voces, modelos, estabilidad, similitud, saludo y límites se
            configuran en un único lugar. Estos ajustes generales no activan
            otra voz ni sustituyen esa configuración.
          </p>
          <a className="button secondary" href="#/settings/voice">
            Abrir Voces y audios
          </a>
          <p>
            Gemini interpreta la nota entrante. ElevenLabs genera la respuesta
            hablada sólo si el hilo está en IA, pertenece al alcance
            seleccionado y tiene cupo; en los demás casos continúa por texto.
          </p>
        </section>
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
              <h3>
                {section === "ai" && liveModels && group === "Voz y multimedia"
                  ? "Análisis de imágenes"
                  : group}
              </h3>
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
              liveModels={liveModels}
            />
          )}
          {section === "ai" &&
            (liveModels ? (
              <>
                <section className="panel">
                  <h3>Selección desde el catálogo</h3>
                  <p>
                    Los modelos guardados se seleccionan en{" "}
                    <a href="#/settings/models">APIs y modelos</a>. RinovaPlus
                    carga las opciones de cada proveedor y conserva aquí sus
                    selecciones, sin escribir identificadores. Para las
                    respuestas automáticas de WhatsApp configura{" "}
                    <a href="#/settings/voice">Voces y audios</a>.
                  </p>
                </section>
                <LiveFallbacks value={draft} onChange={setDraft} />
              </>
            ) : (
              <Fallbacks value={draft} onChange={setDraft} />
            ))}
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
  liveModels,
}: {
  value: Document;
  onChange: (value: Document) => void;
  contract: Contract;
  liveModels: boolean;
}) {
  const entries = Object.entries(contract.provider_categories);
  const [providerFilter, setProviderFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const activeCategories = contract.provider_categories[providerFilter] ?? [];
  const currentCategory = categoryFilter || activeCategories[0];
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
      {liveModels && entries.length > 0 && (
        <SelectField
          id="catalog-provider"
          label="Proveedor del catálogo"
          options={[
            { value: "", label: "Selecciona un proveedor" },
            ...entries.map(([provider]) => ({
              value: provider,
              label: providerLabel(provider),
            })),
          ]}
          value={providerFilter}
          onChange={(event) => {
            setProviderFilter(event.target.value);
            setCategoryFilter("");
          }}
        />
      )}
      {liveModels && activeCategories.length > 1 && (
        <SelectField
          id="catalog-category"
          label="Tipo de modelo"
          value={currentCategory}
          options={activeCategories.map((category) => ({
            value: category,
            label: categoryLabels[category] ?? category,
          }))}
          onChange={(event) => setCategoryFilter(event.target.value)}
        />
      )}
      {entries
        .filter(([provider]) => !liveModels || provider === providerFilter)
        .map(([provider, categories]) => (
          <section className="panel" key={provider}>
            <h3>{providerLabel(provider)}</h3>
            {categories
              .filter((category) => !liveModels || category === currentCategory)
              .map((category) => {
                const current = selections.find(
                  (row) =>
                    row.provider === provider && row.category === category,
                );
                return (
                  <div className="institution-model-row" key={category}>
                    <Badge>{categoryLabels[category] ?? category}</Badge>
                    {liveModels &&
                    (catalogProviders.has(provider) ||
                      provider === "elevenlabs") ? (
                      <LiveModelSelect
                        provider={provider}
                        category={category}
                        value={current?.selected_model ?? ""}
                        onChange={(model) =>
                          change(provider, category, "selected_model", model)
                        }
                      />
                    ) : liveModels ? (
                      <p>
                        {category === "voice"
                          ? "Este motor utiliza la voz seleccionada; no necesitas escribir un modelo."
                          : "Este servicio usa su API de búsqueda; no necesitas escribir un identificador de modelo."}
                      </p>
                    ) : (
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
                    )}
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
                    {category === "voice" &&
                      (liveModels ? (
                        <LiveVoiceSelect
                          key={provider}
                          provider={provider}
                          value={current?.voice_id ?? ""}
                          onChange={(voice) =>
                            change(provider, category, "voice_id", voice)
                          }
                        />
                      ) : (
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
                      ))}
                  </div>
                );
              })}
          </section>
        ))}
    </>
  );
}
function LiveFallbacks({
  value,
  onChange,
}: {
  value: Document;
  onChange: (value: Document) => void;
}) {
  const [provider, setProvider] = useState("");
  const entries = (value.model_fallbacks_json ?? {}) as Record<
    string,
    string[]
  >;
  const selected = entries[provider] ?? [];
  const save = (models: string[]) =>
    onChange({
      ...value,
      model_fallbacks_json: { ...entries, [provider]: models },
    });
  const move = (index: number, step: number) => {
    const next = [...selected];
    [next[index], next[index + step]] = [next[index + step], next[index]];
    save(next);
  };
  return (
    <section className="panel">
      <h3>Modelos de respaldo</h3>
      <SelectField
        id="fallback-provider"
        label="Proveedor para el respaldo"
        value={provider}
        options={[
          { value: "", label: "Selecciona un proveedor" },
          ...[...catalogProviders].map((id) => ({
            value: id,
            label: providerLabel(id),
          })),
        ]}
        onChange={(event) => setProvider(event.target.value)}
      />
      {provider && (
        <>
          <ol className="institution-fallback-list">
            {selected.map((model, index) => (
              <li key={model}>
                <span>{model}</span>
                <div className="institution-actions">
                  <Button
                    type="button"
                    variant="quiet"
                    aria-label={`Subir ${model}`}
                    disabled={index === 0}
                    onClick={() => move(index, -1)}
                  >
                    Subir
                  </Button>
                  <Button
                    type="button"
                    variant="quiet"
                    aria-label={`Bajar ${model}`}
                    disabled={index === selected.length - 1}
                    onClick={() => move(index, 1)}
                  >
                    Bajar
                  </Button>
                  <Button
                    type="button"
                    variant="quiet"
                    aria-label={`Quitar ${model}`}
                    onClick={() =>
                      save(selected.filter((item) => item !== model))
                    }
                  >
                    Quitar
                  </Button>
                </div>
              </li>
            ))}
          </ol>
          <LiveModelSelect
            key={provider}
            provider={provider}
            category="text"
            value=""
            label="Añadir modelo de respaldo"
            exclude={selected}
            onChange={(model) => save([...selected, model])}
          />
        </>
      )}
    </section>
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
  application?: {
    name: string;
    client_id: string;
    provider: string;
    issuer_profile: string;
  } | null;
};
export function Credentials({
  scope,
  owner,
  kinds,
  onChanged,
  application,
}: {
  scope: "provider" | "channel" | "webhook";
  owner: string;
  kinds: { id: string; label: string }[];
  onChanged?: () => Promise<unknown>;
  application?: { clientId: string; issuerProfile: string; provider: string };
}) {
  const { call, session } = useInstitution(),
    data = useResource<{ items: Credential[] }>(`credentials/${scope}`),
    task = useTask(),
    intent = useIntent();
  const [values, setValues] = useState<Record<string, string>>({});
  const [savedSecret, setSavedSecret] = useState("");
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
        const saved =
          application && kind.id === "app_secret"
            ? (data.value?.items ?? []).filter(
                (row) =>
                  row.kind === "app_secret" &&
                  row.owner !== owner &&
                  row.application?.client_id === application.clientId &&
                  row.application.provider === application.provider &&
                  (row.application.issuer_profile ===
                    application.issuerProfile ||
                    (["meta_whatsapp", "facebook_login"].includes(
                      application.issuerProfile,
                    ) &&
                      ["meta_whatsapp", "facebook_login"].includes(
                        row.application.issuer_profile,
                      ))),
              )
            : [];
        return (
          <div key={kind.id}>
            {saved.length > 0 && (
              <div className="institution-secret-row">
                <SelectField
                  id={`saved-${owner}-${kind.id}`}
                  label="App Secret guardado"
                  value={
                    saved.some((row) => row.id === savedSecret)
                      ? savedSecret
                      : ""
                  }
                  disabled={!writable || task.busy || !!values[kind.id]}
                  options={[
                    { value: "", label: "Selecciona una clave de esta app" },
                    ...saved.map((row) => ({
                      value: row.id,
                      label: `${row.application!.name} · App ID ${row.application!.client_id} · versión ${row.version}`,
                    })),
                  ]}
                  onChange={(event) => setSavedSecret(event.target.value)}
                />
                <Button
                  variant="secondary"
                  disabled={
                    !writable ||
                    task.busy ||
                    !!values[kind.id] ||
                    !saved.some((row) => row.id === savedSecret)
                  }
                  onClick={() =>
                    void task.run(async () => {
                      const body = {
                        scope,
                        owner,
                        kind: kind.id,
                        source_secret_id: savedSecret,
                      };
                      await call("credentials", "PUT", {
                        ...body,
                        operation_id: intent.get(body),
                      });
                      setSavedSecret("");
                      intent.clear();
                      await data.reload();
                      await onChanged?.();
                    }, "App Secret guardado reutilizado en esta aplicación.")
                  }
                >
                  Usar App Secret guardado
                </Button>
              </div>
            )}
            {current?.application && kind.id === "app_secret" && (
              <p>
                Usando App Secret de {current.application.name} · App ID{" "}
                {current.application.client_id}.
              </p>
            )}
            <div className="institution-secret-row">
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
