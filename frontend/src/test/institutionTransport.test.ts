import { expect, it, vi } from "vitest";
import { ApiError, send } from "../institution/api";

it("explains a classified database failure without reporting an access failure or replaying it", async () => {
  const fetcher = vi.fn(async () => Response.json(
    { detail: "general_storage_unavailable" }, { status: 503 },
  ));
  vi.stubGlobal("fetch", fetcher);
  const error = await send("broadcasts/fixture/report?transport-test=storage").catch((reason: unknown) => reason);
  expect(error).toMatchObject({ status: 503, detail: "general_storage_unavailable" });
  expect((error as Error).message).toContain("consulta a la base de datos");
  expect((error as Error).message).not.toMatch(/validar el acceso|clave|IA/);
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("explains a plain-text gateway failure without leaking its body or a JSON parser error", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("Gateway Timeout", { status: 504 })));
  const error = await send("auth/status?transport-test=1").catch((reason: unknown) => reason);
  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ status: 504, detail: "server_temporarily_unavailable" });
  expect((error as Error).message).toContain("Tu configuración se conserva");
  expect((error as Error).message).not.toMatch(/Unexpected token|Gateway Timeout/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("rejects malformed successful responses and preserves classified API errors", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce(new Response("<html>proxy</html>", { status: 200 }))
    .mockResolvedValueOnce(Response.json({ detail: "permission_denied" }, { status: 403 })));
  await expect(send("auth/status?transport-test=2")).rejects.toMatchObject({ status: 502, detail: "invalid_server_response" });
  await expect(send("auth/status?transport-test=3")).rejects.toMatchObject({ status: 403, detail: "permission_denied" });
});
