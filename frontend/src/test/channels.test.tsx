import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChannelSettings } from "../features/ChannelSettings";
import { mockChannelSettings } from "./localClientsMock";
import { channelKeys, channelReferences } from "../shared/channels";
describe("channel capability truth", () => {
  it("lists real channel configuration and opens its masked editor without activating a connection", async () => {
    const requests = mockChannelSettings();
    render(<ChannelSettings />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Actualizar estado" }),
      ).toBeEnabled(),
    );
    for (const key of channelKeys)
      expect(
        screen.getByRole("heading", { name: channelReferences[key].name }),
      ).toBeVisible();
    for (const button of screen.getAllByRole("button", { name: "Conectar" }))
      expect(button).toBeEnabled();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    const section = screen
      .getByRole("heading", { name: "WhatsApp" })
      .closest("section")!;
    fireEvent.click(within(section).getByRole("button", { name: "Conectar" }));
    expect(screen.getByLabelText("Access Token")).toHaveAttribute(
      "type",
      "password",
    );
    expect(screen.getByLabelText("Phone Number ID")).toHaveValue("");
    expect(
      requests.mock.calls.every(
        ([, method]) => method === undefined || method === "GET",
      ),
    ).toBe(true);
    fireEvent.click(
      within(section).getByRole("button", { name: "Cerrar configuración" }),
    );
    expect(screen.queryByLabelText("Access Token")).not.toBeInTheDocument();
  });
});
