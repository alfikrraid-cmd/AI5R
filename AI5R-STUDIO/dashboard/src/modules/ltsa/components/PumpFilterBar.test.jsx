import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PumpFilterBar from "./PumpFilterBar";

describe("PumpFilterBar", () => {
  it("renders the search box with the current search value", () => {
    render(
      <PumpFilterBar
        searchValue="boiler"
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE", "STANDBY"]}
      />
    );

    expect(screen.getByRole("searchbox").value).toBe("boiler");
  });

  it("calls onSearchChange when typing in the search box", () => {
    const onSearchChange = vi.fn();
    render(
      <PumpFilterBar
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
      <PumpFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE", "STANDBY", "FAULT"]}
      />
    );

    expect(screen.getByRole("option", { name: "All Statuses" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "ACTIVE" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "STANDBY" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "FAULT" })).toBeTruthy();
  });

  it("calls onStatusFilterChange when a status is selected", () => {
    const onStatusFilterChange = vi.fn();
    render(
      <PumpFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={onStatusFilterChange}
        statusOptions={["ACTIVE", "FAULT"]}
      />
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(onStatusFilterChange).toHaveBeenCalledWith("FAULT");
  });

  it("labels the status filter for assistive technology", () => {
    render(
      <PumpFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE"]}
      />
    );

    expect(screen.getByRole("combobox", { name: "Filter by status" })).toBeTruthy();
  });
});
