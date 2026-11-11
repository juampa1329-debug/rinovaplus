import { describe, expect, it } from "vitest";
import { filterReviews, transitionReview } from "../shared/review";
import { seedReviews } from "./legacyFixtures";

describe("temporary human review", () => {
  it("returns independent synthetic fixtures and histories", () => {
    const records = seedReviews();
    records[0].name = "Changed";
    expect(seedReviews()[0].name).toBe("Aspirante Demo A");
    expect(records).toHaveLength(3);
  });
  it("filters by case-insensitive text, state and provisional program", () => {
    expect(
      filterReviews(seedReviews(), " demo a ", "pending", "all"),
    ).toHaveLength(1);
    expect(filterReviews(seedReviews(), "", "observed", "all")).toHaveLength(1);
    expect(filterReviews(seedReviews(), "no match", "all", "all")).toHaveLength(
      0,
    );
    expect(
      filterReviews(seedReviews(), "", "all", seedReviews()[0].program),
    ).toHaveLength(1);
  });
  it("starts only a pending record and appends a real local timestamp", () => {
    const record = seedReviews()[0];
    const result = transitionReview(
      record,
      "start",
      "",
      new Date("2026-10-14T15:00:00Z"),
    );
    expect(result.record?.status).toBe("in_review");
    expect(result.record?.history.at(-1)?.at).toBe("2026-10-14T15:00:00.000Z");
    expect(record.status).toBe("pending");
  });
  it.each(["reviewed", "observed", "rejected"] as const)(
    "requires an active review before %s",
    (action) => {
      expect(
        transitionReview(seedReviews()[0], action, "Human reason").error,
      ).toBeTruthy();
    },
  );
  it.each(["reviewed", "observed", "rejected"] as const)(
    "records %s without creating approval or enrollment",
    (action) => {
      const active = transitionReview(seedReviews()[0], "start", "").record!;
      const result = transitionReview(
        active,
        action,
        "  Synthetic review reason  ",
      );
      expect(result.record?.status).toBe(action);
      expect(result.record?.history.at(-1)?.reason).toBe(
        "Synthetic review reason",
      );
      expect(result.record).not.toHaveProperty("approved");
      expect(result.record).not.toHaveProperty("enrollment");
    },
  );
  it("rejects whitespace, short and over-limit reasons without mutation", () => {
    const record = transitionReview(seedReviews()[0], "start", "").record!;
    for (const reason of ["   ", "four", "x".repeat(601)]) {
      expect(transitionReview(record, "observed", reason).error).toBeTruthy();
      expect(record.history).toHaveLength(2);
    }
  });
  it("reopens resolved cases with a reason and preserves every prior event", () => {
    for (const record of seedReviews().slice(1)) {
      const result = transitionReview(record, "reopen", "Correction in demo");
      expect(result.record?.status).toBe("pending");
      expect(result.record?.history.slice(0, -1)).toEqual(record.history);
      expect(
        transitionReview(result.record!, "reopen", "Cannot repeat").error,
      ).toBeTruthy();
    }
  });
  it("does not invent academic eligibility from incomplete data", () => {
    const record = seedReviews()[1];
    expect(record.email).toBe("");
    const pending = transitionReview(
      record,
      "reopen",
      "Review missing demo data",
    ).record!;
    const active = transitionReview(pending, "start", "").record!;
    expect(
      transitionReview(active, "observed", "Missing demo email").record?.status,
    ).toBe("observed");
  });
});
