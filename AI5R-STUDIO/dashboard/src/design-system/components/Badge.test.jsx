import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Badge from "./Badge";
import colors from "../theme/colors";

describe("Badge", () => {
  it("renders its label", () => {
    render(<Badge>New</Badge>);

    expect(screen.getByText("New")).toBeTruthy();
  });

  it("colors itself from theme.colors, keyed by variant", () => {
    render(<Badge variant="success">OK</Badge>);

    // MWO-LTSA-LIGHT-THEME-CONTRAST-FIX -- colors.success is now
    // `var(--ltsa-success, #22C55E)`, not a bare hex. jsdom stores an
    // inline `var(...)` style value verbatim (it does not resolve CSS
    // custom properties the way a real browser's cascade does), so the
    // old hexToRgb()-converted comparison no longer applies to any
    // token that changed -- direct string equality against the theme
    // token itself is the correct, real assertion: "did Badge apply
    // the token", not "did jsdom compute a color".
    expect(screen.getByTestId("badge").style.backgroundColor).toBe(colors.success);
  });

  it("defaults to the purple variant", () => {
    render(<Badge>Default</Badge>);

    // purple has no --ltsa-purple counterpart (see colors.js's own
    // comment) and stays a bare hex -- jsdom DOES normalize a bare hex
    // into rgb(...) form, so this one comparison still needs the
    // conversion.
    expect(screen.getByTestId("badge").style.backgroundColor).toBe(hexToRgb(colors.purple));
  });
});

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  const r = parseInt(value.substring(0, 2), 16);
  const g = parseInt(value.substring(2, 4), 16);
  const b = parseInt(value.substring(4, 6), 16);

  return `rgb(${r}, ${g}, ${b})`;
}
