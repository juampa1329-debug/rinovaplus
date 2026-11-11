import { useLayoutEffect, useRef } from "react";
import { animateChart, stopChartMotion } from "./chartMotion";

export function usePanelEntrance(key: string) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    animateChart(
      node,
      [
        { opacity: 0.45, transform: "translateY(4px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      "panel",
    );
    return () => stopChartMotion(node);
  }, [key]);
  return ref;
}
