import { useEffect, useRef, useState } from "react";
import { mediaApi, type InboxMedia } from "../api/mediaApi";
import { Button, Notice } from "../../../shared/ui";
import { Icon } from "../../../shared/Icon";

export function InboxMediaView({
  conversation,
  asset,
}: {
  conversation: string;
  asset: InboxMedia;
}) {
  const [obtained, setObtained] = useState<InboxMedia | null>(null);
  if (obtained?.id === asset.id) asset = obtained;
  const [preview, setPreview] = useState<{ key: string; url: string } | null>(
    null,
  );
  const [error, setError] = useState("");
  const key = `${conversation}:${asset.id}:${asset.state}`;
  useEffect(() => {
    if (!["pending", "processing"].includes(asset.state)) return;
    const abort = new AbortController();
    const interval = window.setInterval(() => {
      void mediaApi
        .read(conversation, asset.id, abort.signal)
        .then((next) => {
          if (!abort.signal.aborted) setObtained(next);
        })
        .catch(() => {});
    }, 3000);
    return () => {
      abort.abort();
      clearInterval(interval);
    };
  }, [conversation, asset.id, asset.state]);
  useEffect(() => {
    if (asset.state !== "ready" || asset.kind === "document") return;
    const abort = new AbortController();
    let created = "";
    setError("");
    void mediaApi
      .blob(conversation, asset.id, abort.signal)
      .then((blob) => {
        if (abort.signal.aborted) return;
        created = URL.createObjectURL(blob);
        setPreview({ key, url: created });
      })
      .catch((reason) => {
        if (!abort.signal.aborted) setError((reason as Error).message);
      });
    return () => {
      abort.abort();
      if (created) URL.revokeObjectURL(created);
    };
  }, [conversation, asset.id, asset.state, asset.kind, key]);
  async function download() {
    try {
      const blob = await mediaApi.blob(conversation, asset.id);
      const address = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = address;
      anchor.download = asset.name;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(address), 1000);
    } catch (reason) {
      setError((reason as Error).message);
    }
  }
  return (
    <div className="inbox-media">
      <p>
        {asset.name}
        {asset.size ? ` · ${(asset.size / 1024).toFixed(0)} KB` : ""}
        {asset.duration ? ` · ${asset.duration.toFixed(1)} s` : ""}
      </p>
      {asset.state !== "ready" ? (
        <Notice error={["failed", "rejected"].includes(asset.state)}>
          {["pending", "processing"].includes(asset.state)
            ? "Obteniendo y validando el adjunto recibido…"
            : "Adjunto no disponible. El mensaje original se conserva."}
        </Notice>
      ) : (
        <>
          {preview?.key === key && asset.kind === "image" && (
            <img
              src={preview.url}
              alt={asset.name}
              style={{
                display: "block",
                maxWidth: "100%",
                maxHeight: 260,
                objectFit: "contain",
              }}
            />
          )}
          {preview?.key === key && asset.kind === "audio" && (
            <audio
              controls
              preload="metadata"
              src={preview.url}
              style={{ maxWidth: "100%" }}
            />
          )}
          <Button variant="quiet" onClick={() => void download()}>
            Descargar adjunto
          </Button>
        </>
      )}
      {error && <Notice error>{error}</Notice>}
    </div>
  );
}

