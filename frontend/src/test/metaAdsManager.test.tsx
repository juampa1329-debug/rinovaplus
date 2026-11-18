import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AdsWorkspace } from "../institution/AdsWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
import { objectMetrics, safeAdUrl } from "../institution/metaAdsData";
import type { Snapshot } from "../institution/metaAdsData";

const session: Session = {
  session_id: "s",
  csrf_token: "csrf",
  actions: ["ads.manage", "crm.read", "settings.channels.write"],
  user: {
    id: "owner",
    email: "owner@cbn.local",
    full_name: "Equipo",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const base = {
  spend: 120,
  impressions: 1200,
  clicks: 12,
  reach: 700,
  leads: 3,
  ctr: 1,
  cpc: 10,
  cpl: 40,
  cpm: 100,
  conversations: 1,
};
const snapshot: Snapshot = {
  synced_at: "2026-11-18T14:00:00Z",
  no_delivery: false,
  account: {
    id: "123",
    name: "CBN",
    currency: "COP",
    timezone: "America/Bogota",
  },
  period: { start: "2026-11-01", end: "2026-11-18" },
  totals: base,
  daily: [1, 2, 3, 4].map((v) => ({ ...base, date: `2026-11-0${v}` })),
  campaigns: [
    { id: "11", name: "Campaña Software", effective_status: "PAUSED" },
  ],
  adsets: [{ id: "22", name: "Conjunto CBN", campaign_id: "11" }],
  ads: [
    {
      id: "33",
      name: "Anuncio CBN",
      campaign_id: "11",
      adset_id: "22",
      creative: {
        title: "Software",
        body: "Conoce el programa",
        image_url: "https://example.com/image.png",
        destination_url: "https://example.com/software",
      },
    },
  ],
  ad_insights: [{ ...base, ad_id: "33", campaign_id: "11", adset_id: "22" }],
};
afterEach(() => {
  vi.restoreAllMocks();
  window.location.hash = "";
});
beforeEach(() => {
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.open = true;
      },
    },
    close: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.open = false;
      },
    },
  });
});

function mount({ connected = true, value = snapshot as Snapshot | null } = {}) {
  const calls: {
    path: string;
    method: string;
    body: Record<string, unknown>;
  }[] = [];
  const drafts: Record<string, unknown>[] = [];
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const path = new URL(String(input), "http://cbn.local").pathname.replace(
        "/api/institution/",
        "",
      );
      const method = init?.method ?? "GET",
        body = init?.body ? JSON.parse(String(init.body)) : {};
      calls.push({ path, method, body });
      let result: unknown = {};
      if (path === "ads/options")
        result = {
          accounts: connected
            ? [
                {
                  id: "account",
                  name: "CBN",
                  external_account_id: "123",
                  provider: "meta",
                  revision: 1,
                  status: "connected",
                },
              ]
            : [],
          integrations: [
            { id: "source", name: "Facebook CBN", provider: "meta" },
          ],
        };
      else if (path.endsWith("/snapshot")) result = { snapshot: value };
      else if (path.endsWith("/drafts")) {
        if (method === "POST") {
          const row = {
            ...body,
            id: "draft1",
            revision: 1,
            state: "draft",
            review_valid: false,
            provider_writes: false,
          };
          drafts.push(row);
          result = row;
        } else result = { items: drafts };
      } else if (path.endsWith("/sync")) result = snapshot;
      else if (path.endsWith("/review"))
        result = {
          reviewed: true,
          issues: [],
          message: "Revisión local completada.",
        };
      return new Response(JSON.stringify(result), { status: 200 });
    });
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      <AdsWorkspace />
    </SessionBoundary>,
  );
  return { calls, fetcher };
}

it("shows connection guidance without fabricated KPIs", async () => {
  mount({ connected: false });
  expect(
    await screen.findByText("Conecta tu primera cuenta"),
  ).toBeInTheDocument();
  expect(screen.queryByText("Importe gastado")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Conectar con Meta" }),
  ).toBeEnabled();
});

