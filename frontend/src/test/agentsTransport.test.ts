import { expect, it, vi } from "vitest";
import { api } from "../modules/agents/api";

it("translates a fetch transport failure while retaining HTTP conflict and validation guidance", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ code: "agents_revision_conflict" }), {
        status: 409,
      }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({ code: "invalid_request", fields: ["name"] }),
        { status: 422 },
      ),
    );
  await expect(api()).rejects.toThrow(
    "No se pudo conectar con el servidor. Revise la conexión y vuelva a intentarlo.",
  );
  await expect(api()).rejects.toThrow(
    "El registro cambió. Actualice antes de guardar.",
  );
  await expect(api()).rejects.toThrow("Revise estos campos: Nombre.");
});

it("identifies rejected academic fields without displaying submitted values", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify({
      code: "invalid_request",
      fields: ["commercial.aliases", "commercial.source_note", "commercial.financial_plans"],
      input: "private-do-not-display",
    }), { status: 422 }),
  );
  await expect(api("/programs/13", "PUT", {})).rejects.toThrow(
    "Revise estos campos: Otros nombres o alias, Nota de procedencia, Planes de financiación.",
  );
});