export function InboxMediaComposer({
  conversation,
  asset,
  disabled,
  onChange,
  onBusy,
}: {
  conversation: string;
  asset?: InboxMedia;
  disabled: boolean;
  onChange: (asset?: InboxMedia) => void;
  onBusy: (busy: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const [retryFile, setRetryFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const active = useRef(true);
  const abort = useRef<AbortController | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<number | null>(null);
  const canceled = useRef(false);
  useEffect(() => {
    onBusy(busy || recording);
    return () => onBusy(false);
  }, [busy, recording, onBusy]);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      canceled.current = true;
      abort.current?.abort();
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      if (timer.current !== null) clearTimeout(timer.current);
    };
  }, []);
  async function upload(file: File) {
    if (file.size > 5_000_000 || !file.size) {
      setError("Seleccione un archivo de hasta 5 MB que no esté vacío.");
      return;
    }
    const id = crypto.randomUUID();
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    setError("");
    setRetryFile(file);
    onChange({
      id,
      name: file.name,
      state: "uploading",
      kind: null,
      mime: null,
      size: file.size,
      duration: null,
      error: null,
    });
    try {
      const ready = await mediaApi.upload(
        conversation,
        id,
        file,
        controller.signal,
      );
      if (active.current) {
        onChange(ready);
        setRetryFile(null);
      }
    } catch (reason) {
      if (active.current && !controller.signal.aborted) {
        setError((reason as Error).message);
        onChange({
          id,
          name: file.name,
          state: "failed",
          kind: null,
          mime: null,
          size: file.size,
          duration: null,
          error: null,
        });
      }
    } finally {
      if (active.current) setBusy(false);
    }
  }
  async function discard() {
    abort.current?.abort();
    canceled.current = true;
    if (recorder.current?.state === "recording") recorder.current.stop();
    stream.current?.getTracks().forEach((track) => track.stop());
    if (timer.current !== null) clearTimeout(timer.current);
    setRecording(false);
    try {
      if (asset) await mediaApi.discard(conversation, asset.id);
      onChange(undefined);
      setRetryFile(null);
      setError("");
    } catch (reason) {
      setError((reason as Error).message);
    }
  }
  async function record() {
    if (busy || recording || disabled) return;
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError(
        "La grabación no está disponible en este navegador. Puede adjuntar un audio existente.",
      );
      return;
    }
    setError("");
    canceled.current = false;
    setBusy(true);
    try {
      const captured = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      if (!active.current || canceled.current) {
        captured.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = captured;
      const mime = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const device = new MediaRecorder(
        captured,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = device;
      const chunks: Blob[] = [];
      let total = 0;
      device.ondataavailable = (event) => {
        total += event.data.size;
        if (total > 5_000_000) {
          canceled.current = true;
          setError("La grabación superó 5 MB. Intente una nota más corta.");
          device.stop();
        } else chunks.push(event.data);
      };
      device.onstop = () => {
        captured.getTracks().forEach((track) => track.stop());
        if (timer.current !== null) clearTimeout(timer.current);
        if (!active.current) return;
        setRecording(false);
        if (!canceled.current && total)
          void upload(
            new File(chunks, "nota-de-voz.webm", { type: device.mimeType }),
          );
      };
      device.start(250);
      setRecording(true);
      timer.current = window.setTimeout(() => {
        if (device.state === "recording") device.stop();
      }, 60000);
    } catch {
      stream.current?.getTracks().forEach((track) => track.stop());
      if (active.current)
        setError(
          "No se pudo acceder al micrófono. Autorice su uso o adjunte un audio existente.",
        );
    } finally {
      if (active.current) setBusy(false);
    }
  }
  return (
    <div className="inbox-media-composer">
      <details className="scope-text">
        <summary title="Adjuntos · hasta 5 MB por mensaje">Formatos y límites</summary>
        <p>
          Un archivo de hasta 5 MB: JPEG/PNG, PDF/TXT, DOCX/XLSX/PPTX sin macros, o audio
          hasta 5 minutos. Las notas grabadas duran hasta 60 segundos y se
          convierten a Ogg/Opus.
        </p>
      </details>
      <input
        ref={input}
        type="file"
        hidden
        aria-label="Adjuntar imagen, documento o audio"
        accept=".jpg,.jpeg,.png,.pdf,.txt,.docx,.xlsx,.pptx,.mp3,.ogg,.wav,.webm,.m4a,.mp4,.aac,.flac,.amr"
        disabled={disabled || busy || recording || !!asset}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) void upload(file);
        }}
      />
      <div className="actions">
        <Button
          variant="secondary"
          className="media-icon-button"
          aria-label="Adjuntar imagen, documento o audio"
          title="Adjuntar imagen, documento o audio"
          disabled={disabled || busy || recording || !!asset}
          onClick={() => input.current?.click()}
        >
          <Icon name="paperclip" />
        </Button>
        {!recording ? (
          <Button
            variant="secondary"
            className="media-icon-button"
            aria-label="Grabar nota de voz"
            title="Grabar nota de voz"
            disabled={disabled || busy || !!asset}
            onClick={() => void record()}
          >
            <Icon name="microphone" />
          </Button>
        ) : (
          <Button onClick={() => recorder.current?.stop()}>
            Detener y adjuntar nota
          </Button>
        )}
        {(asset || recording || busy) && (
          <Button variant="quiet" onClick={() => void discard()}>
            Cancelar adjunto
          </Button>
        )}
        {retryFile && !busy && !recording && (
          <Button
            variant="quiet"
            disabled={disabled}
            onClick={() => void upload(retryFile)}
          >
            Reintentar carga
          </Button>
        )}
        {asset && !busy && asset.state !== "ready" && (
          <Button
            variant="quiet"
            onClick={() => {
              void mediaApi
                .read(conversation, asset.id)
                .then(onChange)
                .catch((reason) => setError((reason as Error).message));
            }}
          >
            Actualizar adjunto
          </Button>
        )}
      </div>
      {busy && <Notice>Cargando y validando el adjunto privado…</Notice>}
      {recording && (
        <Notice>
          Grabando… Detenga para adjuntar o cancele para descartar.
        </Notice>
      )}
      {asset?.state === "ready" && (
        <InboxMediaView
          key={`draft:${asset.id}`}
          conversation={conversation}
          asset={asset}
        />
      )}
      {error && <Notice error>{error}</Notice>}
    </div>
  );
}
