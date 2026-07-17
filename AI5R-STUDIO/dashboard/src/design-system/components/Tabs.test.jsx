import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Tabs from "./Tabs";

const ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "logs", label: "Logs" },
];

describe("Tabs", () => {
  it("renders every tab's label", () => {
    render(<Tabs items={ITEMS} activeKey="overview" onChange={() => {}} />);

    expect(screen.getByRole("tab", { name: "Overview" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Logs" })).toBeTruthy();
  });

  it("marks the active tab as selected", () => {
    render(<Tabs items={ITEMS} activeKey="logs" onChange={() => {}} />);

    expect(screen.getByRole("tab", { name: "Logs" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tab", { name: "Overview" }).getAttribute("aria-selected")).toBe(
      "false"
    );
  });

  it("calls onChange with the clicked tab's key", () => {
    const onChange = vi.fn();
    render(<Tabs items={ITEMS} activeKey="overview" onChange={onChange} />);

    fireEvent.click(screen.getByRole("tab", { name: "Logs" }));

    expect(onChange).toHaveBeenCalledWith("logs");
  });
});
