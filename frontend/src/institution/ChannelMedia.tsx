import { useState } from "react";
import { Button, Field } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import { useDraftGuard } from "./drafts";

export type Attachment = {
  id: string;
  name: string;
  kind: string;
  state: string;
};
export function MediaUpload({
  conversation,
  value,
  onChange,
}: {
  conversation: string;
  value: Attachment | null;
  onChange: (value: Attachment | null) => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  useDraftGuard(!!file || !!value);
  return (
    <div>
      {task.notices}
      {value ? (
        <p>
          {value.name}{" "}
          <Button variant="quiet" onClick={() => onChange(null)}>
            Quitar adjunto
          </Button>
        </p>
      ) : (
        <>
          <Field
            id="channel-attachment"
            label="Adjuntar archivo (máximo 5 MB)"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf,.txt,.docx,.xlsx,.pptx,.ogg,.mp3,.wav,.m4a"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <Button
            variant="secondary"
            disabled={!file || file.size > 5_000_000 || task.busy}
            onClick={() =>
              void task.run(async () => {
                if (!file) return;
                const encoded = await new Promise<string>((resolve, reject) => {
                  const reader = new FileReader();
                  reader.onload = () =>
                    resolve(String(reader.result).split(",")[1]);
                  reader.onerror = () =>
                    reject(new Error("No se pudo leer el archivo."));
                  reader.readAsDataURL(file);
                });
                const body = {
                  conversation_id: conversation,
                  filename: file.name,
                  content_base64: encoded,
                };
                const result = await call<Attachment>("media/upload", "POST", {
                  ...body,
                  operation_id: intent.get(body),
                });
                onChange(result);
                setFile(null);
              })
            }
          >
            Preparar adjunto
          </Button>
          {file && file.size > 5_000_000 && (
            <p>El archivo supera el límite de 5 MB.</p>
          )}
        </>
      )}
    </div>
  );
}
export function MediaDownload({ attachment }: { attachment: Attachment }) {
  const task = useTask();
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
    <div>
      {task.notices}
      <Button
        variant="secondary"
        disabled={task.busy}
        onClick={() =>
          void task.run(async () => {
            const response = await fetch(
              `/api/institution/media/${attachment.id}`,
              {
                credentials: "same-origin",
                cache: "no-store",
                headers: { "X-CRM-Local": "1" },
              },
            );
            if (!response.ok)
              throw new Error(
                "El adjunto ya no está disponible o no tienes acceso.",
              );
            const blob = await response.blob(),
              url = URL.createObjectURL(blob),
              link = document.createElement("a");
            link.href = url;
            link.download = attachment.name;
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
          })
        }
      >
        Descargar {attachment.name}
      </Button>
    </div>
  );
}
