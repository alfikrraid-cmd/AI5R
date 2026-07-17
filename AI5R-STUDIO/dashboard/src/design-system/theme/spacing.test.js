import { describe, expect, it } from "vitest";
import spacing from "./spacing";

describe("theme/spacing", () => {
  it("defines an ascending xs..xl px scale", () => {
    expect(spacing).toEqual({ xs: 4, sm: 8, md: 16, lg: 24, xl: 32 });
  });
});
