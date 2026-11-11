export const chartTiming = {
  enter: 240,
  update: 240,
  exit: 180,
  panel: 180,
} as const;
const effects = new Map<Element, Animation>();
let keyboard = false;
export const chartMotionAllowed = () =>
  !keyboard &&
  !document.hidden &&
  !(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);

export function stopChartMotion(element: Element) {
  effects.get(element)?.cancel();
  effects.delete(element);
}

export function animateChart(
  element: HTMLElement | SVGElement,
  frames: Keyframe[],
  kind: keyof typeof chartTiming,
  finish?: () => void,
) {
  stopChartMotion(element);
  if (!chartMotionAllowed() || !element.animate) {
    finish?.();
    return;
  }
  const tokens = getComputedStyle(element);
  const animation = element.animate(frames, {
    duration: chartTiming[kind],
    easing:
      tokens
        .getPropertyValue(kind === "update" ? "--ease-in-out" : "--ease-out")
        .trim() || "cubic-bezier(0.23, 1, 0.32, 1)",
  });
  effects.set(element, animation);
  void animation.finished.then(
    () => {
      if (effects.get(element) !== animation) return;
      effects.delete(element);
      finish?.();
    },
    () => {},
  );
}

export function observeChartMotion(onInstant: () => void) {
  const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  const stop = () => {
    for (const element of effects.keys()) stopChartMotion(element);
    onInstant();
  };
  const key = () => {
    keyboard = true;
    document.documentElement.dataset.input = "keyboard";
    stop();
  };
  const pointer = () => {
    keyboard = false;
    document.documentElement.dataset.input = "pointer";
  };
  const reduce = () => {
    if (media?.matches) stop();
  };
  const visibility = () => {
    if (document.hidden) stop();
  };
  document.addEventListener("keydown", key, true);
  document.addEventListener("pointerdown", pointer, true);
  document.addEventListener("visibilitychange", visibility);
  media?.addEventListener("change", reduce);
  return () => {
    document.removeEventListener("keydown", key, true);
    document.removeEventListener("pointerdown", pointer, true);
    document.removeEventListener("visibilitychange", visibility);
    media?.removeEventListener("change", reduce);
    stop();
  };
}
