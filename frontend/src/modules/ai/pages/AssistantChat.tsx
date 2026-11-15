import { useEffect, useRef, useState } from "react";
import {
  aiRequest,
  providerNames,
  type AiSnapshot,
  type AiTestResult,
  defaultMedia,
} from "../../../shared/aiSettings";
import { Button, Notice, TextArea, SelectField } from "../../../shared/ui";
import { useWorkspaceState } from "../../../shared/workspaceSession";

type Message = {
  role: "user" | "assistant";
  content: string;
  model?: string;
  revision?: number;
  audioId?: string;
  voiceStatus?: string;
  voiceError?: string;
  voiceAttempts?: number;
  institutionalSources?: { id: string; title: string; source_kind: string }[];
  institutionalPeriod?: { label: string };
  assistantMemory?: Partial<Record<"program_interest" | "schedule_availability", { value: string }>>;
  sources?: {
    title: string;
    url: string;
    image_url: string;
    content: string;
  }[];
};
type ChatResult = AiTestResult & {
  credential_revision: number;
  audio_id?: string;
  voice_status?: string;
  voice_error?: string;
  voice_attempts?: number;
  sources?: Message["sources"];
  attachment_text?: string;
  institutional_sources?: Message["institutionalSources"];
  institutional_period?: Message["institutionalPeriod"];
  assistant_memory?: Message["assistantMemory"];
};
function freshId() {
  return crypto.randomUUID().replaceAll("-", "");
}
export function AudioReply({ identifier }: { identifier: string }) {
  const [url, setUrl] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const abort = new AbortController();
    let live = true;
    let objectUrl = "";
    void fetch(`/api/ai/media/${identifier}`, {
      headers: { "X-CRM-Local": "1" },
      cache: "no-store",
      signal: abort.signal,
    })
      .then(async (response) => {
        if (
          !response.ok ||
          !response.headers.get("content-type")?.startsWith("audio/")
        )
          throw new Error();
        const blob = await response.blob();
        if (!live) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (live) setFailed(true);
      });
    return () => {
      live = false;
      abort.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [identifier]);
  return failed ? (
    <p>
      El audio temporal venció o no pudo descargarse. El texto permanece
      disponible.
    </p>
  ) : url ? (
    <audio controls src={url} aria-label="Nota de voz del asistente" />
  ) : (
    <p role="status">Cargando nota de voz…</p>
  );
}
async function readAttachment(file: File) {
  if (file.size > 4_000_000)
    throw new Error("El adjunto supera el máximo de 4 MB.");
  const mime = file.type === "audio/x-wav" ? "audio/wav" : file.type;
  if (
    ![
      "audio/wav",
      "audio/mpeg",
      "audio/ogg",
      "audio/flac",
      "audio/webm",
      "image/png",
      "image/jpeg",
      "image/webp",
    ].includes(mime)
  )
    throw new Error("Use WAV, MP3, OGG, FLAC, WebM, PNG, JPEG o WebP.");
  const data = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  });
  return { mime_type: mime, data };
}
function binding(snapshot: AiSnapshot) {
  return `${snapshot.revision}:${snapshot.credential_revision}`;
}
function blockReason(snapshot: AiSnapshot) {
  if (!snapshot.settings.enabled)
    return "Habilite y guarde IA en Ajustes > IA para conversar.";
  if (!snapshot.outbound_enabled)
    return "Permita las consultas externas en Ajustes > APIs para conversar.";
  if (
    !snapshot.providers.find((item) => item.id === snapshot.settings.provider)
      ?.configured
  )
    return "Guarde la API key del proveedor activo en Ajustes > APIs.";
  if (!snapshot.settings.model)
    return "Seleccione y guarde un modelo en Ajustes > APIs.";
  return "";
}

