import { expect, it, vi } from "vitest";

it("pins one source environment and never retargets cached selectors", async () => {
  vi.resetModules();
  const env = await import("./siieEnvironment");
  const test = {
    base_url: "https://siie.example.test/Test/",
    fingerprint: "a".repeat(64),
  };
  const prod = {
    base_url: "https://siie.example.test/Prod/",
    fingerprint: "b".repeat(64),
  };
  env.observeSiie("siie/connection", { environment: test });
  expect(env.siieHeaders("siie-registration/catalogs")).toEqual({
    "X-SIIE-Environment": test.fingerprint,
  });
  expect(env.siieHeaders("workspace/inbox")).toEqual({});
  expect(() => env.observeSiie("siie/periods", { environment: prod })).toThrow(
    /cambió de entorno/,
  );
  expect(env.siieEnvironment()).toEqual(test);
  expect(() =>
    env.observeSiie("siie-registration/preicfes/old", {
      environment: prod,
      environment_current: false,
    }),
  ).not.toThrow();
  expect(env.siieEnvironment()).toEqual(test);
});
