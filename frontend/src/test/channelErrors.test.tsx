import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { Channels } from "../institution/Channels";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";

const session: Session = {
  session_id: "session",
  csrf_token: "csrf",
  actions: ["settings.channels.read", "settings.channels.write"],
  user: {
    id: "owner",
    email: "owner@example.test",
    full_name: "Owner",
    active: true,
    role: "owner",
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};

const graphVersion = "meta:whatsapp_graph_api_version";
const account = {
  id: "channel",
  application_id: "application",
  display_name: "Cuenta de prueba",
  channel: "whatsapp",
  provider_operations_available: true,
  issuer_profile: "meta_whatsapp",
  verified_status: "unverified",
  revision: 1,
  row_version: "version",
  application_version: "application-version",
  fields: { [graphVersion]: "v26.0" },
};

beforeEach(() => {
  const dialog = HTMLDialogElement.prototype;
  if (!dialog.showModal) {
    dialog.showModal = function () {
      this.open = true;
    };
    dialog.close = function () {
      this.open = false;
    };
  }
});

function openChannels() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options?: RequestInit) => {
      const path = url.replace("/api/institution/", "");
      if (path === "channels" && options?.method === "GET") {
        return Response.json({ items: [account] });
      }
      if (path === "channels/catalog") {
        return Response.json({
          provider_operations_available: true,
          groups: [
            {
              id: "whatsapp",
              label: "WhatsApp",
              applies_to_channels: ["whatsapp"],
            },
          ],
          fields: [
            {
              id: graphVersion,
              group: "whatsapp",
              label: "Graph API",
              input_type: "text",
              field_kind: "input",
              editable_in_p2: true,
              value_type: "string",
            },
          ],
        });
      }
      if (path === "channels/channel/history") {
        return Response.json({ queue: [], events: [], operations: [] });
      }
      if (path === "channels/channel" && options?.method === "PUT") {
        return Response.json({ detail: "revision_conflict" }, { status: 409 });
      }
      if (path === "channels/channel/actions/verify") {
        return Response.json({
          status: "failed",
          code: "token_application_mismatch_or_invalid",
          result: {},
        });
      }
      if (path === "channels/channel/actions/subscribe") {
        return Response.json({
          status: "uncertain",
          code: "provider_effect_not_confirmed",
          result: {},
        });
      }
      return Response.json({ items: [], stages: [] });
    }),
  );
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      <Channels openWebhooks={() => {}} />
    </SessionBoundary>,
  );
}

it("explains a provider rejection returned with HTTP 200 and restores keyboard focus", async () => {
  openChannels();
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: /Cuenta de prueba/ }),
  );
  const verify = screen.getByRole("button", {
    name: "Verificar token y cuenta",
  });
  await user.click(verify);
  const dialog = await screen.findByRole("alertdialog", {
    name: "Meta no confirmó el token para esta app",
  });
  expect(dialog).toHaveAccessibleDescription(/depurador de Meta.*App ID/);
  expect(
    within(dialog).getByRole("button", { name: "Cerrar aviso" }),
  ).toHaveFocus();
  expect(screen.queryByText("Cambios guardados.")).not.toBeInTheDocument();
  fireEvent(dialog, new Event("cancel", { cancelable: true }));
  expect(dialog).not.toBeInTheDocument();
  expect(verify).toHaveFocus();
});

it("retains edits after a save fails", async () => {
  openChannels();
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: /Cuenta de prueba/ }),
  );
  const field = screen.getByRole("textbox", { name: "Graph API" });
  await user.clear(field);
  await user.type(field, "v27.0");
  await user.click(screen.getByRole("button", { name: "Guardar cuenta" }));
  const conflict = await screen.findByRole("alertdialog", {
    name: "La cuenta cambió mientras la editabas",
  });
  await user.click(
    within(conflict).getByRole("button", { name: "Cerrar aviso" }),
  );
  expect(field).toHaveValue("v27.0");
});

it("gives safe guidance for uncertain effects", async () => {
  openChannels();
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: /Cuenta de prueba/ }));
  await user.click(
    screen.getByRole("button", { name: "Sincronizar suscripción" }),
  );
  const uncertain = await screen.findByRole("alertdialog", {
    name: "Resultado sin confirmar",
  });
  expect(uncertain).toHaveAccessibleDescription(
    /antes de repetir la operación/,
  );
});
