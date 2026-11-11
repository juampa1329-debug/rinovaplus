import { describe, expect, it } from "vitest";
import {
  appendLocalMessage,
  emptyApplication,
  emptyClient,
  filterClients,
  programs,
  schedules,
  seedClients,
  seedThreads,
  validateApplication,
  validateClient,
} from "./legacyData";

describe("temporary demo contracts", () => {
  it("creates fresh fixtures for every reset", () => {
    const first = seedClients();
    first[0].name = "Changed";
    expect(seedClients()[0].name).toBe("Persona Demo A");
    const threads = seedThreads();
    threads[0].messages.pop();
    expect(seedThreads()[0].messages).toHaveLength(3);
  });
  it("searches name, identifiers, city, programs and tags without case sensitivity", () => {
    for (const query of [
      "persona demo a",
      "DEMO-001",
      "Ciudad ficticia",
      "auxiliar",
      "asesoría",
    ]) {
      expect(
        filterClients(seedClients(), query).some(
          (client) => client.id === "demo-1",
        ),
      ).toBe(true);
    }
    expect(filterClients(seedClients(), "unknown")).toEqual([]);
    expect(filterClients(seedClients(), "", "Nuevo")).toHaveLength(1);
  });
  it("requires name or fictitious identifier", () => {
    expect(validateClient(emptyClient())).toBeTruthy();
    expect(validateClient({ ...emptyClient(), phone: "DEMO-009" })).toBeNull();
    expect(validateClient({ ...emptyClient(), name: "  " })).toBeTruthy();
  });
  it("blocks composer while AI mode is selected and rejects empty or excessive text", () => {
    const thread = seedThreads()[0];
    expect(appendLocalMessage(thread, "Local text")).toBe(thread);
    const human = { ...thread, mode: "human" as const };
    expect(appendLocalMessage(human, " ")).toBe(human);
    expect(appendLocalMessage(human, "x".repeat(4001))).toBe(human);
    const result = appendLocalMessage(human, "  Local text  ");
    expect(result.messages.at(-1)?.body).toBe("Local text");
    expect(human.messages).toHaveLength(3);
  });
  it("validates application fields and allowed fixture selections", () => {
    expect(Object.keys(validateApplication(emptyApplication()))).toEqual([
      "name",
      "email",
      "program",
      "schedule",
      "consent",
    ]);
    expect(
      validateApplication({
        ...emptyApplication(),
        name: "Demo",
        email: "demo@example.invalid",
        program: programs[0],
        schedule: schedules[0],
        consent: true,
      }),
    ).toMatchObject({
      program: expect.any(String),
      schedule: expect.any(String),
    });
    expect(
      validateApplication({
        ...emptyApplication(),
        program: "External",
        schedule: "External",
      }),
    ).toHaveProperty("program");
    expect(
      validateApplication({ ...emptyApplication(), email: "not-an-email" }),
    ).toHaveProperty("email");
  });
});
