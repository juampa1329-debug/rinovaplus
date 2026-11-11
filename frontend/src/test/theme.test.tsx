import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  readThemePreference,
  themeStorageKey,
  useTheme,
} from "../shared/theme";

function Appearance() {
  const { theme, preference, chooseTheme } = useTheme();
  return (
    <>
      <output aria-label="Resolved theme">
        {theme}/{preference}
      </output>
      <button onClick={() => chooseTheme("dark")}>Dark</button>
      <button onClick={() => chooseTheme("system")}>System</button>
    </>
  );
}

let change: (() => void) | undefined;
let dark = false;
const removeListener = vi.fn();
beforeEach(() => {
  localStorage.clear();
  dark = false;
  change = undefined;
  removeListener.mockClear();
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      get matches() {
        return dark;
      },
      addEventListener: (_event: string, callback: () => void) => {
        change = callback;
      },
      removeEventListener: removeListener,
    })),
  );
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("appearance preference", () => {
  it("uses system colors when the saved value is missing or invalid", () => {
    localStorage.setItem(themeStorageKey, "invalid");
    expect(readThemePreference()).toBe("system");
    dark = true;
    render(<Appearance />);
    expect(screen.getByLabelText("Resolved theme")).toHaveTextContent(
      "dark/system",
    );
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });
  it("persists only appearance and restores it on remount", async () => {
    const user = userEvent.setup();
    const first = render(<Appearance />);
    await user.click(screen.getByRole("button", { name: "Dark" }));
    expect(localStorage.length).toBe(1);
    expect(localStorage.getItem(themeStorageKey)).toBe("dark");
    first.unmount();
    render(<Appearance />);
    expect(screen.getByLabelText("Resolved theme")).toHaveTextContent(
      "dark/dark",
    );
  });
  it("follows OS changes only while system is selected and cleans its listener", async () => {
    const user = userEvent.setup();
    const view = render(<Appearance />);
    act(() => {
      dark = true;
      change?.();
    });
    expect(screen.getByLabelText("Resolved theme")).toHaveTextContent(
      "dark/system",
    );
    await user.click(screen.getByRole("button", { name: "Dark" }));
    act(() => {
      dark = false;
      change?.();
    });
    expect(screen.getByLabelText("Resolved theme")).toHaveTextContent(
      "dark/dark",
    );
    await user.click(screen.getByRole("button", { name: "System" }));
    expect(screen.getByLabelText("Resolved theme")).toHaveTextContent(
      "light/system",
    );
    view.unmount();
    expect(removeListener).toHaveBeenCalled();
  });
  it("keeps the control usable when storage is denied", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("Denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Denied");
    });
    const user = userEvent.setup();
    render(<Appearance />);
    await user.click(screen.getByRole("button", { name: "Dark" }));
    expect(screen.getByLabelText("Resolved theme")).toHaveTextContent(
      "dark/dark",
    );
  });
});