function attachmentBlockReason(snapshot: AiSnapshot, file: File | null) {
  if (!file) return "";
  const media = snapshot.settings.media ?? defaultMedia;
  if (file.type.startsWith("audio/") && !media.audio_model)
    return "Seleccione y guarde un modelo de análisis de audio en Ajustes > IA antes de enviar esta nota de voz.";
  if (file.type.startsWith("image/") && !media.vision_model)
    return "Seleccione y guarde un modelo de visión en Ajustes > IA antes de enviar esta imagen.";
  return "";
}

const voiceErrors: Record<string, string> = {
  voice_account_restricted:
    "ElevenLabs restringió temporalmente el uso de esta cuenta. Revise el panel o contacte con su soporte; el texto se conserva.",
  voice_insufficient_credits:
    "ElevenLabs indicó créditos insuficientes. Revise los créditos de su cuenta antes de volver a generar audio.",
  voice_payment_required:
    "ElevenLabs requiere habilitar el pago o un plan compatible para esta síntesis. Revise su cuenta; el texto se conserva.",
  voice_insufficient_permissions:
    "La clave de ElevenLabs no tiene los permisos necesarios para sintetizar audio. Revise sus permisos de Text to Speech.",
  voice_access_denied:
    "ElevenLabs denegó el uso de la voz elegida. Revise el acceso a esa voz en su cuenta o seleccione otra voz disponible.",
  voice_model_access_denied:
    "ElevenLabs denegó el modelo de síntesis elegido. Revise el acceso de su cuenta o seleccione otro modelo.",
  voice_invalid_key:
    "ElevenLabs rechazó la API key. Reemplácela desde Ajustes > APIs; no la envíe por chat.",
  voice_invalid_parameters:
    "ElevenLabs rechazó los parámetros de síntesis. Revise la voz y el modelo guardados en Ajustes > IA.",
  voice_forbidden:
    "ElevenLabs denegó esta síntesis (HTTP 403). Revise los permisos y el acceso de su cuenta a la voz y al modelo.",
  provider_key_missing:
    "Falta la credencial del proveedor de voz. Guárdela en Ajustes > APIs.",
  voice_catalog_required:
    "La voz guardada no está disponible. Cargue el catálogo y seleccione una voz en Ajustes > IA.",
  voice_model_required:
    "Seleccione y guarde un modelo de voz disponible en Ajustes > IA.",
  media_provider_rejected:
    "El proveedor de voz rechazó la solicitud. Revise la credencial, permisos y disponibilidad de su cuenta.",
  media_provider_unavailable:
    "El proveedor de voz no está disponible temporalmente. El texto se conserva.",
  provider_timeout_or_network:
    "El proveedor de voz no respondió a tiempo. El intento consumió un cupo; no se reenvía automáticamente.",
  provider_invalid_audio:
    "El proveedor no devolvió un audio compatible. El texto se conserva.",
  voice_text_too_large:
    "La respuesta supera el límite de síntesis de voz. Configure respuestas más breves en Ajustes > IA.",
  piper_unavailable:
    "Piper no está disponible. Revise la configuración o elija otro proveedor.",
};

