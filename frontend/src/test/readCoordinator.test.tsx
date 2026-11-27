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

it("recovers a transient Inbox search 503, sharing the retry and preserving the exact query", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(4_000_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      response({ detail: "general_storage_unavailable" }, 503),
    )
    .mockResolvedValue(response({ items: [{ name: "Patry" }] }));
  const path = "workspace/inbox?offset=0&livePages=true&q=patry";
  const reads = Promise.all([send(path), send(path)]);
  await vi.advanceTimersByTimeAsync(1000);
  expect(await reads).toEqual([
    { items: [{ name: "Patry" }] },
    { items: [{ name: "Patry" }] },
  ]);
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(
    fetcher.mock.calls.every(
      (v) => v[0] === `/api/institution/${path}` && v[1]?.method === "GET",
    ),
  ).toBe(true);
});

it("bounds Inbox 503 recovery and never retries the same path as a POST", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(4_100_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () =>
      response({ detail: "general_storage_unavailable" }, 503),
    );
  const path = "workspace/inbox?q=bounded-patry";
  const read = send(path).catch((error: unknown) => error);
  await vi.advanceTimersByTimeAsync(5000);
  expect(await read).toMatchObject({ status: 503 });
  expect(fetcher).toHaveBeenCalledTimes(3);
  await expect(send(path, "POST", {})).rejects.toMatchObject({ status: 503 });
  await vi.advanceTimersByTimeAsync(5000);
  expect(fetcher).toHaveBeenCalledTimes(4);
});

it.each([401, 403])(
  "does not retry authorization status %s for Inbox searches",
  async (status) => {
    vi.useFakeTimers();
    vi.setSystemTime(4_200_000);
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(response({ detail: "session_required" }, status));
    await expect(send("workspace/inbox?q=patry")).rejects.toMatchObject({
      status,
    });
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetcher).toHaveBeenCalledTimes(1);
  },
);

it.each(["institution", "agents"])(
  "recovers one pre-work busy GET for %s without duplicating concurrent reads",
  async (client) => {
    vi.useFakeTimers();
    vi.setSystemTime(9_000);
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ detail: "storage_busy" }, 503))
      .mockResolvedValue(response({ ok: true }));
    const load = () =>
      client === "agents" ? api("/busy-fixture") : send("busy-fixture");
    const reads = Promise.all([load(), load()]);
    await vi.advanceTimersByTimeAsync(999);
    expect(fetcher).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(await reads).toEqual([{ ok: true }, { ok: true }]);
    expect(fetcher).toHaveBeenCalledTimes(2);
  },
);

it("bounds busy recovery to two extra GETs and never repeats a mutation", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(10_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => response({ detail: "storage_busy" }, 503));
  const read = send("still-busy").catch((error: unknown) => error);
  await vi.advanceTimersByTimeAsync(5000);
  expect(await read).toMatchObject({ status: 503, detail: "storage_busy" });
  expect(fetcher).toHaveBeenCalledTimes(3);
  await expect(
    send("send-message", "POST", { body: "fixture" }),
  ).rejects.toMatchObject({ detail: "storage_busy" });
  await vi.advanceTimersByTimeAsync(5000);
  expect(fetcher).toHaveBeenCalledTimes(4);
});

it("coalesces readers through a burst of two known lock waits", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(16_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response({ detail: "storage_busy" }, 503))
    .mockResolvedValueOnce(response({ detail: "storage_busy" }, 503))
    .mockResolvedValue(response({ messages: ["current"] }));
  const reads = Promise.all([send("burst-busy"), send("burst-busy")]);
  await vi.advanceTimersByTimeAsync(3999);
  expect(fetcher).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(1);
  expect(await reads).toEqual([
    { messages: ["current"] },
    { messages: ["current"] },
  ]);
  expect(fetcher).toHaveBeenCalledTimes(3);
});

it.each([
  [503, "general_storage_unavailable"],
  [401, "session_required"],
  [403, "permission_denied"],
])("does not replay HTTP %s %s as a lock timeout", async (status, detail) => {
  vi.useFakeTimers();
  vi.setSystemTime(20_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(response({ detail }, status));
  await expect(send("not-a-busy-lock")).rejects.toMatchObject({
    status,
    detail,
  });
  await vi.advanceTimersByTimeAsync(5000);
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("does not bypass an observed rate limit during busy recovery", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(30_000);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(response({ detail: "storage_busy" }, 503));
  const read = send("busy-before-rate-limit").catch((error: unknown) => error);
  await vi.advanceTimersByTimeAsync(500);
  observeReadLimit("60");
  await vi.advanceTimersByTimeAsync(1000);
  expect(await read).toMatchObject({ detail: "storage_busy" });
  expect(fetcher).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(60_001);
});

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
  await expect(send("inbox")).rejects.toMatchObject({
    status: 429,
    retryAfterSeconds: 300,
  });
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

it("retries a one-shot history GET after Retry-After without repeating a mutation", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(9_000_000);
  vi.spyOn(document, "hasFocus").mockReturnValue(true);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      response({ detail: "rate_limited" }, 429, { "Retry-After": "2" }),
    )
    .mockResolvedValue(response({ total: 9 }));
  function View() {
    const read = useRead<{ total: number }>(
      "conversations/fixture/messages",
      0,
      true,
      0,
    );
    return <span>{read.value?.total ?? read.error}</span>;
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
  const view = render(
    <SessionBoundary initial={initial} expire={vi.fn()}>
      <View />
    </SessionBoundary>,
  );
  await act(() => vi.advanceTimersByTimeAsync(200));
  expect(fetcher).toHaveBeenCalledTimes(1);
  await act(() => vi.advanceTimersByTimeAsync(2100));
  expect(screen.getByText("9")).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(
    fetcher.mock.calls.every((v) => !v[1]?.method || v[1].method === "GET"),
  ).toBe(true);
  await act(() => vi.advanceTimersByTimeAsync(60_000));
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(fetcher).toHaveBeenCalledTimes(2);
  view.unmount();
});
