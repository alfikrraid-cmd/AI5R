import { describe, expect, it } from "vitest";
import colors from "./colors";

describe("theme/colors", () => {
  it("defines every semantic token required by the design system", () => {
    const requiredTokens = [
      "background",
      "panel",
      "border",
      "text",
      "textMuted",
      "success",
      "info",
      "warning",
      "danger",
      "purple",
    ];

    requiredTokens.forEach((token) => {
      expect(colors[token]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });

  it("keeps background/panel consistent with the pre-existing dashboard theme", () => {
    expect(colors.background.toUpperCase()).toBe("#0B1020");
    expect(colors.panel.toUpperCase()).toBe("#151C33");
  });
});
