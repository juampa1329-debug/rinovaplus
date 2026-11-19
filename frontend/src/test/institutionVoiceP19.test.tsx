import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VoiceWorkspace } from "../institution/VoiceWorkspace";
import { SessionBoundary, type Session } from "../institution/api";
import { ErrorFeedback } from "../institution/ErrorFeedback";
import { explainChannelError } from "../institution/channelErrors";

const session: Session = {
  session_id: "test",
  csrf_token: "csrf",
  actions: ["settings.ai.read", "settings.ai.write", "settings.providers.read"],
  user: {
    id: "test",
    email: "qa@example.invalid",
    full_name: "QA",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const base = {
  revision: 3,
  document: {
    enabled: true,
    system_prompt: "Orientar con datos revisados.",
    voice: {
      enabled: false,
      max_audios_per_conversation: 3,
      max_audio_seconds: 60,
      max_text_chars: 2000,
      long_reply_min_chars: 400,
      daily_character_limit: 20000,
      mode: "voice_notes_or_long",
      default_profile_id: "juampa",
      profiles: [
        {
          id: "juampa",
          name: "Juampa",
          voice_id: "voice1",
          model_id: "model1",
          active: true,
          schools: [],
          agent_ids: [],
        },
      ],
    },
  },
};
const respond = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });
function mock(
  extra?: (url: string, init?: RequestInit) => Response | undefined,
) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const value = extra?.(url, init);
      if (value) return value;
      if (url.endsWith("/private/audio"))
        return new Response(new Blob(["OggS"], { type: "audio/ogg" }));
      if (url.endsWith("/voice/usage"))
        return respond({ daily_characters: 0, daily_attempts: 0, history: [] });
      if (url.endsWith("/voice/conversations"))
        return respond({
          items: [
            {
              id: "10000000-0000-4000-8000-000000000001",
              label: "WhatsApp · CBN · termina en 5144 · Humano",
            },
          ],
        });
      if (url.endsWith("/api/v1/agents")) return respond({ agents: [] });
      if (url.endsWith("/settings/ai")) return respond(base);
      if (url.endsWith("/voice/catalog"))
        return respond({
          voices: [{ id: "voice1", name: "Juampa" }],
          models: [
            {
              id: "model1",
              name: "Modelo disponible",
              languages: [{ id: "es", name: "Spanish" }],
            },
          ],
        });
      throw new Error("Unexpected route: " + url);
    });
}
function mount(actions = session.actions) {
  return render(
    <ErrorFeedback explain={explainChannelError}>
      <SessionBoundary initial={{ ...session, actions }} expire={() => {}}>
        <VoiceWorkspace />
      </SessionBoundary>
    </ErrorFeedback>,
  );
}
const dialogDescriptors = Object.fromEntries(
  ["showModal", "close"].map((name) => [
    name,
    Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name),
  ]),
);
beforeEach(() => {
  vi.stubGlobal(
    "URL",
    Object.assign(URL, {
      createObjectURL: vi.fn(() => "blob:private-preview"),
      revokeObjectURL: vi.fn(),
    }),
  );
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  for (const [name, descriptor] of Object.entries(dialogDescriptors)) {
    if (descriptor)
      Object.defineProperty(HTMLDialogElement.prototype, name, descriptor);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name);
  }
});

it("shows explicit duration, conversation cap, fallback and existing profile without generating audio", async () => {
  const fetch = mock();
  mount();
  expect(
    await screen.findByRole("heading", { name: "Una voz con criterio" }),
  ).toBeVisible();
  expect(
    screen.getByLabelText("Máximo de audios por conversación"),
  ).toHaveValue(3);
  expect(
    screen.getByLabelText("Duración máxima por audio (segundos)"),
  ).toHaveValue(60);
  expect(
    screen.getByText(/0 = sin límite de duración configurado/),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Guardar configuración de voz" }),
  ).toBeDisabled();
  expect(fetch.mock.calls.some(([, init]) => init?.method === "POST")).toBe(
    false,
  );
});

it("saves zero duration and the chosen mode while preserving the agent system prompt", async () => {
  let saved: { document: typeof base.document } | null = null;
  mock((url, init) => {
    if (url.endsWith("/settings/ai") && init?.method === "PUT") {
      saved = JSON.parse(String(init.body));
      return respond({ ...saved, revision: 4 });
    }
  });
  mount();
  await screen.findByLabelText("Duración máxima por audio (segundos)");
  fireEvent.change(
    screen.getByLabelText("Duración máxima por audio (segundos)"),
    { target: { value: "0" } },
  );
  fireEvent.change(screen.getByLabelText("Usar audio"), {
    target: { value: "voice_notes_and_long" },
  });
  expect(
    screen.getByRole("button", { name: "Generar muestra" }),
  ).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar configuración de voz" }),
  );
  await waitFor(() => expect(saved).not.toBeNull());
  expect(saved!.document.voice.max_audio_seconds).toBe(0);
  expect(saved!.document.voice.mode).toBe("voice_notes_and_long");
  expect(saved!.document.system_prompt).toBe(base.document.system_prompt);
});

