import { Button } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
export function SocialStoryPreview({
  message,
  reload,
}: {
  message: string;
  reload: () => void | Promise<unknown>;
}) {
  const { session, call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  return (
    <div>
      <p>
        Meta notificó la historia. Puedes intentar recuperar su vista previa
        mientras siga disponible; no se envía ninguna respuesta.
      </p>
      {session.actions.includes("inbox.write") && (
        <Button
          variant="secondary"
          disabled={task.busy}
          onClick={() =>
            void task.run(async () => {
              await call("media/story-preview", "POST", {
                operation_id: intent.get({ message }),
                message_id: message,
              });
              await reload();
            }, "Vista previa solicitada. Las historias vencidas pueden no estar disponibles en Meta.")
          }
        >
          Recuperar vista previa de la historia
        </Button>
      )}
      {task.notices}
    </div>
  );
}
