import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { BroadcastContactSelection } from "./BroadcastContactSelection";

const ids = [
  "01234567-89ab-4def-8123-0123456789ab",
  "12345678-89ab-4def-8123-0123456789ab",
];
function upload(data: unknown) {
  const file = new File([JSON.stringify(data)], "seleccion.json", {
    type: "application/json",
  });
  Object.defineProperty(file, "text", {
    value: async () => JSON.stringify(data),
  });
  fireEvent.change(screen.getByLabelText("Archivo de selección de contactos"), {
    target: { files: [file] },
  });
}
it("requires an explicit apply before replacing a reviewed selection", async () => {
  const change = vi.fn();
  render(<BroadcastContactSelection change={change} />);
  fireEvent.click(screen.getByText("Cargar selección revisada de contactos"));
  upload({ version: "rinovaplus-broadcast-selection-v1", contact_ids: ids });
  const button = await screen.findByRole("button", {
    name: "Aplicar selección de 2 contactos",
  });
  expect(change).not.toHaveBeenCalled();
  fireEvent.click(button);
  expect(change).toHaveBeenCalledExactlyOnceWith(ids);
});
it("rejects duplicate contacts without changing the current audience", async () => {
  const change = vi.fn();
  render(<BroadcastContactSelection change={change} />);
  fireEvent.click(screen.getByText("Cargar selección revisada de contactos"));
  upload({
    version: "rinovaplus-broadcast-selection-v1",
    contact_ids: [ids[0], ids[0]],
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "contactos únicos",
  );
  expect(change).not.toHaveBeenCalled();
});
