import { describe, expect, it } from "vitest";
import {
  operationBinding,
  setRecoveryCheck,
  transitionOperation,
} from "../shared/operations";
import { seedOperations } from "./legacyFixtures";

const reason = "Motivo de demostración";
const now = new Date("2026-10-14T18:00:00Z");

describe("isolated operations rehearsal", () => {
  it("returns independent scenarios without configured operational policy", () => {
    const records = seedOperations();
    expect(records).toHaveLength(4);
    records[1].checks[0].checked = true;
    expect(seedOperations()[1].checks[0].checked).toBe(false);
    expect(records.map((record) => record.status)).toEqual([
      "stable",
      "degraded",
      "degraded",
      "degraded",
    ]);
    expect(records.every((record) => record.history.length === 0)).toBe(true);
    expect(records[0]).not.toHaveProperty("sla");
    expect(records[0]).not.toHaveProperty("providerConnected");
  });
  it("pauses a bound scenario with a real local timestamp without mutating the input", () => {
    const record = seedOperations()[1];
    const result = transitionOperation(
      record,
      "pause",
      operationBinding(record),
      reason,
      now,
    );
    expect(result.record?.status).toBe("paused");
    expect(result.record?.history[0]).toMatchObject({
      at: now.toISOString(),
      reason,
    });
    expect(record.status).toBe("degraded");
    expect(record.history).toHaveLength(0);
  });
  it.each(["pause", "review", "resume"] as const)(
    "rejects %s with a stale or different binding",
    (action) => {
      const record = seedOperations()[1];
      expect(
        transitionOperation(
          record,
          action,
          operationBinding(seedOperations()[2]),
          reason,
        ).error,
      ).toBeTruthy();
      expect(
        transitionOperation(record, action, `${record.id}:99`, reason).error,
      ).toBeTruthy();
    },
  );
  it.each(["", "   ", "x".repeat(301)])(
    "rejects invalid reasons before mutation",
    (invalid) => {
      const record = seedOperations()[1];
      expect(
        transitionOperation(record, "pause", operationBinding(record), invalid)
          .error,
      ).toBeTruthy();
      expect(record.history).toHaveLength(0);
    },
  );
  it("rejects recovery checks outside pause, unknown checks and duplicate check changes", () => {
    const record = seedOperations()[1];
    expect(
      setRecoveryCheck(record, record.checks[0].id, true).error,
    ).toBeTruthy();
    const paused = transitionOperation(
      record,
      "pause",
      operationBinding(record),
      reason,
    ).record!;
    expect(setRecoveryCheck(paused, "unknown", true).error).toBeTruthy();
    expect(
      setRecoveryCheck(paused, paused.checks[0].id, false).error,
    ).toBeTruthy();
  });
  it("blocks resume before review and review with incomplete checks", () => {
    const record = seedOperations()[1];
    expect(
      transitionOperation(record, "resume", operationBinding(record), reason)
        .error,
    ).toBeTruthy();
    const paused = transitionOperation(
      record,
      "pause",
      operationBinding(record),
      reason,
    ).record!;
    expect(
      transitionOperation(paused, "review", operationBinding(paused), reason)
        .error,
    ).toBeTruthy();
    expect(
      transitionOperation(paused, "resume", operationBinding(paused), reason)
        .error,
    ).toBeTruthy();
  });
  it("invalidates confirmations after a reversible checklist change", () => {
    let record = seedOperations()[1];
    record = transitionOperation(
      record,
      "pause",
      operationBinding(record),
      reason,
    ).record!;
    const binding = operationBinding(record);
    record = setRecoveryCheck(record, record.checks[0].id, true, now).record!;
    expect(operationBinding(record)).not.toBe(binding);
    expect(
      transitionOperation(record, "review", binding, reason).error,
    ).toBeTruthy();
    record = setRecoveryCheck(record, record.checks[0].id, false, now).record!;
    expect(record.checks[0].checked).toBe(false);
    expect(record.history).toHaveLength(3);
  });
  it.each([0, 1, 2, 3])(
    "completes only scenario %s and keeps every local event",
    (index) => {
      const originals = seedOperations();
      let record = originals[index];
      record = transitionOperation(
        record,
        "pause",
        operationBinding(record),
        reason,
        now,
      ).record!;
      for (const check of record.checks)
        record = setRecoveryCheck(record, check.id, true, now).record!;
      record = transitionOperation(
        record,
        "review",
        operationBinding(record),
        reason,
        now,
      ).record!;
      expect(record.status).toBe("recovering");
      expect(record.incident).toBe(index === 0 ? "none" : "in_review");
      record = transitionOperation(
        record,
        "resume",
        operationBinding(record),
        reason,
        now,
      ).record!;
      expect(record.status).toBe("stable");
      expect(record.incident).toBe(index === 0 ? "none" : "closed");
      expect(record.history).toHaveLength(record.checks.length + 3);
      expect(
        transitionOperation(record, "resume", operationBinding(record), reason)
          .error,
      ).toBeTruthy();
      expect(originals.every((item) => item.history.length === 0)).toBe(true);
    },
  );
  it("clears a previous cycle checklist on a new pause, not the history", () => {
    let record = seedOperations()[1];
    record = transitionOperation(
      record,
      "pause",
      operationBinding(record),
      reason,
    ).record!;
    for (const check of record.checks)
      record = setRecoveryCheck(record, check.id, true).record!;
    record = transitionOperation(
      record,
      "review",
      operationBinding(record),
      reason,
    ).record!;
    record = transitionOperation(
      record,
      "resume",
      operationBinding(record),
      reason,
    ).record!;
    const count = record.history.length;
    record = transitionOperation(
      record,
      "pause",
      operationBinding(record),
      reason,
    ).record!;
    expect(record.checks.every((check) => !check.checked)).toBe(true);
    expect(record.history).toHaveLength(count + 1);
  });
  it("rejects an invalid local clock without partial mutation", () => {
    const record = seedOperations()[1];
    expect(
      transitionOperation(
        record,
        "pause",
        operationBinding(record),
        reason,
        new Date("invalid"),
      ).error,
    ).toBeTruthy();
    expect(record.history).toHaveLength(0);
  });
});
