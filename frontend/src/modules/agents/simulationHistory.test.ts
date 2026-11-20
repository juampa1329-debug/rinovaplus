import { expect, it } from "vitest";
import { simulationHistory } from "./simulationHistory";

it("preserves ordered turns and multiline answers without inventing roles", () => {
  expect(
    simulationHistory(
      "Cliente: Soy Alex.\nAsesor: Hola.\nPodemos orientarte.\nCliente: Ahora prefiero Software.",
    ),
  ).toEqual([
    { role: "user", content: "Soy Alex." },
    { role: "assistant", content: "Hola.\nPodemos orientarte." },
    { role: "user", content: "Ahora prefiero Software." },
  ]);
  expect(simulationHistory(" \n")).toEqual([]);
});

it("rejects missing roles, empty turns and the backend limits before consuming", () => {
  expect(() => simulationHistory("Soy Alex")).toThrow(/Cliente/);
  expect(() => simulationHistory("Cliente: \nAsesor: Hola")).toThrow(/1600/);
  expect(() => simulationHistory("Cliente: " + "a".repeat(1601))).toThrow(
    /1600/,
  );
  expect(() =>
    simulationHistory(Array(13).fill("Cliente: Hola").join("\n")),
  ).toThrow(/12/);
});
