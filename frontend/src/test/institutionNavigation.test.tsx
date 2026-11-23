import { useCallback, useRef, useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { InstitutionNavigation } from "../institution/InstitutionNavigation";

let desktop: (() => void) | undefined;
let media: MediaQueryList;
beforeEach(() => {
  media = {
    matches: true,
    addEventListener: vi.fn((_type, listener) => {
      desktop = listener;
    }),
    removeEventListener: vi.fn(),
  } as unknown as MediaQueryList;
  vi.stubGlobal("matchMedia", () => media);
});
afterEach(() => {
  vi.unstubAllGlobals();
  document.body.style.overflow = "";
});
function Example() {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);
  return (
    <>
      <button ref={trigger} onClick={() => setOpen(true)}>
        Abrir menú
      </button>
      <InstitutionNavigation open={open} close={close} trigger={trigger}>
        <nav>
          <a href="#/inbox" onClick={close}>
            Inbox actual
          </a>
          <a href="#/academic" onClick={close}>
            Académico
          </a>
        </nav>
      </InstitutionNavigation>
      <main inert={open}>Conversación</main>
    </>
  );
}
it.each(["Cerrar menú principal", "Cerrar menú desde el fondo"])(
  "closes through %s and restores focus and scrolling",
  (name) => {
    document.body.style.overflow = "auto";
    render(<Example />);
    const opener = screen.getByRole("button", { name: "Abrir menú" });
    fireEvent.click(opener);
    expect(
      screen.getByRole("dialog", { name: "Menú principal" }),
    ).toHaveAttribute("aria-modal", "true");
    expect(
      screen.getByRole("button", { name: "Cerrar menú principal" }),
    ).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.click(screen.getByRole("button", { name }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(opener).toHaveFocus();
    expect(document.body.style.overflow).toBe("auto");
  },
);
it("keeps keyboard focus in the open drawer and closes with Escape", () => {
  render(<Example />);
  fireEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
  fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
  expect(screen.getByRole("link", { name: "Académico" })).toHaveFocus();
  fireEvent.keyDown(document, { key: "Tab" });
  expect(
    screen.getByRole("button", { name: "Cerrar menú principal" }),
  ).toHaveFocus();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("closes even when choosing the current section without a hashchange", () => {
  render(<Example />);
  fireEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
  fireEvent.click(screen.getByRole("link", { name: "Inbox actual" }));
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("releases the drawer when the viewport switches to desktop", () => {
  render(<Example />);
  fireEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
  Object.assign(media, { matches: false });
  act(() => desktop?.());
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.body.style.overflow).toBe("");
});
