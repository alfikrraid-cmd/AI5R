import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LTSASidebar from "./LTSASidebar";

const GROUPS = [
  {
    heading: null,
    items: [
      { key: "dashboard", label: "Dashboard" },
      { key: "pump", label: "Pump" },
    ],
  },
  {
    heading: "More",
    items: [{ key: "drawing", label: "Drawing" }],
  },
];

describe("LTSASidebar", () => {
  it("renders every item across every group as a tab", () => {
    render(<LTSASidebar groups={GROUPS} activeKey="dashboard" onChange={() => {}} />);

    expect(screen.getByRole("tab", { name: "Dashboard" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Pump" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Drawing" })).toBeTruthy();
  });

  it("marks only the active key as selected", () => {
    render(<LTSASidebar groups={GROUPS} activeKey="pump" onChange={() => {}} />);

    expect(screen.getByRole("tab", { name: "Pump" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tab", { name: "Dashboard" }).getAttribute("aria-selected")).toBe("false");
  });

  it("renders a group heading when provided", () => {
    render(<LTSASidebar groups={GROUPS} activeKey="dashboard" onChange={() => {}} />);

    expect(screen.getByText("More")).toBeTruthy();
  });

  it("calls onChange with the clicked item's key", () => {
    const onChange = vi.fn();
    render(<LTSASidebar groups={GROUPS} activeKey="dashboard" onChange={onChange} />);

    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));

    expect(onChange).toHaveBeenCalledWith("pump");
  });
});
