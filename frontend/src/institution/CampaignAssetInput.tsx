import { useEffect, useRef, useState } from "react";
import { Button, Notice } from "../shared/ui";
import { useInstitution, useTask } from "./api";
import { useDraftGuard } from "./drafts";

export function CampaignAssetInput({
  kind,
  assetId,
  filename,
  id,
  onChange,
  onBusy,
}: {
  kind: string;
  assetId?: string | null;
  filename?: string;
  id: string;
  onChange: (id: string, name: string) => void;
  onBusy: (v: boolean) => void;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    [preview, setPreview] = useState(""),
    [recording, setRecording] = useState(false),
    url = useRef(""),
    recorder = useRef<MediaRecorder | null>(null),
    stream = useRef<MediaStream | null>(null),
    timer = useRef<ReturnType<typeof setTimeout> | null>(null),
    alive = useRef(true);
  useDraftGuard(task.busy || recording);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
      if (url.current) URL.revokeObjectURL(url.current);
    };
  }, []);
  const upload = (file: File) =>
    void task.run(async () => {
      onBusy(true);
      try {
        if (file.size > 5000000) throw Error("El archivo supera 5 MB.");
        const data = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onerror = () => reject(Error("No se pudo leer el archivo."));
          reader.onload = () => resolve(String(reader.result).split(",")[1]);
          reader.readAsDataURL(file);
        });
        const result = await call<{ id: string; name: string }>(
          "campaigns/assets",
          "POST",
          {
            operation_id: crypto.randomUUID(),
            filename: file.name,
            kind,
            content_base64: data,
          },
        );
        if (alive.current) onChange(result.id, result.name);
      } finally {
        onBusy(false);
      }
    }, "Adjunto validado y guardado.");
  const record = () =>
    void task.run(async () => {
      if (
        !navigator.mediaDevices?.getUserMedia ||
        typeof MediaRecorder === "undefined"
      )
        throw Error(
          "El navegador no permite grabar audio. Puedes subir un archivo.",
        );
      onBusy(true);
      try {
        const media = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        if (!alive.current) {
          media.getTracks().forEach((t) => t.stop());
          onBusy(false);
          return;
        }
        stream.current = media;
        const r = new MediaRecorder(media),
          chunks: BlobPart[] = [];
        let size = 0;
        recorder.current = r;
        r.ondataavailable = (e) => {
          if (e.data.size) {
            chunks.push(e.data);
            size += e.data.size;
            if (size > 5000000 && r.state === "recording") r.stop();
          }
        };
        r.onstop = () => {
          if (timer.current) clearTimeout(timer.current);
          media.getTracks().forEach((t) => t.stop());
          onBusy(false);
          if (alive.current) {
            setRecording(false);
            upload(
              new File(chunks, "orientacion.webm", {
                type: r.mimeType || "audio/webm",
              }),
            );
          }
        };
        r.start(1000);
        setRecording(true);
        timer.current = setTimeout(() => {
          if (r.state === "recording") r.stop();
        }, 300000);
      } catch (e) {
        if (timer.current) clearTimeout(timer.current);
        stream.current?.getTracks().forEach((t) => t.stop());
        if (alive.current) setRecording(false);
        onBusy(false);
        throw e;
      }
    }, "Grabación iniciada.");
  const accept =
    kind === "image"
      ? "image/png,image/jpeg"
      : kind === "audio"
        ? "audio/*"
        : kind === "video"
          ? "video/mp4,video/webm"
          : ".pdf,.docx,.xlsx,.pptx,.txt,application/pdf";
  return (
    <div className="campaign-asset">
      {task.notices}
      <label htmlFor={id}>
        Subir{" "}
        {
          (
            {
              image: "imagen",
              audio: "audio",
              video: "video",
              document: "documento",
            } as Record<string, string>
          )[kind]
        }
      </label>
      <input
        id={id}
        type="file"
        accept={accept}
        disabled={task.busy || recording}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload(file);
        }}
      />
      <small>
        Hasta 5 MB. Audio: hasta 5 minutos. Video: hasta 2 minutos y 1920 ×
        1080.
      </small>
      {kind === "audio" &&
        (recording ? (
          <Button variant="secondary" onClick={() => recorder.current?.stop()}>
            Detener grabación
          </Button>
        ) : (
          <Button variant="quiet" disabled={task.busy} onClick={record}>
            Grabar audio
          </Button>
        ))}
      {assetId && (
        <>
          <p>Adjunto: {filename || "Archivo validado"}</p>
          <Button
            variant="quiet"
            disabled={task.busy || recording}
            onClick={() =>
              void task.run(async () => {
                const response = await fetch(
                  `/api/institution/campaigns/assets/${assetId}`,
                  {
                    credentials: "same-origin",
                    headers: { "X-CRM-Local": "1" },
                  },
                );
                if (!response.ok)
                  throw Error(
                    "No se pudo abrir el adjunto con tu acceso actual.",
                  );
                const blob = await response.blob();
                if (url.current) URL.revokeObjectURL(url.current);
                url.current = URL.createObjectURL(blob);
                setPreview(url.current);
              }, "Adjunto abierto.")
            }
          >
            Vista previa del adjunto
          </Button>
        </>
      )}
      {preview && (
        <div>
          {kind === "image" ? (
            <img
              className="campaign-media-preview"
              src={preview}
              alt={filename || "Imagen de la plantilla"}
            />
          ) : kind === "audio" ? (
            <audio controls src={preview} />
          ) : kind === "video" ? (
            <video className="campaign-media-preview" controls src={preview} />
          ) : (
            <Notice>Documento validado para descarga.</Notice>
          )}
          <a href={preview} download={filename || "adjunto"}>
            Descargar {filename || "adjunto"}
          </a>
        </div>
      )}
    </div>
  );
}
