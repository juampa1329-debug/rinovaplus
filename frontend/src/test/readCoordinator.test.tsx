import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError, send, SessionBoundary } from "../institution/api";
import { useRead } from "../institution/Workspace";
import { api } from "../modules/agents/api";
import { observeReadLimit } from "../institution/readCoordinator";
import { VersionNotice } from "../institution/VersionNotice";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});
const response = (body: unknown, status = 200, headers?: HeadersInit) =>
  new Response(JSON.stringify(body), { status, headers });

it("coalesces simultaneous reads, partitions credentials, and never coalesces writes", async () => {
  let release!: () => void;
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
    await blocked;
    return response({ items: [] });
  });
  const reads = [
    send("fixture", "GET", undefined, "a"),
    send("fixture", "GET", undefined, "a"),
    send("fixture", "GET", undefined, "b"),
  ];
  expect(fetcher).toHaveBeenCalledTimes(2);
  release();
  await Promise.all(reads);
  await Promise.all([send("fixture", "POST", {}), send("fixture", "POST", {})]);
  expect(fetcher).toHaveBeenCalledTimes(4);
});

it("pauses all read clients for Retry-After without replaying mutations", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(1_000_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      response({ detail: "rate_limited" }, 429, { "Retry-After": "60" }),
    )
    .mockImplementation(async () => response({ ok: true }));
  await expect(send("inbox")).rejects.toBeInstanceOf(ApiError);
  await expect(send("comments/notifications")).rejects.toMatchObject({
    status: 429,
  });
  await expect(api("/selection")).rejects.toThrow("pausa");
  expect(fetcher).toHaveBeenCalledTimes(1);
  await send("message", "POST", { body: "fixture" });
  expect(fetcher).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(60_001);
  await send("inbox");
  expect(fetcher).toHaveBeenCalledTimes(3);
  observeReadLimit(new Date(Date.now() + 30_000).toUTCString());
  await expect(send("inbox")).rejects.toMatchObject({ status: 429 });
  await vi.advanceTimersByTimeAsync(30_001);
  observeReadLimit("600");
  await vi.advanceTimersByTimeAsync(300_000);
  await expect(send("inbox")).rejects.toMatchObject({ status: 429, retryAfterSeconds: 300 });
  await vi.advanceTimersByTimeAsync(300_001);
});

it("keeps a stable poll across parent rerenders, stops without focus and resumes on focus", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(2_000_000);
  const focused = vi.spyOn(document, "hasFocus").mockReturnValue(true);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => response({ revision: "1", total: 2 }));
  function View() {
    const read = useRead<{ total: number }>(
      "inbox?offset=0",
      0,
      true,
      3000,
      true,
    );
    return <span>{read.value?.total}</span>;
  }
  const initial = {
    session_id: "s",
    csrf_token: "token",
    actions: [],
    user: {
      id: "u",
      email: "u@example.invalid",
      full_name: "Test",
      active: true,
      role: "test",
      revision: 1,
      profile: {},
      mfa_state: "disabled",
    },
  };
  const expire = vi.fn();
  const view = render(
    <SessionBoundary initial={initial} expire={expire}>
      <View />
    </SessionBoundary>,
  );
  await act(() => vi.advanceTimersByTimeAsync(200));
  expect(screen.getByText("2")).toBeInTheDocument();
  view.rerender(
    <SessionBoundary initial={initial} expire={expire}>
      <View />
    </SessionBoundary>,
  );
  await act(() => vi.advanceTimersByTimeAsync(200));
  expect(fetcher).toHaveBeenCalledTimes(1);
  focused.mockReturnValue(false);
  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(fetcher).toHaveBeenCalledTimes(1);
  focused.mockReturnValue(true);
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(fetcher).toHaveBeenCalledTimes(2);
  view.unmount();
});

it("offers manual update on version change without forcing a reload", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(3_000_000);
  const meta = document.createElement("meta");
  meta.name = "rinova-build";
  meta.content = "old";
  document.head.append(meta);
  vi.spyOn(document, "hasFocus").mockReturnValue(true);
  vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ build: "new" }));
  const view = render(<VersionNotice />);
  await act(() => vi.advanceTimersByTimeAsync(60_001));
  expect(
    screen.getByRole("button", { name: "Recargar RinovaPlus" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Guarda tus cambios/)).toBeInTheDocument();
  view.unmount();
  meta.remove();
});
