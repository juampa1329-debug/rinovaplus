import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Admissions } from "../modules/admissions/pages/Admissions";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import {
  admissionsApi,
  AdmissionsError,
} from "../modules/admissions/api/admissionsApi";
import type {
  Applicant,
  ApplicantDetail,
  AdmissionPage,
} from "../modules/admissions/api/admissionsApi";

vi.mock("../modules/admissions/api/admissionsApi", async (original) => {
  const actual =
    await original<typeof import("../modules/admissions/api/admissionsApi")>();
  return {
    ...actual,
    admissionsApi: {
      periods: vi.fn(),
      states: vi.fn(),
      filters: vi.fn(),
      applicants: vi.fn(),
      detail: vi.fn(),
      followups: vi.fn(),
      save: vi.fn(),
    },
  };
});
const applicant: Applicant = {
  id: 12,
  name: "Test Applicant",
  periodId: 3,
  period: "Active period",
  offerId: 21,
  offerPeriodId: 2,
  offerPeriod: "Previous period",
  programId: 1,
  program: "Test program",
  programSchedule: "Test schedule",
  registeredAt: "2026-10-01",
  sourceConfirmed: false,
};
const empty = <T,>(): AdmissionPage<T> => ({
  items: [],
  offset: 0,
  limit: 25,
  hasMore: false,
});
const detail: ApplicantDetail = {
  applicant: {
    ...applicant,
    documentTypeId: 2,
    document: "0012-A",
    mobile: "",
    phone: null,
    email: null,
  },
  schedules: [],
  matchingAvailable: true,
  matches: {
    ...empty(),
    items: [
      {
        id: 99,
        name: "Existing Test Student",
        offerId: 10,
        periodId: 1,
        period: "Historic period",
        program: "Historic program",
      },
    ],
  },
  history: empty(),
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(admissionsApi.periods).mockResolvedValue({
    items: [
      { id: 9, label: "Future period", active: false },
      { id: 3, label: "Active period", active: true },
    ],
    activePeriodId: 3,
    selectionRequired: false,
  });
  vi.mocked(admissionsApi.states).mockResolvedValue({
    items: [{ id: 1, label: "Real source state" }],
  });
  vi.mocked(admissionsApi.filters).mockImplementation(async (periodId) => ({
    periodId,
    items: [
      {
        programId: 1,
        program: "Test program",
        scheduleId: 4,
        schedule: "Test schedule",
      },
    ],
  }));
  vi.mocked(admissionsApi.applicants).mockImplementation(
    async (periodId, _query, offset) => ({
      items: [{ ...applicant, periodId }],
      offset,
      limit: 25,
      hasMore: offset === 0,
      periodId,
    }),
  );
  vi.mocked(admissionsApi.detail).mockResolvedValue(detail);
  vi.mocked(admissionsApi.followups).mockResolvedValue(empty());
});