it("renders source, period, real hierarchy and accessible daily data", async () => {
  mount();
  expect(await screen.findByText("Importe gastado")).toBeInTheDocument();
  expect(screen.getByText(/Meta Marketing API/)).toBeInTheDocument();
  expect(
    screen.getByRole("img", { name: /Gasto por día/ }),
  ).toBeInTheDocument();
  expect(screen.getByText("Ver datos diarios en tabla")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Anuncios (1)" }));
  fireEvent.click(screen.getByRole("button", { name: "Anuncio CBN" }));
  expect(
    screen.getByRole("article", { name: "Vista previa del anuncio" }),
  ).toBeInTheDocument();
});

it("period change clears old results rather than labelling stale data", async () => {
  const { fetcher } = mount();
  await screen.findByText("Importe gastado");
  fetcher.mockImplementation(
    async () => new Response(JSON.stringify({ snapshot: null })),
  );
  fireEvent.change(screen.getByLabelText("Desde"), {
    target: { value: "2026-11-01" },
  });
  fireEvent.change(screen.getByLabelText("Hasta"), {
    target: { value: "2026-11-02" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Ver período" }));
  expect(
    await screen.findByText("Sin consulta para este período"),
  ).toBeInTheDocument();
  expect(screen.queryByText("Importe gastado")).not.toBeInTheDocument();
});

it("sync is explicit and bound to account revision and selected period", async () => {
  const { calls } = mount({ value: null });
  await screen.findByText("Sin consulta para este período");
  fireEvent.click(screen.getByRole("button", { name: "Sincronizar con Meta" }));
  await waitFor(() =>
    expect(calls.some((v) => v.path === "ads/meta/account/sync")).toBe(true),
  );
  const call = calls.find((v) => v.path.endsWith("/sync"))!;
  expect(call.method).toBe("POST");
  expect(call.body.revision).toBe(1);
  expect(call.body.start).toMatch(/^\d{4}-\d{2}-\d{2}$/);
});

it("saves local drafts and requests review without advertising publish calls", async () => {
  const { calls } = mount();
  await screen.findByText("Importe gastado");
  fireEvent.click(screen.getByRole("button", { name: "Borradores locales" }));
  await screen.findByText("Aún no hay borradores guardados en esta cuenta.");
  fireEvent.click(screen.getByRole("button", { name: "Crear borrador" }));
  fireEvent.change(screen.getByLabelText("Nombre del borrador"), {
    target: { value: "Propuesta de Software" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar versión del borrador" }),
  );
  expect(await screen.findByText("Propuesta de Software")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Revisar" }));
  expect(
    await screen.findByRole("dialog", { name: "Resultado de revisión local" }),
  ).toBeInTheDocument();
  expect(
    calls
      .filter((v) => v.method === "POST")
      .every((v) => v.path.includes("/drafts")),
  ).toBe(true);
});

it("aggregates additive metrics while keeping unique reach and weighted ratios honest", () => {
  const data = {
    ...snapshot,
    ad_insights: [
      ...snapshot.ad_insights,
      {
        ...snapshot.ad_insights[0],
        ad_id: "34",
        spend: 60,
        clicks: 6,
        impressions: 300,
      },
    ],
  };
  const value = objectMetrics(data, "campaigns", "11")!;
  expect(value.spend).toBe(180);
  expect(value.ctr).toBe((18 / 1500) * 100);
  expect(value.reach).toBeNull();
  expect(objectMetrics(data, "ads", "missing")).toBeNull();
});

it("rejects unsafe creative links", () => {
  expect(safeAdUrl("javascript:alert(1)")).toBeUndefined();
  expect(safeAdUrl("https://user:secret@example.com")).toBeUndefined();
  expect(safeAdUrl("https://example.com/image.png")).toBe(
    "https://example.com/image.png",
  );
});
