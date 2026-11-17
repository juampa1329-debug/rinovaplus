import { useContext, useEffect, useId, useRef, useState } from "react";
import { Button } from "../shared/ui";
import { Icon } from "../shared/Icon";
import { operationFailure, useInstitution, useIntent, useTask } from "./api";
import { useDraftGuard } from "./drafts";
import { ErrorFeedbackContext } from "./ErrorFeedback";
import {
  clockTime,
  useVoiceRecording,
  VoicePlayer,
  Waveform,
} from "./VoiceNote";

export type Attachment = {
  id: string;
  name: string;
  kind: string;
  state: string;
  mime?: string;
};
const options = [
  { id: "image", label: "Imagen", accepts: ".png,.jpg,.jpeg" },
  { id: "video", label: "Video", accepts: ".mp4,.mov,.webm" },
  { id: "audio", label: "Audio", accepts: ".ogg,.mp3,.wav,.m4a,.webm" },
  { id: "sticker", label: "Sticker", accepts: ".webp" },
  {
    id: "document",
    label: "Documento",
    accepts: ".pdf,.txt,.docx,.xlsx,.pptx",
  },
] as const;
type Category = (typeof options)[number];

function encode(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("No se pudo leer el archivo."));
    reader.readAsDataURL(file);
  });
}

