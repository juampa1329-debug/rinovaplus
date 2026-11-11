import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AssistantChat } from "../modules/ai/pages/AssistantChat";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { aiRequest, defaultMedia, type AiSnapshot } from "../shared/aiSettings";

vi.mock("../shared/aiSettings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../shared/aiSettings")>()),
  aiRequest: vi.fn(),
}));
let snapshot: AiSnapshot;
let sent: Record<string, unknown>[];
let fail: boolean;
beforeEach(() => {
  sent = [];
  fail = false;
  snapshot = {
    revision: 5,
    credential_revision: 2,
    credential_storage_available: true,
    outbound_enabled: true,
    providers: [
      {
        id: "gemini",
        configured: true,
        environment_variable: "GEMINI_API_KEY",
        credential_source: "local",
      },
    ],
    settings: {
      enabled: true,
      provider: "gemini",
      model: "chat-model",
      fallback_enabled: false,
      fallback_model: "",
      backup_provider: null,
      backup_model: "",
      backup_fallback_model: "",
      system_prompt: "Responde con PRUEBA",
      max_tokens: 700,
      temperature: 0.5,
      brief_responses: true,
      split_responses: true,
      wait_seconds: 6,
      typing_ms: 2600,
      chars_per_message: 180,
      fragment_delay_ms: 9000,
      output_tokens: 700,
      recent_messages: 16,
      history_chars: 1200,
      show_typing: true,
      media: {
        ...defaultMedia,
        audio_model: "synthetic-audio-model",
        vision_model: "synthetic-vision-model",
      },
    },
  };
  vi.mocked(aiRequest).mockImplementation(async (path, _method, body) => {
    if (path === "settings") return structuredClone(snapshot);
    sent.push(body as Record<string, unknown>);
    if (fail) throw new Error("Proveedor no disponible. Intente nuevamente.");
    return {
      revision: snapshot.revision,
      credential_revision: snapshot.credential_revision,
      provider: "gemini",
      model: "chat-model",
      text: "PRUEBA: respuesta del asistente",
      attempts: [],
      plan: [],
    };
  });
});
afterEach(() => vi.clearAllMocks());

async function open() {
  const view = render(<AssistantChat active />, {
    wrapper: WorkspaceSessionProvider,
  });
  await screen.findByText(/Google \/ Gemini/);
  return view;
}
async function send(text: string) {
  fireEvent.change(screen.getByLabelText("Mensaje al asistente"), {
    target: { value: text },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enviar mensaje" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Mensaje al asistente")).toBeEnabled(),
  );
}

