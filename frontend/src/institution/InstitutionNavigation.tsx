import { useEffect, useRef } from "react";
import type { ReactNode, RefObject } from "react";
import { Icon } from "../shared/Icon";

export function InstitutionNavigation({
  open,
  close,
  trigger,
  children,
}: {
  open: boolean;
  close: () => void;
  trigger: RefObject<HTMLButtonElement | null>;
  children: ReactNode;
}) {
  const panel = useRef<HTMLElement>(null);
  const dismiss = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const mobile = window.matchMedia("(max-width: 900px)");
    if (!mobile.matches) {
      close();
      return;
    }
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dismiss.current?.focus();
    const resize = () => {
      if (!mobile.matches) close();
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if (event.key === "Tab") {
        const controls = Array.from(
          panel.current?.querySelectorAll<HTMLElement>(
            'a[href], button:not(:disabled), [tabindex="0"]',
          ) ?? [],
        ).filter((el) => !el.hidden && getComputedStyle(el).display !== "none");
        const first = controls[0];
        const last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    mobile.addEventListener("change", resize);
    document.addEventListener("keydown", keyboard);
    const opener = trigger.current;
    return () => {
      document.body.style.overflow = overflow;
      mobile.removeEventListener("change", resize);
      document.removeEventListener("keydown", keyboard);
      opener?.focus();
    };
  }, [open, close, trigger]);
  return (
    <>
      {open && (
        <button
          type="button"
          className="institution-nav-backdrop"
          aria-label="Cerrar menú desde el fondo"
          tabIndex={-1}
          onClick={close}
        />
      )}
      <aside
        id="institution-sidebar"
        ref={panel}
        className={`sidebar ${open ? "is-open" : ""}`}
        role={open ? "dialog" : undefined}
        aria-modal={open || undefined}
        aria-label={open ? "Menú principal" : undefined}
      >
        <button
          type="button"
          ref={dismiss}
          className="button quiet institution-menu-close"
          aria-label="Cerrar menú principal"
          onClick={close}
        >
          <Icon name="close" />
          Cerrar
        </button>
        {children}
      </aside>
    </>
  );
}
