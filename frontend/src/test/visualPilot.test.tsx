import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import { App } from "../App";
import { OverviewCharts } from "../features/Overview";
import { overviewData } from "../shared/overview";
import { seedClients, seedThreads } from "./legacyData";
import { seedCrmConfig } from "../shared/crm";
import { modules } from "../shared/navigation";
import { addTask, finishTask, updateOperation } from "../shared/workflow";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("V5 local pilot", () => {
  it("derives honest totals, configurable and unknown stages, states and pending tasks", () => {
    const clients = seedClients();
    const threads = seedThreads();
    const config = seedCrmConfig();
    config.stages.push({
      key: "later",
      label: "Más adelante",
      probability: 95,
    });
    clients[0].stage = "Etapa ajena";
    threads[0] = addTask(
      updateOperation(threads[0], "state", "En espera"),
      "Revisar local",
      "",
    );
    threads[1] = updateOperation(threads[1], "state", "Cerrada");
    const data = overviewData(clients, threads, config);
    expect(data.stages.reduce((sum, stage) => sum + stage.count, 0)).toBe(4);
    expect(data.stages.find((stage) => stage.key === "later")?.count).toBe(0);
    expect(data.stages.at(-1)).toMatchObject({
      label: "Sin correspondencia",
      count: 1,
    });
    expect(data.states.map((state) => state.count)).toEqual([2, 1, 1]);
    expect(data.tasks).toBe(1);
    threads[0] = finishTask(
      threads[0],
      threads[0].workflow!.tasks[0].id,
      "Completada",
    );
    expect(overviewData(clients, threads, config).tasks).toBe(0);
    expect(overviewData([], [], config)).toMatchObject({
      contacts: 0,
      conversations: 0,
      tasks: 0,
      open: 0,
    });
  });

  it("exposes compact navigation and counts without copying prototype controls", async () => {
    window.location.hash = "/overview";
    const user = userEvent.setup();
    render(<App />);
    const navigation = screen.getByRole("navigation", {
      name: "Navegación principal",
    });
    expect(screen.getByRole("region", { name: "Otros módulos" })).toBeVisible();
    expect(
      within(navigation).getByRole("link", { name: "Admisiones" }),
    ).toBeVisible();
    await user.click(
      within(navigation).getByRole("link", { name: "Conocimiento" }),
    );
    expect(window.location.hash).toBe("#/knowledge");
    expect(within(navigation).getAllByRole("link")).toHaveLength(
      modules.length,
    );
    await user.click(within(navigation).getByRole("link", { name: "Resumen" }));
    expect(screen.queryByText("Repetir entrada")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Estado de las conversaciones" }),
    ).toBeVisible();
  });

  it("keeps final values immediate and cancels chart exit on reentry, keyboard and reduction", async () => {
    const running: {
      cancel: ReturnType<typeof vi.fn>;
      resolve: () => void;
      options: KeyframeAnimationOptions;
    }[] = [];
    let reduced = false;
    const listeners = new Set<() => void>();
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        get matches() {
          return reduced;
        },
        addEventListener: (_: string, listener: () => void) =>
          listeners.add(listener),
        removeEventListener: (_: string, listener: () => void) =>
          listeners.delete(listener),
      })),
    );
    vi.stubGlobal("getComputedStyle", (element: Element) => ({
      clipPath: (element as HTMLElement).style.clipPath || "inset(0 100% 0 0)",
      opacity: (element as HTMLElement).style.opacity || "1",
      getPropertyValue: () => "cubic-bezier(0.23, 1, 0.32, 1)",
    }));
    const animate = vi.fn(
      (_frames: Keyframe[], options: KeyframeAnimationOptions) => {
        let resolve = () => {};
        const finished = new Promise<void>((done) => {
          resolve = done;
        });
        const animation = { cancel: vi.fn(), resolve, options, finished };
        running.push(animation);
        return animation;
      },
    );
    Object.defineProperty(HTMLElement.prototype, "animate", {
      configurable: true,
      value: animate,
    });
    const data = overviewData(seedClients(), seedThreads(), seedCrmConfig());
    const page = render(<OverviewCharts active={false} data={data} />);
    fireEvent.pointerDown(document);
    page.rerender(<OverviewCharts active data={data} />);
    expect(
      running.filter((item) => item.options.duration === 240),
    ).toHaveLength(5);
    expect(screen.getByText("4 contactos")).toBeVisible();
    const root = page.container.firstElementChild as HTMLElement;
    page.rerender(<OverviewCharts active={false} data={data} />);
    expect(root).toHaveAttribute("inert");
    expect(root).toHaveAttribute("aria-hidden", "true");
    expect(root.style.pointerEvents).toBe("none");
    const exit = running.at(-1)!;
    expect(exit.options.duration).toBe(180);
    page.rerender(<OverviewCharts active data={data} />);
    expect(exit.cancel).toHaveBeenCalled();
    await act(async () => exit.resolve());
    expect(root.hidden).toBe(false);
    fireEvent.keyDown(document, { key: "Tab" });
    const count = running.length;
    page.rerender(<OverviewCharts active={false} data={data} />);
    expect(root.hidden).toBe(true);
    expect(running).toHaveLength(count);
    fireEvent.pointerDown(document);
    reduced = true;
    act(() => listeners.forEach((listener) => listener()));
    page.rerender(<OverviewCharts active data={data} />);
    expect(running).toHaveLength(count);
    page.unmount();
    expect(listeners.size).toBe(0);
    reduced = false;
    const strict = render(
      <StrictMode>
        <OverviewCharts active data={data} />
      </StrictMode>,
    );
    expect(
      running.slice(-5).every((item) => item.options.duration === 240),
    ).toBe(true);
    const lastEffects = running.slice(-5);
    strict.unmount();
    expect(lastEffects.every((item) => item.cancel.mock.calls.length > 0)).toBe(
      true,
    );
    Reflect.deleteProperty(HTMLElement.prototype, "animate");
  });
});