it("loads the catalog automatically and saves stability, similarity and a catalog language", async () => {
  let saved: {
    voice: {
      profiles: {
        stability: number;
        similarity_boost: number;
        language_code: string;
      }[];
    };
  } | null = null;
  const fetch = mock((url, init) => {
    if (url.endsWith("/settings/ai") && init?.method === "PUT") {
      saved = JSON.parse(String(init.body)).document;
      return respond(base);
    }
  });
  mount();
  const stability = await screen.findByRole("slider", { name: "Estabilidad" });
  fireEvent.change(stability, { target: { value: "0.25" } });
  fireEvent.change(screen.getByRole("slider", { name: "Similitud" }), {
    target: { value: "0.9" },
  });
  await waitFor(() => expect(screen.getByLabelText("Idioma")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Idioma"), {
    target: { value: "es" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar configuración de voz" }),
  );
  await waitFor(() => expect(saved).not.toBeNull());
  expect(saved!.voice.profiles[0]).toMatchObject({
    stability: 0.25,
    similarity_boost: 0.9,
    language_code: "es",
  });
  expect(
    fetch.mock.calls.some(([url]) => String(url).endsWith("/voice/catalog")),
  ).toBe(true);
});

it("requires selecting the authorized pilot chat before enabling voice", async () => {
  let saved: {
    voice: { scope: string; conversation_ids: string[]; enabled: boolean };
  } | null = null;
  mock((url, init) => {
    if (url.endsWith("/settings/ai") && init?.method === "PUT") {
      saved = JSON.parse(String(init.body)).document;
      return respond(base);
    }
  });
  mount([...session.actions, "inbox.read"]);
  fireEvent.click(await screen.findByLabelText(/Activar audios automáticos/));
  expect(
    screen.getByRole("button", { name: "Guardar configuración de voz" }),
  ).toBeDisabled();
  fireEvent.click(
    await screen.findByLabelText("WhatsApp · CBN · termina en 5144 · Humano"),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar configuración de voz" }),
  );
  await waitFor(() => expect(saved).not.toBeNull());
  expect(saved!.voice).toMatchObject({
    enabled: true,
    scope: "selected_conversations",
    conversation_ids: ["10000000-0000-4000-8000-000000000001"],
  });
});

it("compares four greeting tones without changing the saved voice and reuses paid intents", async () => {
  const requests: { greeting_tone: string; operation_id: string }[] = [];
  const fetch = mock((url, init) => {
    if (url.endsWith("/settings/ai"))
      return respond({
        ...base,
        document: {
          ...base.document,
          voice: {
            ...base.document.voice,
            profiles: [
              { ...base.document.voice.profiles[0], model_id: "eleven_v4" },
            ],
          },
        },
      });
    if (url.endsWith("/voice/catalog"))
      return respond({
        voices: [{ id: "voice1", name: "Juampa" }],
        models: [{ id: "eleven_v4", name: "Eleven v4" }],
      });
    if (url.endsWith("/voice/previews")) {
      requests.push(JSON.parse(String(init?.body)));
      return respond({
        state: "confirmed",
        audio_url: "/api/institution/voice/previews/private/audio",
        duration: 5,
        characters: 20,
      });
    }
  });
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Generar cuatro saludos" }),
  );
  await waitFor(() => expect(requests).toHaveLength(4));
  await screen.findByRole("heading", { name: "Animada" });
  expect(requests.map((v) => v.greeting_tone)).toEqual([
    "inherit",
    "warm",
    "calm",
    "upbeat",
  ]);
  const firstIds = requests.map((v) => v.operation_id);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Generar cuatro saludos" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Generar cuatro saludos" }),
  );
  await waitFor(() => expect(requests).toHaveLength(8));
  expect(requests.slice(4).map((v) => v.operation_id)).toEqual(firstIds);
  expect(fetch.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(
    false,
  );
});

it("stops the comparison after an uncertain result to avoid additional paid generations", async () => {
  let paid = 0;
  mock((url) => {
    if (url.endsWith("/settings/ai"))
      return respond({
        ...base,
        document: {
          ...base.document,
          voice: {
            ...base.document.voice,
            profiles: [
              { ...base.document.voice.profiles[0], model_id: "eleven_v4" },
            ],
          },
        },
      });
    if (url.endsWith("/voice/catalog"))
      return respond({
        voices: [],
        models: [{ id: "eleven_v4", name: "Eleven v4" }],
      });
    if (url.endsWith("/voice/previews")) {
      paid++;
      return respond({ state: "uncertain", audio_url: null, characters: 20 });
    }
  });
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Generar cuatro saludos" }),
  );
  await screen.findByRole("heading", { name: "No se pudo generar el audio" });
  expect(paid).toBe(1);
});

it("reuses the preview intent to avoid duplicate charges and renders a private audio player", async () => {
  const ids: string[] = [];
  mock((url, init) => {
    if (url.endsWith("/voice/previews")) {
      ids.push(JSON.parse(String(init?.body)).operation_id);
      return respond({
        state: "confirmed",
        audio_url: "/api/institution/voice/previews/private/audio",
        duration: 6,
        characters: 30,
      });
    }
  });
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Generar muestra" }),
  );
  expect(
    await screen.findByLabelText("Muestra de voz generada"),
  ).toHaveAttribute("src", "blob:private-preview");
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Generar muestra" }),
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Generar muestra" }));
  await waitFor(() => expect(ids).toHaveLength(2));
  expect(ids[0]).toBe(ids[1]);
});

it("explains insufficient balance in the shared error popup", async () => {
  mock((url) =>
    url.endsWith("/voice/previews")
      ? respond({ detail: "voice_insufficient_credits" }, 502)
      : undefined,
  );
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Generar muestra" }),
  );
  expect(
    await screen.findByRole("heading", { name: "No se pudo generar el audio" }),
  ).toBeVisible();
  expect(
    screen.getAllByText(/ElevenLabs no tiene saldo suficiente/).length,
  ).toBeGreaterThan(0);
});

it("read-only users cannot enable, save or generate paid previews", async () => {
  const fetch = mock();
  mount(["settings.ai.read"]);
  expect(
    await screen.findByLabelText(/Activar audios automáticos/),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Generar muestra" }),
  ).toBeDisabled();
  expect(fetch.mock.calls.some(([, init]) => init?.method === "POST")).toBe(
    false,
  );
});
