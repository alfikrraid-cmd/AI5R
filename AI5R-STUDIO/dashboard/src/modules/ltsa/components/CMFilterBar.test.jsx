import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CMFilterBar from "./CMFilterBar";

describe("CMFilterBar", () => {
  it("renders the search box with the current search value", () => {
    render(
      <CMFilterBar
        searchValue="seal"
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["OPEN", "CLOSED"]}
      />
    );

    expect(screen.getByRole("searchbox").value).toBe("seal");
  });

  it("calls onSearchChange when typing in the search box", () => {
    const onSearchChange = vi.fn();
    render(
      <CMFilterBar
        searchValue=""
        onSearchChange={onSearchChange}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["OPEN"]}
      />
    );

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "bearing" } });

    expect(onSearchChange).toHaveBeenCalledWith("bearing");
  });

  it("renders an ALL option plus every status option in the filter select", () => {
    render(
      <CMFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]}
      />
    );

    expect(screen.getByRole("option", { name: "All Statuses" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Open" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "In Progress" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Resolved" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Closed" })).toBeTruthy();
  });

  it("calls onStatusFilterChange when a status is selected", () => {
    const onStatusFilterChange = vi.fn();
    render(
      <CMFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={onStatusFilterChange}
        statusOptions={["OPEN", "CLOSED"]}
      />
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "CLOSED" } });

    expect(onStatusFilterChange).toHaveBeenCalledWith("CLOSED");
  });
});
