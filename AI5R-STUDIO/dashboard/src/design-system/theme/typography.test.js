import { describe, expect, it } from "vitest";
import typography from "./typography";

describe("theme/typography", () => {
  it("keeps the pre-existing dashboard font family", () => {
    expect(typography.fontFamily).toBe("Arial, sans-serif");
  });

  it("defines a size and weight scale", () => {
    expect(typography.size).toEqual({ sm: 12, md: 14, lg: 18, xl: 24 });
    expect(typography.weight).toEqual({ regular: 400, bold: 700 });
  });
});
