import { useState } from "react";
import { Button, Notice } from "../shared/ui";
import { useTask } from "./api";
import { useAdsResource } from "./adsResource";

type Model = { id: string; name: string };

export const catalogProviders = new Set([
  "gemini",
  "openrouter",
  "openai",
  "anthropic",
  "hermes",
  "kimi",
  "groq",
  "nvidia",
  "mistral",
  "xai",
]);

const brands: Record<string, string> = {
  gemini: "Gemini",
  google: "Google",
  openrouter: "OpenRouter",
  openai: "OpenAI",
  anthropic: "Anthropic",
  meta: "Meta",
  "meta-llama": "Meta",
  mistral: "Mistral",
  mistralai: "Mistral",
  nvidia: "NVIDIA",
  xai: "xAI",
  kimi: "Kimi",
  groq: "Groq",
  elevenlabs: "ElevenLabs",
  google_tts: "Google TTS",
};

export const providerLabel = (id: string) =>
  brands[id] ?? id.charAt(0).toUpperCase() + id.slice(1);

function modelGroup(provider: string, model: Model) {
  if (/\bgemma(?:[-\d]|\b)/i.test(model.id.split("/").at(-1) ?? ""))
    return "Gemma";
  return provider === "openrouter" && model.id.includes("/")
    ? providerLabel(model.id.split("/")[0])
    : providerLabel(provider);
}

export function LiveModelSelect({
  provider,
  category,
  value,
  onChange,
  label = "Seleccionar modelo",
  exclude = [],
}: {
  provider: string;
  category: string;
  value: string;
  onChange: (model: string) => void;
  label?: string;
  exclude?: string[];
}) {
  const task = useTask();
  const data = useAdsResource<{ items: Model[] }>(
    `provider-catalog/${provider}/${category}`,
  );
  const models = data.value?.items ?? null;
  const loading = task.busy || (!models && !data.error);
  const [family, setFamily] = useState("");
  const [query, setQuery] = useState("");
  const id = `model-${provider}-${category}`;
  const families = [
    ...new Set(models?.map((model) => modelGroup(provider, model))),
  ].sort();
  const filtered = (models ?? []).filter(
    (model) =>
      !exclude.includes(model.id) &&
      (!family || modelGroup(provider, model) === family) &&
      `${model.name} ${model.id}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  const isVisible = filtered.some((model) => model.id === value);
  return (
    <div className="institution-model-catalog">
      <Button
        type="button"
        variant="secondary"
        disabled={loading}
        aria-label={`Consultar modelos de ${providerLabel(provider)} para ${category}`}
        onClick={() =>
          void task.run(async () => {
            await data.reload();
          }, "")
        }
      >
        {loading
          ? "Consultando…"
          : models
            ? "Actualizar catálogo"
            : "Consultar modelos"}
      </Button>
      {task.notices}
      {data.error && !task.error && <Notice error>{data.error}</Notice>}
      {models && families.length > 1 && (
        <div className="field">
          <label htmlFor={`${id}-family`}>Familia de modelos</label>
          <select
            id={`${id}-family`}
            value={family}
            onChange={(event) => setFamily(event.target.value)}
          >
            <option value="">Todas las familias</option>
            {families.map((group) => (
              <option key={group}>{group}</option>
            ))}
          </select>
        </div>
      )}
      {models && models.length > 12 && (
        <div className="field">
          <label htmlFor={`${id}-query`}>Buscar modelo</label>
          <input
            id={`${id}-query`}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      )}
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <select
          id={id}
          value={value}
          disabled={!models || loading || !!data.error}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="" disabled>
            Selecciona un modelo disponible
          </option>
          {value && !isVisible && (
            <option value={value} disabled>
              {value} ·{" "}
              {models?.some((model) => model.id === value)
                ? "seleccionado"
                : "guardado"}
            </option>
          )}
          {families.map((group) => {
            const items = filtered.filter(
              (model) => modelGroup(provider, model) === group,
            );
            return (
              items.length > 0 && (
                <optgroup key={group} label={group}>
                  {items.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} · {model.id}
                    </option>
                  ))}
                </optgroup>
              )
            );
          })}
        </select>
        {models && filtered.length === 0 && (
          <small role="status">No hay modelos para esta búsqueda.</small>
        )}
      </div>
    </div>
  );
}
