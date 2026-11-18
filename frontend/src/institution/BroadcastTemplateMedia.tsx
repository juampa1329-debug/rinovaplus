import { useEffect, useRef, useState } from "react";
import { Button, Field, Notice } from "../shared/ui";
import { Icon } from "../shared/Icon";
import { ApiError, useInstitution, useIntent, useTask } from "./api";

export function TemplateSamplePicker({
  account,
  kind,
  onUploaded,
  onPreview,
  purpose = "review",
  onDelivery,
}: {
  account: string;
  kind: string;
  onUploaded: (handle: string) => void;
  onPreview?: (url: string) => void;
  purpose?: "review" | "delivery";
  onDelivery?: (id: string, operation: string) => void;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [file, setFile] = useState<File | null>(null),
    [confirmed, setConfirmed] = useState(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const accept =
    kind === "IMAGE"
      ? "image/jpeg,image/png"
      : kind === "VIDEO"
        ? "video/mp4"
        : "application/pdf";
  return (
    <div className="broadcast-sample-picker">
      <Field
        id={`template-file-${purpose}`}
        label={
          purpose === "review"
            ? "Adjuntar archivo de muestra"
            : "Adjuntar archivo de la campaña"
        }
        type="file"
        accept={accept}
        disabled={task.busy}
        onChange={(e) => {
          const chosen = e.target.files?.[0] || null;
          setFile(chosen);
          setConfirmed(false);
          intent.clear();
          onUploaded("");
          onPreview?.(chosen ? URL.createObjectURL(chosen) : "");
        }}
      />
      <p className="broadcast-help">
        {kind === "IMAGE"
          ? "JPG o PNG"
          : kind === "VIDEO"
            ? "MP4, hasta 2 minutos y 1920 × 1080"
            : "PDF"}
        . Hasta 5 MB en RinovaPlus.{" "}
        {purpose === "review"
          ? "Usa una muestra sin datos personales. El archivo real de la campaña se elige después."
          : "Este archivo se enviará a los destinatarios cuando actives la campaña. Cargarlo no envía mensajes."}
      </p>
      {file && (
        <>
          <p>
            <Icon name="paperclip" /> {file.name} ·{" "}
            {(file.size / 1000000).toFixed(2)} MB
          </p>
          <label className="broadcast-check">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={task.busy}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            {purpose === "review"
              ? "Autorizo enviar esta muestra a Meta para revisar la plantilla."
              : "Autorizo cargar este archivo en Meta para usarlo en esta campaña."}
          </label>
          <Button
            variant="secondary"
            disabled={
              !confirmed || task.busy || file.size > 5000000 || !file.size
            }
            onClick={() =>
              void task.run(
                async () => {
                  if (file.size > 5000000 || !file.size)
                    throw Error("Elige un archivo válido de hasta 5 MB.");
                  const content_base64 = await new Promise<string>(
                    (resolve, reject) => {
                      const reader = new FileReader();
                      reader.onerror = () =>
                        reject(
                          Error(
                            "No se pudo leer el archivo. Selecciónalo de nuevo.",
                          ),
                        );
                      reader.onload = () =>
                        resolve(String(reader.result).split(",")[1]);
                      reader.readAsDataURL(file);
                    },
                  );
                  const body = {
                    filename: file.name,
                    kind: kind.toLowerCase(),
                    content_base64,
                    confirmed: true,
                    reason: "Muestra de cabecera para revisión de plantilla",
                    revision: 0,
                    purpose,
                  };
                  const result = await call<{
                    status: string;
                    handle?: string;
                    code?: string;
                    media_id?: string;
                    operation_id?: string;
                  }>(
                    `broadcasts/accounts/${account}/templates/sample`,
                    "POST",
                    {
                      ...body,
                      operation_id: intent.get(body),
                    },
                  );
                  if (
                    result.status !== "confirmed" ||
                    (purpose === "review"
                      ? !result.handle
                      : !result.media_id || !result.operation_id)
                  )
                    throw new ApiError(
                      502,
                      result.code ||
                        (result.status === "uncertain" ||
                        result.status === "running"
                          ? "template_sample_upload_unknown"
                          : "template_sample_upload_rejected"),
                    );
                  if (alive.current) {
                    if (purpose === "review") onUploaded(result.handle!);
                    else onDelivery?.(result.media_id!, result.operation_id!);
                  }
                },
                purpose === "review"
                  ? "Archivo de muestra cargado en Meta. Ya puedes guardar la plantilla."
                  : "Archivo cargado en Meta. Guarda la campaña y revisa los destinatarios antes de activarla.",
              )
            }
          >
            {task.busy
              ? "Cargando archivo…"
              : purpose === "review"
                ? "Cargar muestra en Meta"
                : "Cargar archivo de la campaña"}
          </Button>
          {file.size > 5000000 && (
            <Notice error>
              El archivo supera los 5 MB. Elige uno más pequeño.
            </Notice>
          )}
        </>
      )}
      {task.notices}
    </div>
  );
}

export const templateExamples = [
  {
    name: "solicitud_documento_cbn",
    label: "Documento solicitado",
    category: "UTILITY",
    header: "DOCUMENT",
    body: "Hola {{customer_first_name}}, te compartimos el documento que solicitaste para continuar tu trámite con CBN. Si necesitas aclarar algún punto, responde a este mensaje.",
    buttons: ["Tengo una pregunta", "Recibido"],
  },
  {
    name: "confirmacion_cita_cbn",
    label: "Confirmación de cita",
    category: "UTILITY",
    header: "",
    body: "Hola {{customer_first_name}}, confirmamos la cita que solicitaste con CBN. Tu asesor te compartirá la fecha y la hora acordadas. ¿Necesitas ajustar algún detalle?",
    buttons: ["Hablar con mi asesor", "Necesito cambiarla"],
  },
  {
    name: "respuesta_solicitud_cbn",
    label: "Seguimiento de una solicitud",
    category: "UTILITY",
    header: "",
    body: "Hola {{customer_first_name}}, tenemos una actualización sobre la solicitud que registraste en CBN. Responde a este mensaje para revisarla con tu asesor.",
    buttons: ["Ver mi solicitud", "Hablar con asesor"],
  },
  {
    name: "material_solicitado_cbn",
    label: "Imagen informativa solicitada",
    category: "UTILITY",
    header: "IMAGE",
    body: "Hola {{customer_first_name}}, aquí está el material que nos pediste. Si algo no queda claro, cuéntanos y lo revisamos contigo.",
    buttons: ["Tengo una pregunta", "Gracias, recibido"],
  },
  {
    name: "video_solicitado_cbn",
    label: "Video de orientación solicitado",
    category: "UTILITY",
    header: "VIDEO",
    body: "Hola {{customer_first_name}}, te compartimos el video de orientación que solicitaste a CBN. Puedes responder aquí si necesitas ayuda con el siguiente paso.",
    buttons: ["Necesito ayuda", "Recibido"],
  },
  {
    name: "informacion_programas_cbn",
    label: "Información general de programas",
    category: "MARKETING",
    header: "",
    body: "Hola {{customer_first_name}}, somos el equipo de CBN. Si te interesa conocer nuestros programas, podemos orientarte por aquí. ¿Quieres recibir información?",
    buttons: ["Quiero información", "Ahora no", "No recibir mensajes"],
  },
];

export function TemplateExampleGuide({
  choose,
}: {
  choose: (example: (typeof templateExamples)[number]) => void;
}) {
  return (
    <details className="broadcast-template-guide">
      <summary>Guía y ejemplos de mensajes naturales</summary>
      <p>
        Identifica a CBN, explica el motivo concreto y haz una sola pregunta.
        Usa frases breves, sin urgencia artificial ni precios que no estén
        confirmados.
      </p>
      <p>
        Utilidad corresponde a una solicitud o trámite real, sin promoción.
        Informar programas de forma general o retomar interesados puede ser
        Marketing aunque el tono sea cercano. Meta determina la categoría final.
      </p>
      <div className="broadcast-example-grid">
        {templateExamples.map((e) => (
          <article key={e.name}>
            <h4>{e.label}</h4>
            <small>
              {e.category === "UTILITY"
                ? "Utilidad · sólo si hubo solicitud real"
                : "Marketing · requiere autorización"}
            </small>
            <p>{e.body}</p>
            <Button variant="secondary" onClick={() => choose(e)}>
              Usar ejemplo: {e.label}
            </Button>
          </article>
        ))}
      </div>
      <p>
        Los ejemplos son borradores. Revisa el contexto y los datos antes de
        enviarlos a Meta o a una persona. No se envía nada al elegir un ejemplo.
      </p>
    </details>
  );
}
