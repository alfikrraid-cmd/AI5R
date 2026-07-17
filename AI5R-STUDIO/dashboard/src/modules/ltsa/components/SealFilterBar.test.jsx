import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SealFilterBar from "./SealFilterBar";

describe("SealFilterBar", () => {
  it("renders the search box with the current search value", () => {
    render(
      <SealFilterBar
        searchValue="crane"
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE", "STANDBY"]}
      />
    );

    expect(screen.getByRole("searchbox").value).toBe("crane");
  });

  it("calls onSearchChange when typing in the search box", () => {
    const onSearchChange = vi.fn();
    render(
      <SealFilterBar
        searchValue=""
        onSearchChange={onSearchChange}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE"]}
      />
    );

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "seal" } });

    expect(onSearchChange).toHaveBeenCalledWith("seal");
  });

  it("renders an ALL option plus every status option", () => {
    render(
      <SealFilterBar
        searchValue=""
        onSearchChange={() => {}}
        statusFilter="ALL"
        onStatusFilterChange={() => {}}
        statusOptions={["ACTIVE", "FAULT"]}
      />
    );

    expect(screen.getByRole("option", { name: "All Statuses" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "ACTIVE" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "FAULT" })).toBeTruthy();
  });

  it("calls onStatusFilterChange when a status is selected", () => {
    const onStatusFilterChange = vi.fn();
    render(
      <SealFilterBar
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
});