export function AssistantChat({ active }: { active: boolean }) {
  const [, setSettingsSection] = useWorkspaceState("settingsSection");
  const [snapshot, setSnapshot] = useState<AiSnapshot | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [turnBlocked, setTurnBlocked] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [attachment, setAttachment] = useState<File | null>(null);
  const attachmentInput = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const conversation = useRef<{ id: string; binding: string } | null>(null);
  const mediaTurn = useRef<string | null>(null);
  const epoch = useRef(0);
  const pending = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const currentBinding = useRef<string | null>(null);

  function openSettings(section: "IA" | "APIs") {
    setSettingsSection(section);
    window.location.hash = "/settings";
  }

  function clearAttachment() {
    setAttachment(null);
    if (attachmentInput.current) attachmentInput.current.value = "";
  }

  function newConversation(preserveContent = false) {
    epoch.current++;
    controller.current?.abort();
    pending.current = false;
    setBusy(false);
    setMessages([]);
    if (!preserveContent) {
      setDraft("");
      clearAttachment();
    }
    conversation.current = null;
    mediaTurn.current = null;
    setTurnBlocked(false);
    try {
      sessionStorage.removeItem("crm-ai-conversation");
    } catch {
      /* Optional local metadata. */
    }
    setError("");
    setNotice(
      preserveContent
        ? "Conversación nueva preparada. El mensaje y el adjunto se conservan; pulse Enviar para realizar un nuevo intento."
        : "Conversación descartada.",
    );
  }

  function acceptSnapshot(next: AiSnapshot) {
    const changed =
      currentBinding.current !== null &&
      currentBinding.current !== binding(next);
    if (changed) {
      setTurnBlocked(false);
      setMessages([]);
      conversation.current = null;
      mediaTurn.current = null;
      setNotice(
        "Los ajustes o las credenciales cambiaron. Se inició una conversación nueva con la configuración guardada.",
      );
    }
    currentBinding.current = binding(next);
    setSnapshot(next);
    return changed;
  }

  useEffect(() => {
    const version = ++epoch.current;
    pending.current = false;
    if (active) {
      void Promise.resolve()
        .then(() => {
          if (epoch.current !== version) return;
          setBusy(false);
          setLoading(true);
          setError("");
          return aiRequest<AiSnapshot>("settings");
        })
        .then((next) => {
          if (epoch.current !== version || !next) return;
          acceptSnapshot(next);
        })
        .catch((reason) => {
          if (epoch.current === version) setError((reason as Error).message);
        })
        .finally(() => {
          if (epoch.current === version) setLoading(false);
        });
    }
    return () => {
      epoch.current = version + 1;
      controller.current?.abort();
    };
  }, [active, refresh]);

  async function send() {
    if (
      pending.current ||
      turnBlocked ||
      !snapshot ||
      (!draft.trim() && !attachment) ||
      blockReason(snapshot)
    )
      return;
    const attachmentBlocked = attachmentBlockReason(snapshot, attachment);
    if (attachmentBlocked) {
      setError(attachmentBlocked);
      return;
    }
    pending.current = true;
    setBusy(true);
    setError("");
    const version = epoch.current;
    const prompt = draft.trim() || "Responde al adjunto.";
    const abort = new AbortController();
    controller.current = abort;
    try {
      const latest = await aiRequest<AiSnapshot>(
        "settings",
        "GET",
        undefined,
        abort.signal,
      );
      if (version !== epoch.current) return;
      if (acceptSnapshot(latest)) {
        setError(
          "Revise la configuración actual y vuelva a enviar su mensaje para usarla.",
        );
        return;
      }
      const blocked = blockReason(latest);
      if (blocked) {
        setError(blocked);
        return;
      }
      const attachmentBlocked = attachmentBlockReason(latest, attachment);
      if (attachmentBlocked) {
        setError(attachmentBlocked);
        return;
      }
      const history = latest.settings.recent_messages
        ? messages
            .slice(-latest.settings.recent_messages)
            .map(({ role, content }) => ({
              role,
              content: content.slice(-latest.settings.history_chars),
            }))
        : [];
      const media = latest.settings.media ?? defaultMedia;
      const useMedia = media.voice_enabled || !!attachment || !!search;
      let mediaBody = {};
      if (
        useMedia ||
        latest.settings.provider === "kimi" ||
        latest.settings.backup_provider === "kimi"
      ) {
        if (
          !conversation.current ||
          conversation.current.binding !== binding(latest)
        ) {
          try {
            const stored = JSON.parse(
              sessionStorage.getItem("crm-ai-conversation") ?? "null",
            );
            if (
              stored?.binding === binding(latest) &&
              /^[a-f0-9]{32}$/.test(stored.id)
            )
              conversation.current = stored;
          } catch {
            /* Storage is optional; no credentials are stored. */
          }
        }
        if (
          !conversation.current ||
          conversation.current.binding !== binding(latest)
        ) {
          const created = await aiRequest<{ conversation_id: string }>(
            "conversation",
            "POST",
            {},
            abort.signal,
          );
          conversation.current = {
            id: created.conversation_id,
            binding: binding(latest),
          };
          try {
            sessionStorage.setItem(
              "crm-ai-conversation",
              JSON.stringify(conversation.current),
            );
          } catch {
            /* The server still owns the budget. */
          }
        }
        mediaBody = { conversation_id: conversation.current.id };
        if (useMedia) {
          mediaTurn.current ??= freshId();
          mediaBody = {
            conversation_id: conversation.current.id,
            turn_id: mediaTurn.current,
            attachment: attachment ? await readAttachment(attachment) : null,
            search,
          };
        }
      }
      const result = await aiRequest<ChatResult>(
        useMedia ? "media-chat" : "chat",
        "POST",
        {
          revision: latest.revision,
          credential_revision: latest.credential_revision,
          prompt,
          history,
          ...mediaBody,
        },
        abort.signal,
      );
      if (version !== epoch.current) return;
      const after = await aiRequest<AiSnapshot>(
        "settings",
        "GET",
        undefined,
        abort.signal,
      );
      if (version !== epoch.current) return;
      if (
        acceptSnapshot(after) ||
        result.revision !== after.revision ||
        result.credential_revision !== after.credential_revision
      ) {
        setError(
          "La configuración cambió durante la respuesta. El mensaje no se añadió; vuelva a enviarlo con los ajustes actuales.",
        );
        return;
      }
      setMessages(
        (previous) =>
          [
            ...previous,
            { role: "user", content: prompt },
            {
              role: "assistant",
              content: result.text,
              model: result.model,
              revision: result.revision,
              audioId: result.audio_id,
              voiceStatus: result.voice_status,
              voiceError: result.voice_error,
              voiceAttempts: result.voice_attempts,
              sources: result.sources,
              institutionalSources: result.institutional_sources,
              institutionalPeriod: result.institutional_period,
              assistantMemory: result.assistant_memory,
            },
          ].slice(-60) as Message[],
      );
      setDraft("");
      clearAttachment();
      mediaTurn.current = null;
      setNotice(
        result.attachment_text
          ? `Contenido del adjunto: ${result.attachment_text}`
          : "",
      );
    } catch (reason) {
      if (version === epoch.current) {
        if ((reason as Error & { code?: string }).code === "turn_already_started")
          setTurnBlocked(true);
        setError((reason as Error).message);
      }
    } finally {
      if (version === epoch.current) {
        pending.current = false;
        setBusy(false);
      }
    }
  }

  if (!active) return null;
  const blocked = snapshot
    ? turnBlocked
      ? "Este turno ya se consumió y no se vuelve a enviar. Inicie una conversación nueva para realizar otro intento; puede conservar el mensaje y el adjunto."
      : blockReason(snapshot) || attachmentBlockReason(snapshot, attachment)
    : "";
  return (
    <section
      className="panel assistant-chat"
      aria-labelledby="assistant-chat-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="assistant-chat-title">Conversar con el asistente</h2>
          <p>
            Asistente virtual de RinovaPlus · Conexión real al proveedor
            configurado
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={!snapshot || loading}
          onClick={() => newConversation()}
        >
          Nueva conversación
        </Button>
      </div>
      <Button
        variant="quiet"
        disabled={busy || loading}
        onClick={() => setRefresh((value) => value + 1)}
      >
        Actualizar configuración guardada
      </Button>
      {loading && <p role="status">Cargando configuración guardada…</p>}
      {snapshot && (
        <>
          <p>
            {providerNames[snapshot.settings.provider]} ·{" "}
            <strong>{snapshot.settings.model || "Sin modelo"}</strong> · Ajustes{" "}
            {snapshot.revision}
          </p>
          <details className="scope-note">
            <summary>System prompt guardado y límites</summary>
            <p className="assistant-prompt">
              {snapshot.settings.system_prompt ||
                "Sin preferencias adicionales"}
            </p>
            <p>
              La plataforma añade la identidad virtual y las restricciones
              institucionales. Historial: hasta{" "}
              {snapshot.settings.recent_messages} mensajes y{" "}
              {snapshot.settings.history_chars} caracteres por mensaje. Los
              cambios requieren una conversación nueva.
            </p>
            <p>El programa y la disponibilidad declarados se conservan en esta sesión hasta 24 horas, incluso al recargar. Nueva conversación inicia un contexto separado. La disponibilidad personal no confirma el horario de clases.</p>
          </details>
        </>
      )}
      <p className="scope-text" id="assistant-chat-scope">
        Al enviar, el proveedor recibe su mensaje, el historial acotado de esta
        conversación y las instrucciones configuradas.
      </p>
      {notice && <Notice>{notice}</Notice>}
      {error && <Notice error>{error}</Notice>}
      <div
        role="log"
        aria-label="Conversación con IA"
        aria-live="polite"
        aria-relevant="additions"
        className="assistant-chat-log"
      >
        {messages.length === 0 && (
          <p className="scope-text">
            Escriba un mensaje para iniciar la conversación.
          </p>
        )}
        {messages.map((message, index) => (
          <article
            className={`assistant-chat-message ${message.role}`}
            key={index}
          >
            <strong>
              {message.role === "user" ? "Usted" : "Asistente virtual"}
            </strong>
            <p>{message.content}</p>
            {message.audioId && <AudioReply identifier={message.audioId} />}
            {message.voiceStatus && (
              <small>
                {(
                  {
                    disabled: "Voz deshabilitada",
                    limit_reached: "Límite de voz alcanzado",
                    text_selected: "Respuesta en texto elegida",
                    generated: "Nota de voz generada",
                    failed_text_preserved: "La voz falló; se conserva el texto",
                  } as Record<string, string>
                )[message.voiceStatus] ?? "Voz no disponible"}{" "}
                · Intentos de voz: {message.voiceAttempts ?? 0}
              </small>
            )}
            {message.voiceError && (
              <Notice error>
                {voiceErrors[message.voiceError] ??
                  "No se pudo generar la nota de voz. Revise la selección de voz y el estado del proveedor; el texto se conserva."}
                <div className="actions">
                  <Button
                    variant="secondary"
                    onClick={() =>
                      openSettings(
                        message.voiceError === "provider_key_missing"
                          ? "APIs"
                          : "IA",
                      )
                    }
                  >
                    Configurar voz
                  </Button>
                </div>
              </Notice>
            )}
            {message.voiceStatus === "limit_reached" && (
              <p>
                El límite de notas de esta conversación se alcanzó. Puede
                continuar en texto o revisar el límite en Ajustes &gt; IA.
              </p>
            )}
            {!!message.sources?.length && (
              <ul aria-label="Fuentes externas">
                {message.sources.map((source, index) => (
                  <li key={index}>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {source.title}
                    </a>
                    {source.image_url && (
                      <>
                        {" "}
                        ·{" "}
                        <a
                          href={source.image_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Ver imagen externa
                        </a>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {message.model && (
              <small>
                {message.model} · Ajustes {message.revision}
              </small>
            )}
            {!!message.institutionalSources?.length && <details><summary>Fuentes institucionales · {message.institutionalPeriod?.label}</summary><ul>{message.institutionalSources.map((source) => <li key={source.id}>{source.title} · {source.source_kind === "sql" ? "Fuente institucional" : "Documento complementario"}</li>)}</ul></details>}
            {(message.assistantMemory?.program_interest || message.assistantMemory?.schedule_availability) && <details><summary>Datos declarados en esta sesión</summary>{message.assistantMemory.program_interest && <p>Programa de interés: {message.assistantMemory.program_interest.value}</p>}{message.assistantMemory.schedule_availability && <p>Disponibilidad personal: {message.assistantMemory.schedule_availability.value}. No confirma el horario de clases.</p>}</details>}
          </article>
        ))}
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <TextArea
          id="assistant-chat-message"
          label="Mensaje al asistente"
          value={draft}
          maxLength={2000}
          disabled={busy}
          aria-describedby="assistant-chat-scope assistant-chat-limit"
          onChange={(event) => {
            setDraft(event.target.value);
            mediaTurn.current = null;
          }}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              void send();
            }
          }}
        />
        <div className="form-grid">
          <div className="field">
            <label htmlFor="assistant-attachment">
              Adjuntar nota de voz o imagen
            </label>
            <input
              id="assistant-attachment"
              type="file"
              ref={attachmentInput}
              accept="audio/wav,audio/mpeg,audio/ogg,audio/flac,audio/webm,image/png,image/jpeg,image/webp"
              disabled={busy}
              onChange={(event) => {
                setAttachment(event.target.files?.[0] ?? null);
                mediaTurn.current = null;
              }}
            />
            <small>
              Máximo 4 MB. Gemini recibe el archivo para transcribir o analizar.
            </small>
          </div>
          <SelectField
            id="assistant-search"
            label="Búsqueda externa para este mensaje"
            value={search}
            disabled={busy}
            options={[
              { value: "", label: "Sin búsqueda" },
              { value: "web", label: "Buscar en la web" },
              { value: "images", label: "Buscar imágenes" },
            ]}
            onChange={(event) => {
              setSearch(event.target.value);
              mediaTurn.current = null;
            }}
          />
        </div>
        {attachment && (
          <p>
            {attachment.name}{" "}
            <Button variant="quiet" disabled={busy} onClick={clearAttachment}>
              Quitar adjunto
            </Button>
          </p>
        )}
        <small id="assistant-chat-limit">
          {draft.length} / 2000 caracteres · Enter envía; Shift + Enter crea una
          línea.
        </small>
        <div className="scope-note" aria-label="Estado para enviar">
          {turnBlocked && (
            <Button
              variant="secondary"
              disabled={busy || loading}
              onClick={() => newConversation(true)}
            >
              Nueva conversación y conservar contenido
            </Button>
          )}
          <p role="status">
            {loading
              ? "Cargando configuración guardada…"
              : !snapshot
                ? "No hay configuración disponible. Actualice la configuración guardada."
                : blocked ||
                  (!draft.trim() && !attachment
                    ? "Conexión preparada. Escriba un mensaje o adjunte un archivo para habilitar Enviar."
                    : "Configuración preparada para enviar este mensaje.")}
          </p>
          {snapshot && (
            <p>
              IA {snapshot.settings.enabled ? "habilitada" : "deshabilitada"} ·
              Consultas externas{" "}
              {snapshot.outbound_enabled ? "autorizadas" : "deshabilitadas"} ·
              Voz{" "}
              {(snapshot.settings.media ?? defaultMedia).voice_enabled
                ? (snapshot.settings.media ?? defaultMedia).prefer_voice
                  ? "activada, preferir nota de voz"
                  : "activada, la IA decide si responde en audio"
                : "deshabilitada"}
              .
            </p>
          )}
          <div className="actions">
            <Button
              variant={
                snapshot && !snapshot.settings.enabled ? "primary" : "quiet"
              }
              disabled={busy}
              onClick={() => openSettings("IA")}
            >
              Configurar IA y voz
            </Button>
            <Button
              variant="quiet"
              disabled={busy}
              onClick={() => openSettings("APIs")}
            >
              Configurar APIs y modelos
            </Button>
          </div>
        </div>
        <div className="actions">
          <Button
            type="submit"
            disabled={
              busy ||
              loading ||
              !snapshot ||
              !!blocked ||
              (!draft.trim() && !attachment)
            }
          >
            {busy ? "Esperando respuesta…" : "Enviar mensaje"}
          </Button>
        </div>
        {busy && (
          <p role="status">
            Consultando al proveedor. La primera respuesta tras reiniciar
            también valida el catálogo de modelos.
          </p>
        )}
      </form>
    </section>
  );
}
