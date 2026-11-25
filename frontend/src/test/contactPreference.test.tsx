import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ContactPreference } from "../institution/ContactPreference";
const state = vi.hoisted(() => ({ blocked: true, error: "" }));
vi.mock("../institution/Settings", () => ({ useResource: () => ({value: {no_contact: state.blocked}, error: state.error}) }));
afterEach(cleanup);
it("shows explicit no-contact status separately from sales stage", () => {
  render(<ContactPreference id="contact" />);
  expect(screen.getByText("No contactar")).toBeInTheDocument();
  expect(screen.getByText(/excluye de campañas y seguimientos/)).toBeInTheDocument();
});
it("never presents a missing preference as permission to send", () => {
  state.blocked = false;
  render(<ContactPreference id="other" />);
  expect(screen.getByText(/verifica por separado el consentimiento/)).toBeInTheDocument();
});
it("does not show an allowed state if the preference query fails", () => {
  state.error = "unavailable";
  render(<ContactPreference id="other" />);
  expect(screen.getByText(/No se pudo consultar/)).toBeInTheDocument();
  expect(screen.queryByText(/Sin solicitud/)).not.toBeInTheDocument();
});