export function MediaUpload({
  conversation,
  channel,
  value,
  onChange,
  onBusy,
}: {
  conversation: string;
  channel?: string;
  value: Attachment | null;
  onChange: (value: Attachment | null) => void;
  onBusy: (busy: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<{
    file: File;
    category: Category["id"];
  } | null>(null);
  const [preparing, setPreparing] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const category = useRef<Category | null>(null);
  const generation = useRef(0);
  const busy = useRef(false);
  const clip = useRef<HTMLButtonElement>(null);
  const id = useId();
  const { call } = useInstitution();
  const report = useContext(ErrorFeedbackContext);
  const intent = useIntent();
  const audioEnabled = channel !== "tiktok";
  useDraftGuard(!!pending || !!value || preparing);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );

  async function upload(file: File, kind: Category["id"]) {
    if (busy.current) return;
    setPending(null);
    const sizeLimit =
      kind === "sticker"
        ? 100_000
        : channel === "tiktok"
          ? 3_000_000
          : 5_000_000;
    if (!file.size || file.size > sizeLimit) {
      const limit =
        kind === "sticker" ? "100 KB" : channel === "tiktok" ? "3 MB" : "5 MB";
      report?.(
        {
          code: "inbox_file_size",
          message: `Selecciona un archivo que pese entre 1 byte y ${limit}.`,
        },
        clip.current,
      );
      return;
    }
    if (kind === "sticker" && !/\.webp$/i.test(file.name)) {
      report?.({ code: "media_sticker_invalid", message: "" }, clip.current);
      return;
    }
    const current = generation.current;
    setPending({ file, category: kind });
    busy.current = true;
    setPreparing(true);
    try {
      const content_base64 = await encode(file);
      if (current !== generation.current) return;
      const body = {
        conversation_id: conversation,
        filename: file.name,
        content_base64,
        ...(kind === "video" ? { kind } : {}),
      };
      const attached = await call<Attachment>("media/upload", "POST", {
        ...body,
        operation_id: intent.get(body),
      });
      if (current === generation.current) {
        onChange(attached);
        setPending(null);
      }
    } catch (error) {
      if (current === generation.current)
        report?.(
          operationFailure(error, "El archivo no se pudo preparar."),
          clip.current,
        );
    } finally {
      if (current === generation.current) {
        busy.current = false;
        setPreparing(false);
      }
    }
  }

  const voice = useVoiceRecording(
    (file) => void upload(file, "audio"),
    (message) => report?.({ code: "inbox_recording_failed", message }),
  );
  const capturing = voice.status !== "idle";
  useDraftGuard(capturing);
  useEffect(() => {
    onBusy(capturing || preparing || !!pending);
    return () => onBusy(false);
  }, [capturing, preparing, pending, onBusy]);
  const supported = options.filter(({ id }) =>
    channel === "tiktok"
      ? id === "image"
      : id !== "sticker" || !channel || ["local", "whatsapp"].includes(channel),
  );
  return (
    <div
      className="inbox-attachment-toolbar"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          clip.current?.focus();
        }
      }}
    >
      <div className="inbox-toolbar-actions">
        <button
          type="button"
          className="inbox-tool-button"
          ref={clip}
          aria-label="Adjuntar archivo"
          title="Adjuntar archivo"
          aria-expanded={open}
          aria-controls={open ? id : undefined}
          disabled={capturing || preparing || !!value || !!pending}
          onClick={() => setOpen(!open)}
        >
          <Icon name="paperclip" />
        </button>
        {audioEnabled && (
          <button
            type="button"
            className="inbox-tool-button"
            aria-label="Grabar nota de voz"
            title="Grabar nota de voz"
            disabled={capturing || preparing || !!value || !!pending}
            onClick={() => {
              setOpen(false);
              void voice.start();
            }}
          >
            <Icon name="microphone" />
          </button>
        )}
        <input
          ref={input}
          type="file"
          hidden
          aria-label="Archivo adjunto"
          onChange={(event) => {
            const selected = event.target.files?.[0];
            if (selected && category.current)
              void upload(selected, category.current.id);
            event.target.value = "";
          }}
        />
      </div>
      {open && (
        <div
          className="inbox-composer-popover inbox-attachment-options"
          id={id}
          role="group"
          aria-label="Tipo de adjunto"
        >
          {supported.map((option) => (
            <Button
              key={option.id}
              variant="quiet"
              onClick={() => {
                category.current = option;
                if (input.current) {
                  input.current.accept = option.accepts;
                  input.current.click();
                }
                setOpen(false);
                clip.current?.focus();
              }}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}
      {capturing && (
        <div className="inbox-composer-popover inbox-recording">
          <div className="inbox-recording-line">
            <span className="inbox-recording-dot" aria-hidden="true" />
            <span role="status">
              {voice.status === "opening" ? "Abriendo micrófono…" : "Grabando"}
            </span>
            <time>{clockTime(voice.elapsed)}</time>
          </div>
          <Waveform samples={voice.samples} />
          <div className="inbox-toolbar-actions">
            <Button variant="quiet" onClick={() => voice.stop(true)}>
              Cancelar grabación
            </Button>
            <Button
              disabled={voice.status === "opening"}
              onClick={() => voice.stop()}
            >
              Listo
            </Button>
          </div>
        </div>
      )}
      {(value || pending) && (
        <div className="inbox-composer-popover inbox-prepared-attachment">
          {value && <MediaDownload key={value.id} attachment={value} />}
          {preparing && <p role="status">Preparando {pending?.file.name}…</p>}
          {pending && !preparing && (
            <Button
              variant="secondary"
              onClick={() => void upload(pending.file, pending.category)}
            >
              Reintentar adjunto
            </Button>
          )}
          {!preparing && (
            <Button
              variant="quiet"
              onClick={() => {
                onChange(null);
                setPending(null);
              }}
            >
              Quitar adjunto
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

async function mediaBlob(mediaId: string, signal?: AbortSignal) {
  const response = await fetch(`/api/institution/media/${mediaId}`, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { "X-CRM-Local": "1" },
    signal,
  });
  if (!response.ok)
    throw new Error("El adjunto ya no está disponible o no tienes acceso.");
  return response.blob();
}

export function MediaDownload({ attachment }: { attachment: Attachment }) {
  const task = useTask();
  const region = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState<{ url: string; blob: Blob } | null>(
    null,
  );
  const [previewFailed, setPreviewFailed] = useState(false);
  const mediaId = attachment.id;
  const canPreview =
    attachment.state === "ready" &&
    ["image", "video", "audio"].includes(attachment.kind);
  useEffect(() => {
    if (!canPreview || !region.current) return;
    const controller = new AbortController();
    let url = "";
    let observer: IntersectionObserver | undefined;
    const load = () => {
      observer?.disconnect();
      void mediaBlob(mediaId, controller.signal)
        .then((blob) => {
          if (!controller.signal.aborted) {
            url = URL.createObjectURL(blob);
            setPreview({ url, blob });
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) setPreviewFailed(true);
        });
    };
    if (typeof IntersectionObserver !== "undefined") {
      observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) load();
      });
      observer.observe(region.current);
    } else load();
    return () => {
      controller.abort();
      observer?.disconnect();
      if (url) URL.revokeObjectURL(url);
    };
  }, [mediaId, canPreview]);
  if (attachment.state !== "ready")
    return (
      <small>
        {attachment.name} ·{" "}
        {attachment.state === "failed"
          ? "No se pudo preparar"
          : "En preparación"}
      </small>
    );
  return (
    <div className="inbox-attachment" ref={region}>
      {task.notices}
      {previewFailed && <small>No se pudo cargar la vista previa. Intenta descargar el archivo.</small>}
      {preview && attachment.kind === "image" && (
        <img
          className={preview.blob.type === "image/webp" ? "inbox-sticker" : ""}
          src={preview.url}
          alt={attachment.name}
        />
      )}
      {preview && attachment.kind === "video" && (
        <video controls playsInline preload="metadata" src={preview.url} />
      )}
      {preview && attachment.kind === "audio" && (
        <VoicePlayer url={preview.url} blob={preview.blob} />
      )}
      <Button
        variant="quiet"
        disabled={task.busy}
        onClick={() =>
          void task.run(async () => {
            const blob = preview?.blob ?? (await mediaBlob(mediaId));
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = attachment.name;
            link.click();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
          })
        }
      >
        Descargar {attachment.name}
      </Button>
    </div>
  );
}
