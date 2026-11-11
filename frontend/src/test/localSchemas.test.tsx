import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { ChannelSettings } from "../features/ChannelSettings";
import { mockChannelSettings } from "./localClientsMock";
import catalog from "../shared/endpointCatalog.json";

it("keeps the finite local metadata inventory and pending connected approval", () => {
  const business = catalog.routes.filter(
    (route) => route.response_status === 501,
  );
  expect(catalog.routes).toHaveLength(157);
  expect(business).toHaveLength(134);
  expect(catalog.superseded_proposals).toHaveLength(14);
  expect(catalog.superseded_proposals[0].path).toBe("/api/v1/catalog/programs");
  expect(
    catalog.superseded_proposals.map(
      (route) => `${route.method} ${route.path}`,
    ),
  ).toEqual([
    "GET /api/v1/catalog/programs",
    "GET /api/v1/channels",
    "POST /api/v1/channels/whatsapp/number-registration",
    "POST /api/v1/channels/whatsapp/number-verification",
    "GET /api/v1/channels/whatsapp/numbers",
    "GET /api/v1/channels/{channel}",
    "POST /api/v1/channels/{channel}/activation",
    "GET /api/v1/channels/{channel}/capabilities",
    "POST /api/v1/channels/{channel}/connection-tests",
    "POST /api/v1/channels/{channel}/discovery",
    "PUT /api/v1/channels/{channel}/draft",
    "POST /api/v1/channels/{channel}/pause",
    "GET /api/v1/channels/{channel}/webhook-reference",
    "POST /api/v1/webhooks/{channel}",
  ]);
  for (const proposal of catalog.superseded_proposals.slice(1, -1)) {
    expect(
      catalog.routes.find(
        (route) =>
          route.method === proposal.method && route.path === proposal.path,
      ),
    ).toMatchObject({
      connected_status: "local_operational",
      response_status: 200,
      source_locator: "backend/app/modules/channels/router.py",
    });
  }
  expect(
    catalog.routes.some(
      (route) =>
        route.method === "POST" && route.path === "/api/v1/webhooks/{channel}",
    ),
  ).toBe(false);
  for (const path of ["/api/v1/webhooks/meta", "/api/v1/webhooks/tiktok"])
    expect(
      catalog.routes.find(
        (route) => route.method === "POST" && route.path === path,
      ),
    ).toMatchObject({ connected_status: "local_operational" });
  expect(
    business.filter((route) => route.schema_status === "local_defined"),
  ).toHaveLength(122);
  expect(
    business.filter((route) => route.schema_status === "provisional"),
  ).toHaveLength(12);
  expect(
    business.every((route) => route.connected_status === "approval_pending"),
  ).toBe(true);
  expect(business.every((route) => route.schema_revision === "local-v2")).toBe(
    true,
  );
  expect(business.filter((route) => route.phase.startsWith("7"))).toHaveLength(
    38,
  );
});

it("keeps operational channel configuration distinct from the remaining contract stubs without activating services", async () => {
  const requests = mockChannelSettings();
  const user = userEvent.setup();
  render(<ChannelSettings />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Actualizar estado" }),
    ).toBeEnabled(),
  );
  const section = screen
    .getByRole("heading", { name: "WhatsApp" })
    .closest("section")!;
  await user.click(within(section).getByRole("button", { name: "Conectar" }));
  expect(
    screen.getByLabelText("WhatsApp Business Account ID (WABA)"),
  ).toBeVisible();
  expect(screen.getByLabelText("Access Token")).toHaveAttribute(
    "type",
    "password",
  );
  expect(
    screen.queryByText("Contratos propios API · Stubs 501"),
  ).not.toBeInTheDocument();
  expect(
    requests.mock.calls.every(
      ([, method]) => method === undefined || method === "GET",
    ),
  ).toBe(true);
});
