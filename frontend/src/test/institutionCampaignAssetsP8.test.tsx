import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CampaignAssetInput } from "../institution/CampaignAssetInput";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
const session: Session = {
  session_id: "s",
  csrf_token: "asset-csrf",
  actions: ["campaigns.manage", "crm.read"],
  user: {
    id: "u",
    email: "u@cbn.local",
    full_name: "Orientación",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const originalDevices = navigator.mediaDevices;
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: originalDevices,
  });
});
function mount(kind = "image") {
  const changed = vi.fn(),
    busy = vi.fn(),
    fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "asset",
            name: "orientacion.png",
            kind,
            size: 5,
          }),
          { headers: { "Content-Type": "application/json" } },
        ),
      );
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      <CampaignAssetInput
        kind={kind}
        id="file"
        onChange={changed}
        onBusy={busy}
      />
    </SessionBoundary>,
  );
  return { changed, busy, fetcher };
}
it("uploads a file with institution CSRF and updates only its template block", async () => {
  const { changed, fetcher, busy } = mount();
  fireEvent.change(screen.getByLabelText("Subir imagen"), {
    target: {
      files: [new File(["bytes"], "orientacion.png", { type: "image/png" })],
    },
  });
  await waitFor(() =>
    expect(changed).toHaveBeenCalledWith("asset", "orientacion.png"),
  );
  const [, init] = fetcher.mock.calls[0];
  const body = JSON.parse(String(init?.body));
  expect(body.kind).toBe("image");
  expect(body.content_base64).toBe("Ynl0ZXM=");
  expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("asset-csrf");
  expect(busy).toHaveBeenLastCalledWith(false);
  expect(
    fetcher.mock.calls.every(([p]) => !String(p).endsWith("/activate")),
  ).toBe(true);
});
it("rejects oversized media before sending its contents", async () => {
  const { fetcher } = mount();
  const file = new File(["x"], "grande.png");
  Object.defineProperty(file, "size", { value: 5000001 });
  fireEvent.change(screen.getByLabelText("Subir imagen"), {
    target: { files: [file] },
  });
  expect(
    await screen.findByText("El archivo supera 5 MB."),
  ).toBeInTheDocument();
  expect(fetcher).not.toHaveBeenCalled();
});
it("records only after a user gesture, stops tracks and uploads the resulting audio", async () => {
  const stop = vi.fn(),
    getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia },
  });
  class Recorder {
    state = "inactive";
    mimeType = "audio/webm";
    ondataavailable: ((e: { data: Blob }) => void) | null = null;
    onstop: (() => void) | null = null;
    start() {
      this.state = "recording";
    }
    stop() {
      this.state = "inactive";
      this.ondataavailable?.({
        data: new Blob(["audio"], { type: "audio/webm" }),
      });
      this.onstop?.();
    }
  }
  vi.stubGlobal("MediaRecorder", Recorder);
  const { changed } = mount("audio");
  expect(getUserMedia).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Grabar audio" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Detener grabación" }),
  );
  await waitFor(() => expect(changed).toHaveBeenCalled());
  expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
  expect(stop).toHaveBeenCalled();
});
