import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Sidebar from "./Sidebar";

const ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "agents", label: "Agents" },
];

describe("Sidebar", () => {
  it("renders every item's label", () => {
    render(<Sidebar items={ITEMS} activeKey="overview" onSelect={() => {}} />);

    expect(screen.getByText("Overview")).toBeTruthy();
    expect(screen.getByText("Agents")).toBeTruthy();
  });

  it("marks the active item", () => {
    render(<Sidebar items={ITEMS} activeKey="agents" onSelect={() => {}} />);

    expect(screen.getByText("Agents").getAttribute("aria-current")).toBe("true");
    expect(screen.getByText("Overview").getAttribute("aria-current")).toBeNull();
  });

  it("calls onSelect with the clicked item's key", () => {
    const onSelect = vi.fn();
    render(<Sidebar items={ITEMS} activeKey="overview" onSelect={onSelect} />);

    fireEvent.click(screen.getByText("Agents"));

    expect(onSelect).toHaveBeenCalledWith("agents");
  });
});
