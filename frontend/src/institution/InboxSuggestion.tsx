import { useEffect, useRef, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Notice } from "../shared/ui";

type Props = {
  conversation: string;
  question: string;
  incoming: string;
  channel?: string;
  onUseReply: (text: string) => void;
};
export function InboxSuggestion(props: Props) {
  return (
    <SuggestionDraft
      key={`${props.conversation}:${props.incoming}`}
      {...props}
    />
  );
}
function SuggestionDraft({
  conversation,
  question,
  channel,
  onUseReply,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const generation = useRef(0);
  const lifetime = useRef({ active: true });
  useEffect(() => {
    const current = lifetime.current;
    current.active = true;
    return () => {
      current.active = false;
    };
  }, []);
  async function suggest() {
    const version = ++generation.current;
    setBusy(true);
    setError("");
    setText("");
    try {
      const selection = await api<{ revision: number }>(
        `/conversations/${conversation}`,
      );
      if (!lifetime.current.active || version !== generation.current) return;
      const result = await api<{ text?: string; handoff?: boolean }>(
        `/conversations/${conversation}/draft`,
        "POST",
        {
          request_id: crypto.randomUUID(),
          revision: selection.revision,
          question: question.slice(0, 2000),
          channel: channel === "messenger" ? "facebook" : (channel ?? "local"),
          call_provider: true,
          acknowledge_consumption: true,
        },
      );
      if (!lifetime.current.active || version !== generation.current) return;
      if (result.text) setText(result.text);
      else
        setError(
          "El agente necesita información adicional o revisión humana. Revisa su configuración y las fuentes del programa.",
        );
    } catch (failure) {
      if (lifetime.current.active && version === generation.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "No se pudo generar la sugerencia.",
        );
    } finally {
      if (lifetime.current.active && version === generation.current)
        setBusy(false);
    }
  }
  return (
    <section
      className="inbox-ai-suggestion"
      aria-label="Sugerencia de IA"
      aria-busy={busy}
    >
      <Button
        variant="quiet"
        disabled={busy || !question.trim()}
        onClick={() => void suggest()}
      >
        {busy ? "Preparando respuesta…" : "Sugerir respuesta con IA"}
      </Button>
      {error && <Notice error>{error}</Notice>}
      {text && (
        <div role="status">
          <p className="agents-response-text">{text}</p>
          <Button variant="secondary" onClick={() => onUseReply(text)}>
            Usar en el mensaje
          </Button>
          <small>
            Revisa el borrador. Para enviarlo, activa Humano y pulsa Enviar.
          </small>
        </div>
      )}
    </section>
  );
}
