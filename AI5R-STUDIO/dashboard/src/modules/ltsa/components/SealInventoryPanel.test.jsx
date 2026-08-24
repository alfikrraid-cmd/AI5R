import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SealInventoryPanel from "./SealInventoryPanel";

describe("SealInventoryPanel", () => {
  it("renders stock records and low stock counts", () => {
    render(<SealInventoryPanel overview={{ seal_stock_count: 5, low_stock_seal_count: 1 }} />);

    expect(screen.getByText("Stock Records")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
    expect(screen.getByText("Low Stock")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("shows N/A, never a fabricated 0, when low_stock_seal_count is null", () => {
    render(<SealInventoryPanel overview={{ seal_stock_count: 5, low_stock_seal_count: null }} />);

    expect(screen.getByText("N/A")).toBeTruthy();
  });
});