describe("real assistant conversation", () => {
  it("fetches generated audio with the local header and revokes the blob when leaving", async () => {
    sessionStorage.clear();
    snapshot.settings.media = { ...defaultMedia, voice_enabled: true };
    const createUrl = vi.fn().mockReturnValue("blob:test-audio");
    const revokeUrl = vi.fn();
    vi.stubGlobal(
      "URL",
      Object.assign(URL, {
        createObjectURL: createUrl,
        revokeObjectURL: revokeUrl,
      }),
    );
    const fetchAudio = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob(["RIFF1234WAVE"], { type: "audio/wav" }), {
        headers: { "Content-Type": "audio/wav" },
      }),
    );
    vi.mocked(aiRequest).mockImplementation(async (path) => {
      if (path === "settings") return structuredClone(snapshot);
      if (path === "conversation") return { conversation_id: "c".repeat(32) };
      return {
        revision: 5,
        credential_revision: 2,
        provider: "gemini",
        model: "chat-model",
        text: "Hola",
        attempts: [],
        plan: [],
        audio_id: "d".repeat(32),
        voice_status: "generated",
        voice_attempts: 1,
      };
    });
    const view = await open();
    await send("Audio");
    const player = await screen.findByLabelText("Nota de voz del asistente");
    expect(player).toHaveAttribute("src", "blob:test-audio");
    expect(player).not.toHaveAttribute("autoplay");
    expect(fetchAudio).toHaveBeenCalledWith(
      `/api/ai/media/${"d".repeat(32)}`,
      expect.objectContaining({
        headers: { "X-CRM-Local": "1" },
        cache: "no-store",
      }),
    );
    view.unmount();
    expect(revokeUrl).toHaveBeenCalledWith("blob:test-audio");
    fetchAudio.mockRestore();
  });
  it("uses a server conversation for voice and renders the quota result without automatic retry", async () => {
    sessionStorage.clear();
    snapshot.settings.media = {
      ...defaultMedia,
      voice_enabled: true,
      prefer_voice: true,
    };
    vi.mocked(aiRequest).mockImplementation(async (path, _method, body) => {
      if (path === "settings") return structuredClone(snapshot);
      if (path === "conversation") return { conversation_id: "a".repeat(32) };
      sent.push(body as Record<string, unknown>);
      return {
        revision: 5,
        credential_revision: 2,
        provider: "gemini",
        model: "chat-model",
        text: "Texto con límite",
        attempts: [],
        plan: [],
        voice_status: "limit_reached",
        voice_attempts: 2,
      };
    });
    await open();
    await send("Prueba de voz");
    expect(sent).toHaveLength(1);
    expect(sent[0]).toMatchObject({
      conversation_id: "a".repeat(32),
      search: "",
      attachment: null,
    });
    expect(sent[0].turn_id).toMatch(/^[a-f0-9]{32}$/);
    expect(screen.getByText(/Límite de voz alcanzado/)).toHaveTextContent(
      "Intentos de voz: 2",
    );
    expect(JSON.parse(sessionStorage.getItem("crm-ai-conversation")!)).toEqual({
      id: "a".repeat(32),
      binding: "5:2",
    });
  });
  it("sends an uploaded audio as a bounded explicit attachment and search only when selected", async () => {
    sessionStorage.clear();
    vi.mocked(aiRequest).mockImplementation(async (path, _method, body) => {
      if (path === "settings") return structuredClone(snapshot);
      if (path === "conversation") return { conversation_id: "b".repeat(32) };
      sent.push(body as Record<string, unknown>);
      return {
        revision: 5,
        credential_revision: 2,
        provider: "gemini",
        model: "chat-model",
        text: "Audio leído",
        attempts: [],
        plan: [],
        attachment_text: "Contenido ficticio",
      };
    });
    await open();
    const file = new File(["RIFF1234WAVE"], "prueba.wav", {
      type: "audio/wav",
    });
    await userEvent.upload(
      screen.getByLabelText("Adjuntar nota de voz o imagen"),
      file,
    );
    await send("Analiza la nota");
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toMatchObject({
      attachment: { mime_type: "audio/wav", data: btoa("RIFF1234WAVE") },
      search: "",
    });
    expect(screen.getByText(/Contenido del adjunto:/)).toHaveTextContent(
      "Contenido ficticio",
    );
    expect(screen.queryByText("prueba.wav")).not.toBeInTheDocument();
    const input = screen.getByLabelText(
      "Adjuntar nota de voz o imagen",
    ) as HTMLInputElement;
    expect(input.value).toBe("");
    expect(input.files).toHaveLength(0);
    await userEvent.upload(input, file);
    expect(input.files).toHaveLength(1);
    await send("Analiza otra vez");
    await waitFor(() => expect(sent).toHaveLength(2));
    expect(input.value).toBe("");
  });
  it("clears native attachment selection on remove and new conversation", async () => {
    await open();
    const input = screen.getByLabelText(
      "Adjuntar nota de voz o imagen",
    ) as HTMLInputElement;
    const file = new File(["RIFF1234WAVE"], "prueba.wav", {
      type: "audio/wav",
    });
    await userEvent.upload(input, file);
    fireEvent.click(screen.getByRole("button", { name: "Quitar adjunto" }));
    expect(input.value).toBe("");
    expect(input.files).toHaveLength(0);
    await userEvent.upload(input, file);
    fireEvent.click(screen.getByRole("button", { name: "Nueva conversación" }));
    expect(input.value).toBe("");
    expect(input.files).toHaveLength(0);
    expect(screen.queryByText("prueba.wav")).not.toBeInTheDocument();
  });
  it("preserves native attachment selection on a failed send", async () => {
    await open();
    const input = screen.getByLabelText(
      "Adjuntar nota de voz o imagen",
    ) as HTMLInputElement;
    const file = new File(["RIFF1234WAVE"], "prueba.wav", {
      type: "audio/wav",
    });
    await userEvent.upload(input, file);
    fail = true;
    await send("Analiza la nota");
    expect(input.files).toHaveLength(1);
    expect(input.files?.[0]).toBe(file);
    expect(screen.getByText("prueba.wav")).toBeInTheDocument();
  });
  it("loads metadata only, then sends two explicit turns with only its own history", async () => {
    await open();
    expect(sent).toHaveLength(0);
    await send("Recuerda violeta");
    await send("¿Qué color dije?");
    expect(sent[0]).toEqual({
      revision: 5,
      credential_revision: 2,
      prompt: "Recuerda violeta",
      history: [],
    });
    expect(sent[1]).toEqual({
      revision: 5,
      credential_revision: 2,
      prompt: "¿Qué color dije?",
      history: [
        { role: "user", content: "Recuerda violeta" },
        { role: "assistant", content: "PRUEBA: respuesta del asistente" },
      ],
    });
    expect(sent[0]).not.toHaveProperty("system_prompt");
    expect(screen.getAllByText("chat-model · Ajustes 5")).toHaveLength(2);
  });
  it("retains input on failure and retry appends the successful turn once", async () => {
    await open();
    fail = true;
    await send("Mensaje ficticio");
    expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue(
      "Mensaje ficticio",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Proveedor no disponible",
    );
    fail = false;
    await send("Mensaje ficticio");
    expect(screen.getByRole("log")).toHaveTextContent("Mensaje ficticio");
    expect(screen.getAllByText("Mensaje ficticio")).toHaveLength(1);
  });
  it("blocks inference while disabled or outbound is not permitted", async () => {
    snapshot.outbound_enabled = false;
    await open();
    fireEvent.change(screen.getByLabelText("Mensaje al asistente"), {
      target: { value: "Prueba" },
    });
    expect(
      screen.getByRole("button", { name: "Enviar mensaje" }),
    ).toBeDisabled();
    expect(sent).toHaveLength(0);
  });
  it("keeps successful history across navigation and resets it after config changes", async () => {
    const view = await open();
    await send("Violeta");
    view.rerender(<AssistantChat active={false} />);
    view.rerender(<AssistantChat active />);
    await screen.findByText("Violeta");
    snapshot.revision++;
    snapshot.settings.system_prompt = "Nueva instrucción";
    await send("Continuar");
    expect(sent).toHaveLength(1);
    expect(screen.queryByText("Violeta")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue(
      "Continuar",
    );
    await send("Continuar");
    expect(sent[1]).toMatchObject({ revision: 6, history: [] });
  });
  it("ignores a late provider response after reset", async () => {
    await open();
    let resolve!: (value: unknown) => void;
    vi.mocked(aiRequest).mockImplementation(async (path) => {
      if (path === "settings") return structuredClone(snapshot);
      return await new Promise((done) => {
        resolve = done;
      });
    });
    fireEvent.change(screen.getByLabelText("Mensaje al asistente"), {
      target: { value: "Prueba" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar mensaje" }));
    await waitFor(() => expect(resolve).toBeDefined());
    expect(
      screen.getByRole("button", { name: "Esperando respuesta…" }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Nueva conversación" }));
    resolve({ revision: 5, credential_revision: 2, text: "Late response" });
    await waitFor(() =>
      expect(screen.queryByText("Late response")).not.toBeInTheDocument(),
    );
    expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue("");
  });
  it("Enter sends while Shift Enter permits a newline", async () => {
    await open();
    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Mensaje al asistente"),
      "Prueba{Shift>}{Enter}{/Shift}línea",
    );
    expect(sent).toHaveLength(0);
    await user.type(screen.getByLabelText("Mensaje al asistente"), "{Enter}");
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0].prompt).toBe("Prueba\nlínea");
  });
});
