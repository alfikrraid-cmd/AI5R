import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import WorkOrderFilterBar from "./WorkOrderFilterBar";

describe("WorkOrderFilterBar", () => {
  it("renders the search box with the current search value", () => {
    render(
      <WorkOrderFilterBar
        searchValue="seal"
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["OPEN", "COMPLETED"]}
      />
    );

    expect(screen.getByRole("searchbox").value).toBe("seal");
  });

  it("calls onSearchChange when typing in the search box", () => {
    const onSearchChange = vi.fn();
    render(
      <WorkOrderFilterBar
        searchValue=""
        onSearchChange={onSearchChange}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["OPEN"]}
      />
    );

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "pump" } });

    expect(onSearchChange).toHaveBeenCalledWith("pump");
  });

  it("renders an ALL option plus every status option in the filter select", () => {
    render(
      <WorkOrderFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["OPEN", "IN_PROGRESS", "COMPLETED"]}
      />
    );

    expect(screen.getByRole("option", { name: "All Statuses" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "OPEN" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "IN_PROGRESS" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "COMPLETED" })).toBeTruthy();
  });

  it("calls onStatusFilterChange when a status is selected", () => {
    const onStatusFilterChange = vi.fn();
    render(
      <WorkOrderFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={onStatusFilterChange}
        statusOptions={["OPEN", "COMPLETED"]}
      />
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "COMPLETED" } });

    expect(onStatusFilterChange).toHaveBeenCalledWith("COMPLETED");
  });
});
