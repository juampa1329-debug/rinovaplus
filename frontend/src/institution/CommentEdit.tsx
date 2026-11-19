import { useState } from "react";
import { Button, Notice, TextArea } from "../shared/ui";
import { useInstitution, useIntent } from "./api";
import { useDraftGuard } from "./drafts";
import { OperationDialog } from "./ErrorFeedback";

export type CommentEditInfo = {
  supported: boolean;
  source: "meta" | "crm";
  revision: string;
  history: { previous: string; body: string; at: string }[];
};

export function CommentEdit({
  identity,
  body,
  edit,
  done,
}: {
  identity: string;
  body: string;
  edit?: CommentEditInfo | null;
  done: () => Promise<unknown>;
}) {
  const { call, session } = useInstitution();
  const intent = useIntent();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(body);
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [notice, setNotice] = useState<{
    title: string;
    detail: string;
    nextStep?: string;
    success?: boolean;
  } | null>(null);
  useDraftGuard(open && text !== body);
  const check = async () => {
    if (!edit) return;
    setBusy(true);
    try {
      const status = await call<{ pending: { operation_id: string } | null }>(
        `comments/${identity}/edit-status?source=${edit.source}`,
      );
      setPending(status.pending?.operation_id || null);
    } catch (error) {
      setNotice({
        title: "No se pudo comprobar la edición",
        detail:
          error instanceof Error
            ? error.message
            : "La consulta no está disponible.",
        nextStep: "Vuelve a abrir el editor cuando se restablezca la conexión.",
      });
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };
  const reconcile = async () => {
    if (!edit || !pending) return;
    setBusy(true);
    try {
      const result = await call<{ status: string; body?: string }>(
        `comments/${identity}/edit/reconcile`,
        "POST",
        { source: edit.source, operation_id: pending },
      );
      setPending(null);
      intent.clear();
      setOpen(false);
      setNotice({
        title: "Texto de Facebook comprobado",
        detail:
          result.status === "confirmed"
            ? "La edición quedó aplicada y confirmada por la consulta de Meta."
            : "Sin reenviar ningún cambio, actualizamos el hilo con el texto que Meta devuelve ahora. Puedes volver a abrir el editor para preparar una nueva versión.",
        success: true,
      });
      await done();
    } catch (error) {
      setNotice({
        title: "La edición aún necesita revisión",
        detail:
          error instanceof Error ? error.message : "Meta no está disponible.",
        nextStep:
          "Espera a que termine la operación antes de comprobar de nuevo. Esta consulta no modifica Facebook.",
      });
    } finally {
      setBusy(false);
    }
  };
  const save = async () => {
    if (!edit) return;
    setBusy(true);
    try {
      const request = {
        source: edit.source,
        revision: edit.revision,
        body: text.trim(),
      };
      const operation = intent.get({ identity, ...request });
      const result = await call<{ status: string; code?: string }>(
        `comments/${identity}/edit`,
        "POST",
        { ...request, operation_id: operation },
      );
      if (result.status !== "confirmed") {
        if (result.status === "uncertain" || result.status === "running")
          setPending(operation);
        setNotice({
          title:
            result.status === "uncertain"
              ? "El cambio necesita revisión"
              : "Meta no confirmó la edición",
          detail:
            result.status === "uncertain"
              ? "No sabemos todavía si Meta aplicó el cambio. No volveremos a enviarlo automáticamente."
              : "La publicación conserva su texto anterior o necesita actualizarse desde Meta.",
          nextStep: `Abre el comentario original en Facebook y comprueba su texto antes de repetir. Referencia: ${result.code || result.status}.`,
        });
        return;
      }
      setOpen(false);
      setNotice({
        title: "Comentario actualizado",
        detail:
          "Facebook confirmó el nuevo texto. La versión anterior queda en el historial de esta respuesta.",
        success: true,
      });
      await done();
    } catch (error) {
      setNotice({
        title: "No se pudo completar la edición",
        detail:
          error instanceof Error ? error.message : "No se pudo consultar Meta.",
        nextStep:
          "Conservamos tu borrador. Actualiza el hilo para comprobar si cambió el comentario y revisa la conexión de Facebook en Canales.",
      });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="comment-edit">
      {edit?.supported && session.actions.includes("inbox.write") && !open && (
        <Button
          variant="quiet"
          onClick={() => {
            setText(body);
            setOpen(true);
            void check();
          }}
        >
          Editar comentario
        </Button>
      )}
      {open && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setReview(true);
          }}
        >
          <TextArea
            id={`edit-${identity}`}
            label="Editar respuesta publicada"
            value={text}
            maxLength={4000}
            onChange={(event) => setText(event.target.value)}
            disabled={busy}
          />
          <p>
            El cambio será visible en Facebook, tanto si la respuesta original
            la escribió una persona como Gemini.
          </p>
          <div className="institution-actions">
            <Button
              type="submit"
              disabled={
                busy || !!pending || !text.trim() || text.trim() === body
              }
            >
              Revisar cambio
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => setOpen(false)}
            >
              Cancelar edición
            </Button>
          </div>
          {busy && (
            <Notice>Verificando el comentario y guardando en Meta…</Notice>
          )}
          {pending && (
            <Notice>
              Hay una edición pendiente de comprobar.{" "}
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void reconcile()}
              >
                Comprobar texto en Facebook
              </Button>
            </Notice>
          )}
        </form>
      )}
      {!!edit?.history?.length && (
        <details>
          <summary>Editado · Historial ({edit.history.length})</summary>
          <ol>
            {edit.history.map((value, index) => (
              <li key={`${value.at}-${index}`}>
                <time dateTime={value.at}>
                  {new Date(value.at).toLocaleString("es-CO")}
                </time>
                <p>
                  <strong>Antes:</strong> {value.previous}
                </p>
                <p>
                  <strong>Después:</strong> {value.body}
                </p>
              </li>
            ))}
          </ol>
        </details>
      )}
      {review && (
        <OperationDialog
          guidance={{
            title: "Actualizar comentario en Facebook",
            detail: text.trim(),
            nextStep:
              "Se editará esta respuesta de la cuenta conectada. Conservaremos el texto anterior y comprobaremos la confirmación de Meta.",
          }}
          dismiss={() => setReview(false)}
          dismissLabel="Volver al borrador"
          confirm={{ label: "Guardar en Facebook", run: () => void save() }}
        />
      )}
      {notice && (
        <OperationDialog
          guidance={notice}
          success={notice.success}
          dismiss={() => setNotice(null)}
        />
      )}
    </div>
  );
}
