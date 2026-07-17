import { describe, expect, it } from "vitest";
import * as DesignSystem from "./index";

describe("design-system/index", () => {
  it("exports every design system component", () => {
    const expected = [
      "Card",
      "Panel",
      "MetricCard",
      "Button",
      "StatusBadge",
      "ProgressBar",
      "Timeline",
      "Table",
      "SearchBox",
      "Badge",
      "EmptyState",
      "Modal",
      "PageHeader",
      "Sidebar",
      "Tabs",
      "Topbar",
    ];

    expected.forEach((name) => {
      expect(DesignSystem[name]).toBeTypeOf("function");
    });

    expect(Object.keys(DesignSystem).length).toBe(expected.length);
  });
});
