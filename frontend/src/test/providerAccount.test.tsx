import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ProviderAccount } from "../institution/ProviderAccount";

const { call } = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../institution/api", () => ({ useInstitution: () => ({ call }) }));
beforeEach(() => {
  call.mockReset();
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
});
afterEach(() => {
  Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal");
  vi.restoreAllMocks();
});

it("reads only when opened, separates key allowance from balance, and keeps payment external", async () => {
  call.mockResolvedValue({
    checked_at: "2026-11-22T23:00:00Z",
    account_status: "management_key_required",
    key: { usage: 1.23, usage_daily: 0, limit: null, limit_remaining: null },
  });
  render(<ProviderAccount provider="openrouter" />);
  expect(call).not.toHaveBeenCalled();
  const trigger = screen.getByRole("button", {
    name: "Saldo y consumo de OpenRouter",
  });
  fireEvent.click(trigger);
  await screen.findByText(/OpenRouter exige una Management API key/);
  expect(await screen.findByText("USD 1,23")).toBeVisible();
  expect(screen.getByText("Sin límite fijado")).toBeVisible();
  expect(screen.getByText("Depende del saldo de la cuenta")).toBeVisible();
  expect(call.mock.calls).toEqual([["provider-balance/openrouter"]]);
  expect(
    screen.getByRole("link", { name: /Recargar en OpenRouter/ }),
  ).toHaveAttribute("href", "https://openrouter.ai/settings/credits");
  fireEvent.click(screen.getByRole("button", { name: "Cerrar detalle" }));
  expect(trigger).toHaveFocus();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("shows ElevenLabs units and voice slots with a manual refresh and no subscription write", async () => {
  call.mockResolvedValue({
    checked_at: "2026-11-22T23:00:00Z",
    quota: {
      used: 25,
      limit: 100,
      remaining: 75,
      tier: "creator",
      reset_at: null,
    },
    voice_slots: { voice_slots_used: 2, voice_limit: 10 },
    overage_enabled: false,
  });
  render(<ProviderAccount provider="elevenlabs" />);
  fireEvent.click(
    screen.getByRole("button", { name: "Saldo y consumo de ElevenLabs" }),
  );
  await screen.findByText("75");
  expect(screen.getByText("No informada")).toBeVisible();
  expect(
    screen.getByRole("progressbar", { name: "Uso del plan ElevenLabs" }),
  ).toHaveAttribute("value", "25");
  expect(screen.queryByText(/USD/)).not.toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar saldo y consumo" }),
  );
  await waitFor(() => expect(call).toHaveBeenCalledTimes(2));
  expect(
    call.mock.calls.every(
      ([path, ...rest]) =>
        path === "provider-balance/elevenlabs" && !rest.length,
    ),
  ).toBe(true);
});

it("preserves dated prior data if manual refresh fails", async () => {
  call
    .mockResolvedValueOnce({
      checked_at: "2026-11-22T23:00:00Z",
      account: { total_credits: 10, total_usage: 1, remaining: 9 },
      key: null,
    })
    .mockRejectedValueOnce(Error("No se pudo consultar"));
  render(<ProviderAccount provider="openrouter" />);
  fireEvent.click(
    screen.getByRole("button", { name: "Saldo y consumo de OpenRouter" }),
  );
  await screen.findByText("USD 9");
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar saldo y consumo" }),
  );
  await screen.findByText(/Se conserva la consulta anterior/);
  expect(screen.getByText("USD 9")).toBeVisible();
  expect(screen.getByText(/Bogotá · Consulta anterior/)).toBeVisible();
});