describe("real admissions workspace", () => {
  it("combines source program and schedule, resets pages and clears filters while retaining the period", async () => {
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await screen.findByRole("button", { name: /Test Applicant/ });
    fireEvent.click(
      within(
        screen.getByRole("navigation", { name: "Páginas de aspirantes" }),
      ).getByRole("button", { name: "Siguiente" }),
    );
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        3,
        "",
        25,
        expect.any(AbortSignal),
        {},
      ),
    );
    fireEvent.change(screen.getByLabelText("Programa del aspirante"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText("Jornada del programa"), {
      target: { value: "4" },
    });
    const count = vi.mocked(admissionsApi.applicants).mock.calls.length;
    fireEvent.change(screen.getByLabelText("Buscar aspirante"), {
      target: { value: "Te" },
    });
    fireEvent.change(screen.getByLabelText("Buscar aspirante"), {
      target: { value: "Test" },
    });
    expect(admissionsApi.applicants).toHaveBeenCalledTimes(count);
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        3,
        "Test",
        0,
        expect.any(AbortSignal),
        { programId: 1, scheduleId: 4 },
      ),
    );
    expect(
      vi
        .mocked(admissionsApi.applicants)
        .mock.calls.slice(count)
        .some((call) => call[1] === "Te"),
    ).toBe(false);
    fireEvent.click(
      screen.getByRole("button", { name: "Restablecer filtros" }),
    );
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        3,
        "",
        0,
        expect.any(AbortSignal),
        {},
      ),
    );
    expect(screen.getByLabelText("Período al que aspira")).toHaveValue("3");
    fireEvent.change(screen.getByLabelText("Programa del aspirante"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText("Jornada del programa"), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText("Período al que aspira"), {
      target: { value: "9" },
    });
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        9,
        "",
        0,
        expect.any(AbortSignal),
        {},
      ),
    );
    expect(screen.getByLabelText("Programa del aspirante")).toHaveValue("");
    expect(screen.getByLabelText("Jornada del programa")).toHaveValue("");
  });

  it("ignores an old name request after a filter changes", async () => {
    let release!: (
      value: AdmissionPage<Applicant> & { periodId: number },
    ) => void;
    const original = vi
      .mocked(admissionsApi.applicants)
      .getMockImplementation()!;
    vi.mocked(admissionsApi.applicants).mockImplementation(
      (periodId, query, ...rest) =>
        query === "old"
          ? new Promise((resolve) => {
              release = resolve;
            })
          : original(periodId, query, ...rest),
    );
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await screen.findByRole("button", { name: /Test Applicant/ });
    fireEvent.change(screen.getByLabelText("Buscar aspirante"), {
      target: { value: "old" },
    });
    await waitFor(() => expect(release).toBeDefined());
    fireEvent.change(screen.getByLabelText("Buscar aspirante"), {
      target: { value: "Test" },
    });
    fireEvent.change(screen.getByLabelText("Programa del aspirante"), {
      target: { value: "1" },
    });
    await screen.findByRole("button", { name: /Test Applicant/ });
    await act(async () =>
      release({
        ...empty(),
        periodId: 3,
        items: [{ ...applicant, name: "Obsolete name" }],
      }),
    );
    expect(
      screen.queryByRole("button", { name: /Obsolete name/ }),
    ).not.toBeInTheDocument();
  });
  it("preserves the draft per applicant when period and selected record change", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await user.click(
      await screen.findByRole("button", { name: /Test Applicant/ }),
    );
    await screen.findByText("No hay seguimientos CRM registrados.");
    await user.type(
      screen.getByLabelText("Nota de seguimiento"),
      "Unconfirmed note",
    );
    await user.selectOptions(
      screen.getByLabelText("Estado del seguimiento"),
      "1",
    );
    await user.selectOptions(
      screen.getByLabelText("Período al que aspira"),
      "9",
    );
    await user.click(
      await screen.findByRole("button", { name: /Test Applicant/ }),
    );
    expect(screen.getByLabelText("Nota de seguimiento")).toHaveValue("");
    await user.selectOptions(
      screen.getByLabelText("Período al que aspira"),
      "3",
    );
    await user.click(
      await screen.findByRole("button", { name: /Test Applicant/ }),
    );
    expect(screen.getByLabelText("Nota de seguimiento")).toHaveValue(
      "Unconfirmed note",
    );
    expect(screen.getByLabelText("Estado del seguimiento")).toHaveValue("1");
  });
  it("selects source active period and resets pagination on manual period/search", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await screen.findByRole("button", { name: /Test Applicant/ });
    expect(screen.getByLabelText("Período al que aspira")).toHaveValue("3");
    expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
      3,
      "",
      0,
      expect.any(AbortSignal),
      {},
    );
    await user.click(
      within(
        screen.getByRole("navigation", { name: "Páginas de aspirantes" }),
      ).getByRole("button", { name: "Siguiente" }),
    );
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        3,
        "",
        25,
        expect.any(AbortSignal),
        {},
      ),
    );
    await user.selectOptions(
      screen.getByLabelText("Período al que aspira"),
      "9",
    );
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        9,
        "",
        0,
        expect.any(AbortSignal),
        {},
      ),
    );
    await user.type(screen.getByLabelText("Buscar aspirante"), "0012");
    await waitFor(() =>
      expect(admissionsApi.applicants).toHaveBeenLastCalledWith(
        9,
        "0012",
        0,
        expect.any(AbortSignal),
        {},
      ),
    );
  });

  it("requires explicit period when active source is ambiguous; never queries all", async () => {
    vi.mocked(admissionsApi.periods).mockResolvedValue({
      items: [{ id: 3, label: "Period", active: false }],
      activePeriodId: null,
      selectionRequired: true,
    });
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await screen.findByText(/SIIE no tiene un único período activo/);
    expect(admissionsApi.applicants).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
  });

  it("ignores old list response after period selection changes", async () => {
    let resolveOld!: (
      value: AdmissionPage<Applicant> & { periodId: number },
    ) => void;
    vi.mocked(admissionsApi.applicants).mockImplementation((periodId) =>
      periodId === 3
        ? new Promise((resolve) => {
            resolveOld = resolve;
          })
        : Promise.resolve({
            ...empty(),
            items: [
              { ...applicant, id: 15, name: "New period applicant", periodId },
            ],
            periodId,
          }),
    );
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await waitFor(() => expect(admissionsApi.applicants).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText("Período al que aspira"), {
      target: { value: "9" },
    });
    await screen.findByRole("button", { name: /New period applicant/ });
    await act(async () =>
      resolveOld({ ...empty(), items: [applicant], periodId: 3 }),
    );
    expect(
      screen.queryByRole("button", { name: /Test Applicant/ }),
    ).not.toBeInTheDocument();
  });

  it("shows distinct offer period and historic student candidates only on detail", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    expect(admissionsApi.detail).not.toHaveBeenCalled();
    await user.click(
      await screen.findByRole("button", { name: /Test Applicant/ }),
    );
    expect(await screen.findByText("Existing Test Student")).toBeVisible();
    expect(screen.getByText(/El período de la oferta/)).toHaveTextContent(
      "Previous period",
    );
    expect(screen.getByText(/Estudiante #99/)).toHaveTextContent(
      "Historic period",
    );
    expect(screen.getByText(/no se fusionan personas/)).toBeVisible();
  });

  it("preserves note and operation identity after uncertain save; clears only confirmed", async () => {
    const user = userEvent.setup();
    vi.mocked(admissionsApi.save)
      .mockRejectedValueOnce(new TypeError("network"))
      .mockResolvedValue(empty());
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await user.click(
      await screen.findByRole("button", { name: /Test Applicant/ }),
    );
    await screen.findByText("No hay seguimientos CRM registrados.");
    await user.type(
      screen.getByLabelText("Nota de seguimiento"),
      "Test CRM follow-up",
    );
    await user.selectOptions(
      screen.getByLabelText("Estado del seguimiento"),
      "1",
    );
    await user.click(
      screen.getByRole("button", { name: "Guardar seguimiento" }),
    );
    await screen.findByText(/No se confirmó el guardado/);
    expect(screen.getByLabelText("Nota de seguimiento")).toHaveValue(
      "Test CRM follow-up",
    );
    await user.click(
      screen.getByRole("button", { name: "Guardar seguimiento" }),
    );
    await screen.findByText("Seguimiento confirmado.");
    expect(admissionsApi.save).toHaveBeenCalledTimes(2);
    expect(vi.mocked(admissionsApi.save).mock.calls[0]).toEqual(
      vi.mocked(admissionsApi.save).mock.calls[1],
    );
    expect(screen.getByLabelText("Nota de seguimiento")).toHaveValue("");
  });

  it("keeps edited draft after server conflict", async () => {
    const user = userEvent.setup();
    vi.mocked(admissionsApi.followups).mockResolvedValue({
      ...empty(),
      items: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          body: "Original",
          stateId: 1,
          state: "Real source state",
          dueDate: null,
          revision: 1,
          createdAt: "2026-10-01",
          updatedAt: "2026-10-01",
        },
      ],
    });
    vi.mocked(admissionsApi.save).mockRejectedValue(new AdmissionsError(409));
    render(
      <WorkspaceSessionProvider>
        <Admissions />
      </WorkspaceSessionProvider>,
    );
    await user.click(
      await screen.findByRole("button", { name: /Test Applicant/ }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Editar seguimiento" }),
    );
    await user.type(screen.getByLabelText("Nota de seguimiento"), " edited");
    await user.click(
      screen.getByRole("button", { name: "Guardar seguimiento" }),
    );
    await screen.findByText(/El seguimiento cambió/);
    expect(screen.getByLabelText("Nota de seguimiento")).toHaveValue(
      "Original edited",
    );
  });
});
