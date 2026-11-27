import { expect, it } from "vitest";
import { emptyClient } from "../shared/demo";
import {
  contactConflicts,
  rebaseReviewedContact,
} from "../institution/contactEditing";

it("keeps concurrent fields and the academic identity when reviewing a stage edit", () => {
  const base = { ...emptyClient(), id: "fixture", stage: "Seguimiento" };
  const draft = { ...base, stage: "Cerrado sin matrícula" };
  const current = {
    ...base,
    city: "Santa Marta",
    program: "Actual",
    programId: 10,
  };
  expect(contactConflicts(base, draft, current)).toEqual([]);
  expect(rebaseReviewedContact(base, draft, current)).toEqual({
    ...current,
    stage: draft.stage,
  });
  expect(current.stage).toBe("Seguimiento");
});

it("compares the same edited field without silently rebasing or mutating it", () => {
  const base = { ...emptyClient(), stage: "Seguimiento" };
  const draft = { ...base, stage: "Cerrado sin matrícula" };
  const current = { ...base, stage: "Matriculado" };
  expect(contactConflicts(base, draft, current)).toEqual([
    {
      key: "stage",
      label: "Etapa",
      saved: "Matriculado",
      edited: "Cerrado sin matrícula",
    },
  ]);
  expect(current.stage).toBe("Matriculado");
});

it("merges reviewed custom changes per key while preserving other recent values", () => {
  const base = {
    ...emptyClient(),
    customValues: { one: "old", remove: "value" },
  };
  const draft = { ...base, customValues: { one: "mine" } };
  const current = {
    ...base,
    customValues: { one: "theirs", remove: "value", two: "fresh" },
  };
  expect(contactConflicts(base, draft, current)[0]).toMatchObject({
    key: "custom:one",
    saved: "theirs",
    edited: "mine",
  });
  expect(rebaseReviewedContact(base, draft, current).customValues).toEqual({
    one: "mine",
    two: "fresh",
  });
});
