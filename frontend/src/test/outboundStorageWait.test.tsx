import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { explainInboxError, MessageDelivery } from "../institution/InboxDelivery";

afterEach(cleanup);

it("shows a retained storage wait without claiming delivery or suggesting a duplicate send", () => {
  render(<MessageDelivery state="queued" reason="outbound_storage_wait" />);
  expect(screen.getByText("Esperando al servidor")).toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.queryByText(/No enviado|Descartado|Entregado/)).not.toBeInTheDocument();
  expect(explainInboxError({ code: "outbound_storage_wait", message: "" }).nextStep)
    .toContain("No hace falta volver a enviarlo");
});

it("keeps a historical failure distinguishable from the new pending state", () => {
  render(<MessageDelivery state="failed" reason="storage_busy" />);
  expect(screen.getByRole("button", { name: "No enviado" })).toBeInTheDocument();
  expect(screen.queryByText("Esperando al servidor")).not.toBeInTheDocument();
  expect(explainInboxError({ code: "storage_busy", message: "" }).title).toContain("base de datos");
});
