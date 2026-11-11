import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { clientsApi } from "../modules/clients/api/clientsApi";
import {
  emptyInstitutionalProfile,
  institutionalIdentityApi,
  trimIdentitySpaces,
  validateInstitutionalProfile,
  type IdentityPage,
} from "../modules/contacts/api/institutionalIdentity";

function catalog() {
  vi.mocked(institutionalIdentityApi.catalog).mockResolvedValue({
    documentTypes: [{ id: 3, label: "Tipo de prueba", code: "TP" }],
    periods: {
      items: [{ id: 9, label: "Período de prueba", active: true }],
      activePeriodId: 9,
      selectionRequired: false,
    },
  });
}
function expandCandidates() {
  const details = screen
    .getByText("Posibles duplicados y registros institucionales")
    .closest("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
}
const page = (name: string): IdentityPage => ({
  items: [
    {
      source: "student",
      sourceId: "42",
      contactId: null,
      name,
      givenNames: name,
      firstSurname: "Original",
      secondSurname: null,
      documentTypeId: 3,
      document: "00-X",
      phone: "11111",
      alternatePhone: "22222",
      email: null,
      periodId: 9,
      period: "Período de prueba",
      offerPeriodId: 8,
      offerPeriod: "Período original",
      programId: null,
      program: null,
      city: null,
      reasons: ["same_phone"],
    },
  ],
  offset: 0,
  limit: 25,
  hasMore: false,
  mode: "identity",
  criteriaRequired: false,
  identityScope: "all_periods_and_programs",
});

describe("C2 shared declared profile and read-only comparison", () => {
  it("keeps names separate and does not assume an active period, then saves declared fields through the existing mutation", async () => {
    catalog();
    window.location.hash = "/clients";
    render(<App />);
    const names = await screen.findByLabelText("Nombres informados");
    await screen.findByRole("option", { name: "TP · Tipo de prueba" });
    expect(names).toHaveValue("");
    expect(screen.getByLabelText("Período al que aspira")).toHaveValue("");
    const visibleName = (
      screen.getByLabelText("Nombre visible") as HTMLInputElement
    ).value;
    fireEvent.change(names, { target: { value: "Nombres declarados" } });
    fireEvent.change(screen.getByLabelText("Tipo de documento informado"), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByLabelText("Número de documento informado"), {
      target: { value: "00-X" },
    });
    fireEvent.change(screen.getByLabelText("Correo informado"), {
      target: { value: "a".repeat(80) + "@example.invalid" },
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Guardar ficha" }),
    );
    await waitFor(() => expect(clientsApi.save).toHaveBeenCalled());
    expect(vi.mocked(clientsApi.save).mock.calls.at(-1)?.[0]).toMatchObject({
      name: visibleName,
      institutionalProfile: {
        givenNames: "Nombres declarados",
        document: "00-X",
        documentTypeId: 3,
        aspirationPeriodId: null,
      },
    });
  });

  it("preserves declared field drafts across Clients and Inbox without copying a record", async () => {
    catalog();
    window.location.hash = "/inbox";
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Nombres informados"), {
      target: { value: "Borrador sin publicar" },
    });
    await userEvent.click(
      screen.getByRole("link", { name: "Clientes y prospectos" }),
    );
    expect(await screen.findByLabelText("Nombres informados")).toHaveValue(
      "Borrador sin publicar",
    );
    expect(clientsApi.save).not.toHaveBeenCalled();
  });

  it("cancels obsolete AJAX requests, keeps identity global and explains alternate phone matches in a read-only comparison", async () => {
    catalog();
    window.location.hash = "/clients";
    let oldResolve!: (value: IdentityPage) => void;
    vi.mocked(institutionalIdentityApi.candidates)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            oldResolve = resolve;
          }),
      )
      .mockResolvedValue(page("Resultado actual"));
    render(<App />);
    await screen.findByLabelText("Nombres informados");
    fireEvent.change(screen.getByLabelText("Número de documento informado"), {
      target: { value: " \t00-X\t " },
    });
    fireEvent.change(screen.getByLabelText("Tipo de documento informado"), {
      target: { value: "3" },
    });
    expandCandidates();
    await waitFor(() =>
      expect(institutionalIdentityApi.candidates).toHaveBeenCalledTimes(1),
    );
    const first = vi.mocked(institutionalIdentityApi.candidates).mock.calls[0];
    expect(first[0]).toMatchObject({
      document: "\t00-X\t",
      periodId: null,
      programId: null,
    });
    fireEvent.change(screen.getByLabelText("Teléfono"), {
      target: { value: "22222" },
    });
    await screen.findByText("Resultado actual");
    expect(first[1]?.aborted).toBe(true);
    oldResolve(page("Resultado obsoleto"));
    await userEvent.click(
      screen.getByRole("button", { name: "Comparar datos" }),
    );
    expect(screen.queryByText("Resultado obsoleto")).not.toBeInTheDocument();
    expect(
      screen.getByText("Teléfono alternativo original").nextElementSibling,
    ).toHaveTextContent("22222");
    expect(
      screen
        .getByLabelText("Comparación de identidad de lectura")
        .querySelector("input,select,textarea"),
    ).toBeNull();
    expect(clientsApi.save).not.toHaveBeenCalled();
  });

  it("rejects incomplete document pairs and preserves punctuation and tabs", () => {
    expect(trimIdentitySpaces(" \t00-X\t ")).toBe("\t00-X\t");
    expect(
      validateInstitutionalProfile({
        ...emptyInstitutionalProfile(),
        document: "00-X",
      }),
    ).toHaveProperty("institutionalDocument");
    expect(
      validateInstitutionalProfile({
        ...emptyInstitutionalProfile(),
        documentTypeId: 3,
        document: "00-X",
      }),
    ).toEqual({});
  });
});
