import { useLayoutEffect, useRef, useState } from "react";
import type { RefObject, PointerEvent, KeyboardEvent } from "react";

type Side = "list" | "context";
type Widths = Record<Side, number>;

const storageKey = "crm-cbn-inbox-panel-widths-v1";

function readWidths(): Widths {
  try {
    const value: unknown = JSON.parse(
      localStorage.getItem(storageKey) ?? "null",
    );
    if (
      value &&
      typeof value === "object" &&
      "list" in value &&
      "context" in value
    ) {
      const { list, context } = value;
      if (
        typeof list === "number" &&
        Number.isFinite(list) &&
        list >= 200 &&
        list <= 360 &&
        typeof context === "number" &&
        Number.isFinite(context) &&
        context >= 260 &&
        context <= 420
      )
        return { list: Math.round(list), context: Math.round(context) };
    }
  } catch {
    // Unavailable or invalid browser storage falls back to the default layout.
  }
  return { list: 220, context: 288 };
}

function saveWidths(value: Widths) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(value));
  } catch {
    // Resizing still works in this session when browser storage is unavailable.
  }
}

function fitWidths(
  preferred: Widths,
  total: number,
  contextVisible: boolean,
): Widths {
  const next = { ...preferred };
  const budget = total - 320 - (contextVisible ? 24 : 12);
  if (contextVisible)
    next.context = Math.max(260, Math.min(next.context, budget - 200));
  next.list = Math.max(
    200,
    Math.min(next.list, budget - (contextVisible ? next.context : 0)),
  );
  return next;
}

export function InboxPanelResize({
  container,
  contextVisible,
}: {
  container: RefObject<HTMLDivElement | null>;
  contextVisible: boolean;
}) {
  const [values, setValues] = useState(readWidths);
  const widths = useRef<Widths>(values);
  const preferred = useRef<Widths>(values);
  const [available, setAvailable] = useState(0);
  const drag = useRef<{ side: Side; x: number; width: number } | null>(null);

  function limits(side: Side, total: number, current: Widths) {
    const other =
      side === "list" ? (contextVisible ? current.context : 0) : current.list;
    const minimum = side === "list" ? 200 : 260;
    const maximum = Math.min(
      side === "list" ? 360 : 420,
      total - other - 320 - (contextVisible ? 24 : 12),
    );
    return { minimum, maximum: Math.max(minimum, maximum) };
  }

  function resize(side: Side, requested: number) {
    const total = container.current?.clientWidth ?? 0;
    const { minimum, maximum } = limits(side, total, widths.current);
    const next = {
      ...widths.current,
      [side]: Math.round(Math.max(minimum, Math.min(maximum, requested))),
    };
    widths.current = next;
    preferred.current = { ...preferred.current, [side]: next[side] };
    saveWidths(preferred.current);
    setValues(next);
  }

  useLayoutEffect(() => {
    const grid = container.current;
    if (!grid) return;
    function fit() {
      if (!grid || grid.clientWidth === 0) return;
      const total = grid.clientWidth;
      setAvailable(total);
      if (!window.matchMedia("(min-width: 1101px)").matches) return;
      const next = fitWidths(preferred.current, total, contextVisible);
      widths.current = next;
      setValues((previous) =>
        previous.list === next.list && previous.context === next.context
          ? previous
          : next,
      );
    }
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(grid);
    return () => observer.disconnect();
  }, [container, contextVisible]);

  useLayoutEffect(() => {
    container.current?.style.setProperty(
      "--inbox-list-width",
      `${values.list}px`,
    );
    container.current?.style.setProperty(
      "--inbox-context-width",
      `${values.context}px`,
    );
  }, [container, values]);

  function start(event: PointerEvent<HTMLDivElement>, side: Side) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.focus();
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { side, x: event.clientX, width: widths.current[side] };
  }

  function move(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    const { side, x, width } = drag.current;
    resize(side, width + (event.clientX - x) * (side === "list" ? 1 : -1));
  }

  function key(event: KeyboardEvent<HTMLDivElement>, side: Side) {
    const { minimum, maximum } = limits(side, available, widths.current);
    const direction = side === "list" ? 1 : -1;
    const step = event.shiftKey ? 48 : 16;
    const requested =
      event.key === "Home"
        ? minimum
        : event.key === "End"
          ? maximum
          : event.key === "ArrowLeft"
            ? widths.current[side] - step * direction
            : event.key === "ArrowRight"
              ? widths.current[side] + step * direction
              : null;
    if (requested === null) return;
    event.preventDefault();
    resize(side, requested);
  }

  return (
    <>
      {(["list", ...(contextVisible ? ["context"] : [])] as Side[]).map(
        (side) => {
          const range = limits(side, available, values);
          const label =
            side === "list" ? "Ancho de la bandeja" : "Ancho de la ficha CRM";
          return (
            <div
              key={side}
              className={`inbox-resize-handle resize-${side}`}
              role="separator"
              tabIndex={0}
              aria-label={label}
              aria-orientation="vertical"
              aria-valuemin={range.minimum}
              aria-valuemax={range.maximum}
              aria-valuenow={values[side]}
              aria-valuetext={`${values[side]} píxeles`}
              title={`${label}. Arrastre o use las flechas; Inicio/Fin para los límites.`}
              onPointerDown={(event) => start(event, side)}
              onPointerMove={move}
              onPointerUp={() => {
                drag.current = null;
              }}
              onPointerCancel={() => {
                drag.current = null;
              }}
              onLostPointerCapture={() => {
                drag.current = null;
              }}
              onKeyDown={(event) => key(event, side)}
            />
          );
        },
      )}
    </>
  );
}
