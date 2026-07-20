import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PMFilterBar from "./PMFilterBar";

describe("PMFilterBar", () => {
  it("renders the search box with the current search value", () => {
    render(
      <PMFilterBar
        searchValue="lubrication"
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE", "OVERDUE"]}
      />
    );

    expect(screen.getByRole("searchbox").value).toBe("lubrication");
  });

  it("calls onSearchChange when typing in the search box", () => {
    const onSearchChange = vi.fn();
    render(
      <PMFilterBar
        searchValue=""
        onSearchChange={onSearchChange}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE"]}
      />
    );

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "pump" } });

    expect(onSearchChange).toHaveBeenCalledWith("pump");
  });

  it("renders an ALL option plus every status option in the filter select", () => {
    render(
      <PMFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE", "DUE_SOON", "OVERDUE"]}
      />
    );

    expect(screen.getByRole("option", { name: "All Statuses" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "ACTIVE" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "DUE_SOON" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "OVERDUE" })).toBeTruthy();
  });

  it("calls onStatusFilterChange when a status is selected", () => {
    const onStatusFilterChange = vi.fn();
    render(
      <PMFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={onStatusFilterChange}
        statusOptions={["ACTIVE", "OVERDUE"]}
      />
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "OVERDUE" } });

    expect(onStatusFilterChange).toHaveBeenCalledWith("OVERDUE");
  });
});
