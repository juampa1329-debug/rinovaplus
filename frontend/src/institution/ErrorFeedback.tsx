import {
  createContext,
  useCallback,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { Button } from "../shared/ui";
import "./error-feedback.css";

export type OperationFailure = {
  message: string;
  code?: string;
  status?: number;
};
export type ErrorGuidance = { title: string; detail: string; nextStep: string };
type Report = (
  failure: OperationFailure,
  trigger?: Element | null,
) => ErrorGuidance | undefined;

export const ErrorFeedbackContext = createContext<Report | null>(null);

export function ErrorFeedback({
  children,
  explain,
}: {
  children: ReactNode;
  explain: (failure: OperationFailure) => ErrorGuidance;
}) {
  const [current, setCurrent] = useState<{
    guidance: ErrorGuidance;
    trigger: Element | null;
  } | null>(null);
  const report = useCallback<Report>(
    (failure, trigger = document.activeElement) => {
      if (trigger && !trigger.isConnected) return;
      const guidance = explain(failure);
      setCurrent((visible) => visible ?? { guidance, trigger });
      return guidance;
    },
    [explain],
  );
  return (
    <ErrorFeedbackContext.Provider value={report}>
      {children}
      {current && (
        <ErrorDialog
          guidance={current.guidance}
          trigger={current.trigger}
          dismiss={() => setCurrent(null)}
        />
      )}
    </ErrorFeedbackContext.Provider>
  );
}

function ErrorDialog({
  guidance,
  trigger,
  dismiss,
}: {
  guidance: ErrorGuidance;
  trigger: Element | null;
  dismiss: () => void;
}) {
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);

  useLayoutEffect(() => {
    const node = dialog.current;
    if (!node || node.open) return;
    node.showModal?.();
    node.querySelector("button")?.focus();
    return () => {
      if (node.open) node.close();
    };
  }, []);

  const close = () => {
    dialog.current?.close();
    if (trigger instanceof HTMLElement && trigger.isConnected)
      trigger.focus({ preventScroll: true });
    dismiss();
  };
  return (
    <dialog
      ref={dialog}
      className="operation-error-dialog"
      role="alertdialog"
      aria-labelledby={`${id}-title`}
      aria-describedby={`${id}-detail ${id}-next-step`}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <div className="operation-error-content">
        <span className="operation-error-icon" aria-hidden="true">
          !
        </span>
        <div className="operation-error-copy">
          <h2 id={`${id}-title`}>{guidance.title}</h2>
          <p id={`${id}-detail`}>{guidance.detail}</p>
        </div>
        <div className="operation-error-next" id={`${id}-next-step`}>
          <h3>Cómo resolverlo</h3>
          <p>{guidance.nextStep}</p>
        </div>
        <Button onClick={close}>Cerrar aviso</Button>
      </div>
    </dialog>
  );
}
