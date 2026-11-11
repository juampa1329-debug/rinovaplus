import { fixtureCrmConfig as seedCrmConfig } from "./legacyFixtures";
import { describe, expect, it } from "vitest";
import { seedClients, seedThreads, appendLocalMessage } from "./legacyData";
import {
  addStage,
  addTag,
  addCustomField,
  deactivateField,
  validateCrmClient,
  filterByTag,
  tagCounts,
} from "../shared/crm";
import { analyzeConversation } from "../shared/conversationAnalysis";
import { appendLocalReply, filterComments } from "../shared/comments";
import { seedComments } from "./legacyFixtures";

describe("shared local CRM configuration", () => {
  it("rejects duplicate normalized stage keys and invalid probabilities", () => {
    const config = seedCrmConfig();
    expect(
      addStage(config, { key: " NUEVO ", label: "Duplicada", probability: 5 })
        .error,
    ).toBeTruthy();
    expect(
      addStage(config, {
        key: "follow_up",
        label: "Seguimiento",
        probability: 101,
      }).error,
    ).toBeTruthy();
    const result = addStage(config, {
      key: "follow_up",
      label: "Seguimiento",
      probability: 35,
    });
    expect(result.config.stages.at(-1)?.key).toBe("follow_up");
    expect(config.stages).toHaveLength(4);
  });
  it("keeps legacy tags and counts/filter them consistently", () => {
    const clients = seedClients();
    const config = seedCrmConfig();
    expect(addTag(config, "  solicita asesoría ").error).toBeTruthy();
    expect(filterByTag(clients, "Solicita asesoría")).toHaveLength(1);
    expect(tagCounts(clients, config.tags)["Solicita asesoría"]).toBe(1);
  });
  it("requires list options and rejects duplicate case-normalized field keys", () => {
    const config = seedCrmConfig();
    expect(
      addCustomField(config, {
        key: " Correo ",
        label: "Otro",
        type: "Text",
        options: [],
        active: true,
      }).error,
    ).toBeTruthy();
    expect(
      addCustomField(config, {
        key: "test",
        label: "Test",
        type: "List",
        options: [],
        active: true,
      }).error,
    ).toBeTruthy();
    expect(
      addCustomField(config, {
        key: "test",
        label: "Test",
        type: "List",
        options: ["A", "a"],
        active: true,
      }).error,
    ).toBeTruthy();
    expect(
      addCustomField(config, {
        key: "constructor",
        label: "Test",
        type: "Text",
        options: [],
        active: true,
      }).error,
    ).toBeTruthy();
  });
  it.each([
    ["Text", "texto", "x".repeat(501)],
    ["Number", "12.5", "NaN"],
    ["List", "A", "C"],
    ["Date", "2026-10-13", "2026-02-30"],
    ["Boolean", "false", "maybe"],
    ["Email", "demo@example.invalid", "bad"],
    ["Phone", "+57005000", "bad phone"],
    ["URL", "https://example.invalid", "javascript:alert(1)"],
  ] as const)(
    "validates %s without coercion and preserves inactive data",
    (type, valid, invalid) => {
      const config = addCustomField(seedCrmConfig(), {
        key: "test",
        label: "Test",
        type,
        options: ["A", "B"],
        active: true,
      }).config;
      const client = { ...seedClients()[0], customValues: { test: valid } };
      expect(validateCrmClient(client, config)).toEqual({});
      expect(
        validateCrmClient(
          { ...client, customValues: { test: invalid } },
          config,
        ),
      ).toHaveProperty("test");
      const inactive = deactivateField(config, "test");
      expect(
        validateCrmClient(
          { ...client, customValues: { test: invalid } },
          inactive,
        ),
      ).toEqual({});
      expect(client.customValues.test).toBe(valid);
    },
  );
});

describe("evidence-based demonstration, not model inference", () => {
  const analyze = (bodies: string[]) =>
    analyzeConversation({
      ...seedThreads()[0],
      wait: undefined,
      messages: bodies.map((body, i) => ({
        id: String(i),
        direction: "incoming" as const,
        body,
      })),
    });
  it("does not let old intent override a latest rejection", () => {
    expect(
      analyze(["Quiero inscribirme", "Ya no me interesa, no continuaré"])
        .temperature,
    ).toBe("Frío");
    expect(
      analyze(["Quiero inscribirme", "Ya no me interesa, no continuaré"]).risk,
    ).toBe("Alto");
  });
  it.each([
    "No quiero inscribirme",
    "No me interesa",
    "Nunca quiero matricularme",
    'El anuncio dice "quiero inscribirme"',
    "¿Qué significa ‘quiero inscribirme’?",
  ])("never heats negated or quoted intent: %s", (body) => {
    expect(analyze([body]).temperature).not.toBe("Caliente");
    expect(analyze([body]).temperature).not.toBe("Tibio");
  });
  it("handoff is not buying intent; outgoing only/no incoming is unknown", () => {
    const result = analyze(["Necesito hablar con un asesor"]);
    expect(result.humanRequested).toBe(true);
    expect(result.temperature).toBe("Sin evidencia");
    expect(analyzeConversation(seedThreads()[3]).risk).toBe("No evaluable");
    expect(
      analyzeConversation({ ...seedThreads()[0], messages: [] }).temperature,
    ).toBe("Sin evidencia");
    expect(analyze(["Me interesa la jornada"]).humanRequested).toBe(false);
    expect(analyze(["Ya tengo un asesor"]).humanRequested).toBe(false);
    expect(
      analyze(["No quiero hablar con un robot, me interesa la jornada"])
        .temperature,
    ).not.toBe("Frío");
  });
  it("waiting is synthetic, tied to the latest message, and not disinterest", () => {
    const thread = seedThreads()[0];
    expect(analyzeConversation(thread).waiting).toContain("sintética");
    expect(analyzeConversation(thread).risk).not.toBe("Alto");
    expect(
      analyzeConversation({
        ...thread,
        wait: { lastMessageId: "stale", minutes: 30 },
      }).waiting,
    ).toBe("Espera no evaluable");
    const sent = appendLocalMessage(
      { ...thread, mode: "human" },
      "Quiero inscribirme",
    );
    expect(sent.wait).toBeUndefined();
    expect(analyzeConversation(sent).temperature).toBe(
      analyzeConversation(thread).temperature,
    );
    expect(analyzeConversation(sent).waiting).toBe("Espera no evaluable");
  });
  it("has four intended unconnected channels", () => {
    expect(seedThreads().map((thread) => thread.channel)).toEqual([
      "WhatsApp",
      "Facebook",
      "Instagram",
      "TikTok",
    ]);
  });
});

describe("local social comments", () => {
  it("filters platform/status/search and excludes WhatsApp", () => {
    expect(seedComments().map((comment) => comment.platform)).toEqual([
      "Facebook",
      "Instagram",
      "TikTok",
    ]);
    expect(
      filterComments(seedComments(), "", "Instagram", "Pendiente"),
    ).toHaveLength(1);
    expect(filterComments(seedComments(), "missing", "Todas", "Todos")).toEqual(
      [],
    );
  });
  it("only appends bounded local replies and updates local status", () => {
    const comment = seedComments()[0];
    expect(appendLocalReply(comment, " ")).toBe(comment);
    expect(appendLocalReply(comment, "x".repeat(1501))).toBe(comment);
    const updated = appendLocalReply(comment, " Texto ficticio ");
    expect(updated.status).toBe("Respondido");
    expect(updated.replies.at(-1)?.body).toBe("Texto ficticio");
    expect(comment.replies).toHaveLength(0);
    expect(seedComments()[0].status).toBe("Pendiente");
  });
});
