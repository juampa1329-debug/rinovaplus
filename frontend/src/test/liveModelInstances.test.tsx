import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { LiveModelSelect } from "../institution/LiveModelSelect";

vi.mock("../institution/api", () => ({
  useTask: () => ({ busy: false, notices: null }),
}));
vi.mock("../institution/adsResource", () => ({
  useAdsResource: () => ({
    value: {
      items: [
        { id: "fixture/a:free", name: "A", input_usd_per_million: 3, output_usd_per_million: 15 },
        { id: "fixture/b:free", name: "B" },
      ],
    },
    error: "",
  }),
}));

it("keeps the labels and selections independent for two backups of the same provider", () => {
  const first = vi.fn(),
    second = vi.fn();
  render(
    <>
      <LiveModelSelect
        id="backup-first"
        provider="openrouter"
        category="text"
        value="fixture/a:free"
        label="Primer respaldo"
        onChange={first}
      />
      <LiveModelSelect
        id="backup-second"
        provider="openrouter"
        category="text"
        value=""
        label="Segundo respaldo"
        onChange={second}
      />
    </>,
  );
  expect(screen.getByLabelText("Primer respaldo")).not.toBe(
    screen.getByLabelText("Segundo respaldo"),
  );
  fireEvent.change(screen.getByLabelText("Segundo respaldo"), {
    target: { value: "fixture/b:free" },
  });
  expect(second).toHaveBeenCalledWith("fixture/b:free");
  expect(first).not.toHaveBeenCalled();
});

it("returns the selected catalog price atomically with the model", () => {
  const selected = vi.fn(), changed = vi.fn();
  render(<LiveModelSelect id="primary" label="Principal" provider="openrouter" category="text" value="" onChange={changed} onSelect={selected} />);
  fireEvent.change(screen.getByLabelText("Principal"), {target:{value:"fixture/a:free"}});
  expect(selected).toHaveBeenCalledWith({id:"fixture/a:free",name:"A",input_usd_per_million:3,output_usd_per_million:15});
  expect(changed).not.toHaveBeenCalled();
});
