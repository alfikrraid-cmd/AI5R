import { describe, expect, it } from "vitest";
import colors from "./colors";

// MWO-LTSA-LIGHT-THEME-CONTRAST-FIX -- every token except `purple` is now
// `var(--ltsa-<token>, <original dark hex>)`, not a bare hex, so the
// design system stays theme-aware inside .ltsa-shell (ltsaTokens.css)
// while falling back to the exact original dark value everywhere else
// (the "od" module's console, per ltsaTokens.css's own header comment).
const VAR_PATTERN = /^var\(--ltsa-[a-z-]+, (#[0-9A-Fa-f]{6})\)$/;

function fallbackHex(token) {
  const match = colors[token].match(VAR_PATTERN);
  return match ? match[1].toUpperCase() : null;
}

describe("theme/colors", () => {
  it("defines every semantic token required by the design system", () => {
    const varTokens = ["background", "panel", "border", "text", "textMuted", "success", "info", "warning", "danger"];

    varTokens.forEach((token) => {
      expect(colors[token]).toMatch(VAR_PATTERN);
    });

    // purple has no --ltsa-purple counterpart in ltsaTokens.css -- stays
    // a bare hex, never a fabricated var() reference to a token that
    // doesn't exist.
    expect(colors.purple).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });

  it("keeps background/panel's dark-theme FALLBACK consistent with the pre-existing dashboard theme (unchanged for every consumer outside .ltsa-shell)", () => {
    expect(fallbackHex("background")).toBe("#0B1020");
    expect(fallbackHex("panel")).toBe("#151C33");
  });

  it("maps each token to its real ltsaTokens.css custom property name", () => {
    expect(colors.background).toContain("--ltsa-bg,");
    expect(colors.panel).toContain("--ltsa-surface,");
    expect(colors.border).toContain("--ltsa-border,");
    expect(colors.text).toContain("--ltsa-text,");
    expect(colors.textMuted).toContain("--ltsa-text-muted,");
    expect(colors.success).toContain("--ltsa-success,");
    expect(colors.info).toContain("--ltsa-info,");
    expect(colors.warning).toContain("--ltsa-warning,");
    expect(colors.danger).toContain("--ltsa-danger,");
  });
});
