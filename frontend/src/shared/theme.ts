import { useEffect, useState } from "react";

export type ThemePreference = "light" | "dark" | "system";
export const themeStorageKey = "crm-cbn-appearance";

export function readThemePreference(): ThemePreference {
  try {
    const value = localStorage.getItem(themeStorageKey);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

function systemIsDark() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function useTheme() {
  const [preference, setPreference] =
    useState<ThemePreference>(readThemePreference);
  const [systemDark, setSystemDark] = useState(systemIsDark);
  const theme =
    preference === "system" ? (systemDark ? "dark" : "light") : preference;

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const update = () => setSystemDark(media?.matches ?? false);
    media?.addEventListener("change", update);
    return () => media?.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#0f282c" : "#f5f7f2");
  }, [theme]);

  function chooseTheme(value: ThemePreference) {
    setPreference(value);
    try {
      localStorage.setItem(themeStorageKey, value);
    } catch {
      // Appearance still works for this tab when storage is unavailable.
    }
  }

  return { preference, theme, chooseTheme };
}
