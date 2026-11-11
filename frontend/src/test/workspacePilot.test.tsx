import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { App } from "../App";
import { usePanelEntrance } from "../shared/usePanelEntrance";
import { chartTiming, observeChartMotion } from "../shared/chartMotion";

async function navigate(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  const link = screen.queryByRole("link", { name });
  if (!link) await user.click(screen.getByText("Otros módulos"));
  await user.click(screen.getByRole("link", { name }));
}
const change = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe("V6 workspace continuity", () => {
  it("uses the slower panel rhythm only on section changes, cancels on unmount and stays immediate for keyboard input", () => {
    const cancel = vi.fn();
    const animate = vi.fn(() => ({
      cancel,
      finished: new Promise<void>(() => {}),
    }));
    Object.defineProperty(HTMLElement.prototype, "animate", {
      configurable: true,
      value: animate,
    });
    const stop = observeChartMotion(() => {});
    fireEvent.pointerDown(document);
    function Panel({ section }: { section: string }) {
      const ref = usePanelEntrance(section);
      const [value, setValue] = useState("");
      return (
        <div ref={ref}>
          <input
            aria-label="Draft"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        </div>
      );
    }
    const view = render(<Panel section="IA" />);
    expect(chartTiming).toEqual({
      enter: 240,
      update: 240,
      exit: 180,
      panel: 180,
    });
    expect(animate).toHaveBeenCalledTimes(1);
    expect(animate.mock.calls[0]).toEqual([
      expect.any(Array),
      expect.objectContaining({ duration: 180 }),
    ]);
    fireEvent.change(screen.getByLabelText("Draft"), {
      target: { value: "Do not animate typing" },
    });
    expect(animate).toHaveBeenCalledTimes(1);
    view.rerender(<Panel section="Perfil" />);
    expect(cancel).toHaveBeenCalled();
    expect(animate).toHaveBeenCalledTimes(2);
    fireEvent.keyDown(document, { key: "Tab" });
    view.rerender(<Panel section="IA" />);
    expect(animate).toHaveBeenCalledTimes(2);
    view.unmount();
    stop();
    Reflect.deleteProperty(HTMLElement.prototype, "animate");
  });
  it("keeps separate client, custom-field and new-client drafts without implicit saves, then discards or resets explicitly", async () => {
    window.location.hash = "/clients";
    const user = userEvent.setup();
    render(<App />);
    const notes = "Notas internas";
    await screen.findByRole("button", { name: /Persona Demo A/ });
    change(notes, "Draft A only");
    await user.click(screen.getByRole("button", { name: /Persona Demo B/ }));
    change(notes, "Draft B only");
    await user.click(screen.getByRole("button", { name: "Nuevo" }));
    change("Nombre visible", "Unsaved new person");
    await navigate(user, "Resumen");
    await screen.findByRole("heading", { name: "Contactos por etapa" });
    expect(screen.getByText("4 contactos")).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Cambiar a modo/ }));
    await navigate(user, "Clientes y prospectos");
    expect(await screen.findByLabelText("Nombre visible")).toHaveValue(
      "Unsaved new person",
    );
    await user.click(screen.getByRole("button", { name: /Persona Demo A/ }));
    expect(screen.getByLabelText(notes)).toHaveValue("Draft A only");
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.getByLabelText(notes)).not.toHaveValue("Draft A only");
    await user.click(screen.getByRole("button", { name: /Persona Demo B/ }));
    expect(screen.getByLabelText(notes)).toHaveValue("Draft B only");
    expect(
      screen.queryByRole("button", { name: "Restablecer demo" }),
    ).not.toBeInTheDocument();
    expect(JSON.stringify(localStorage)).not.toContain("Draft B only");
  });
});
