import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MediaSettingsFields } from "../modules/ai/components/MediaSettingsFields";
import { defaultMedia } from "../shared/aiSettings";

describe("voice settings controls", () => {
  it("renders actual account names, selected model and manual ID together", () => {
    const change = vi.fn();
    render(
      <MediaSettingsFields
        media={{
          ...defaultMedia,
          voice_id: "account-voice",
          voice_model: "tts",
        }}
        onChange={change}
        catalogs={{
          elevenlabs: {
            ready: true,
            local: false,
            voices: [
              { id: "account-voice", name: "Voz configurada", language: "es" },
            ],
            models: [{ id: "tts", name: "Modelo TTS" }],
          },
        }}
        geminiModels={[]}
        loadCatalog={vi.fn()}
        section="IA"
      />,
    );
    expect(screen.getByLabelText("Nombre visible de voz")).toHaveValue(
      "account-voice",
    );
    expect(
      screen.getByRole("option", { name: "Voz configurada · account-voice" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Voice ID manual opcional")).toHaveValue(
      "account-voice",
    );
    expect(screen.getByLabelText("Modelo de voz")).toHaveValue("tts");
    fireEvent.click(
      screen.getByLabelText("Si recibe nota de voz, responder con nota de voz"),
    );
    expect(change).toHaveBeenCalledWith(
      expect.objectContaining({ reply_audio_with_voice: true }),
    );
  });
  it("keeps cap disabled unless enabled and supports zero", () => {
    const change = vi.fn();
    const view = render(
      <MediaSettingsFields
        media={defaultMedia}
        onChange={change}
        catalogs={{}}
        geminiModels={[]}
        loadCatalog={vi.fn()}
        section="IA"
      />,
    );
    expect(
      screen.getByLabelText("Máximo de notas de voz por conversación"),
    ).toBeDisabled();
    view.rerender(
      <MediaSettingsFields
        media={{ ...defaultMedia, voice_limit_enabled: true, voice_limit: 0 }}
        onChange={change}
        catalogs={{}}
        geminiModels={[]}
        loadCatalog={vi.fn()}
        section="IA"
      />,
    );
    expect(
      screen.getByLabelText("Máximo de notas de voz por conversación"),
    ).toHaveValue(0);
    expect(
      screen.getByLabelText("Máximo de notas de voz por conversación"),
    ).toBeEnabled();
  });
  it("loads local catalog only on click and does not pretend Google has a model catalog", () => {
    const load = vi.fn().mockResolvedValue(undefined);
    render(
      <MediaSettingsFields
        media={{ ...defaultMedia, voice_provider: "google_tts" }}
        onChange={vi.fn()}
        catalogs={{}}
        geminiModels={[]}
        loadCatalog={load}
        section="APIs"
        outboundEnabled
      />,
    );
    expect(load).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Modelo de voz")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: "Cargar voces y modelos de Google Cloud TTS",
      }),
    );
    expect(load).toHaveBeenCalledWith("google_tts");
  });
  it("exposes Gemini analysis and all requested search providers", () => {
    render(
      <MediaSettingsFields
        media={defaultMedia}
        onChange={vi.fn()}
        catalogs={{}}
        geminiModels={[
          {
            id: "gemini-model",
            name: "Gemini",
            output_limit: 8000,
            temperature: true,
            max_temperature: 2,
          },
        ]}
        loadCatalog={vi.fn()}
        section="IA"
      />,
    );
    expect(
      screen.getAllByRole("option", { name: "Gemini · gemini-model" }),
    ).toHaveLength(2);
    for (const name of ["Tavily Search", "Brave Search API", "SerpAPI"])
      expect(screen.getByRole("option", { name })).toBeInTheDocument();
  });
});
