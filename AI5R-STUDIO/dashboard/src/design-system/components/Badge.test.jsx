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

    expect(screen.getByTestId("badge").style.backgroundColor).toBe(hexToRgb(colors.success));
  });

  it("defaults to the purple variant", () => {
    render(<Badge>Default</Badge>);

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
