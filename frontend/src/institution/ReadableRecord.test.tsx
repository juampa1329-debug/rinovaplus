import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { ReadableRecord } from "./ReadableRecord";

it("shows imported source notes as readable fields without the JSON envelope", () => {
  render(
    <ReadableRecord
      text={
        "Preinscripción registrada.\n" +
        JSON.stringify({
          origen: "Noviembre.xls",
          sha256: "technical-hash",
          hoja: "Sheet1",
          fila: 10,
          datos_exportados: {
            Aspirante: "Ana",
            "Programa de Interes": "Cocina",
            Estado: "Interesado",
          },
        })
      }
    />,
  );
  expect(screen.getByText("Preinscripción registrada.")).toBeInTheDocument();
  expect(screen.getByText("Ana")).toBeInTheDocument();
  expect(screen.getByText("Programa de Interes")).toBeInTheDocument();
  expect(screen.getByText("Noviembre.xls")).toBeInTheDocument();
  expect(screen.queryByText("technical-hash")).toBeNull();
  expect(document.querySelector("pre")).toBeNull();
});
it("keeps normal campaign prose and malformed JSON intact without injecting markup", () => {
  const text = "Hola Ana. {Esta es tu información}\n<script>texto</script>";
  render(<ReadableRecord text={text} />);
  expect(document.querySelector(".readable-record-text")?.textContent).toBe(
    text,
  );
  expect(document.querySelector("script")).toBeNull();
});
