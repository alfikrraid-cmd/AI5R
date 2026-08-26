import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MechanicalSealStock from "./MechanicalSealStock";
import { getMechanicalSealStock } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({ getMechanicalSealStock: vi.fn() }));

afterEach(() => vi.clearAllMocks());

const POOL = {
  stock_pool_id: "MSSP-1",
  seal_type: "T48MP",
  nominal_size: '1-1/4"',
  quantity_on_hand: 3,
  quantity_reserved: 0,
  quantity_available: 3,
  drawing_reference: "E12926",
  stock_location: "TAP DMI",
  verification_status: "CONFIRMED",
  compatibility_status: "CONFIRMED",
  applications: [{ equipment_tag: "300-P-1A" }, { equipment_tag: "300-P-1B" }],
};

function load(items = [POOL], total = items.length) {
  getMechanicalSealStock.mockResolvedValue({ items, total, total_quantity: 107, limit: 25, offset: 0 });
}

describe("Mechanical Seal Stock", () => {
  it("renders real stock rows and shared quantity once", async () => {
    load();
    render(<MechanicalSealStock />);
    expect(await screen.findByText("T48MP")).toBeTruthy();
    expect(screen.getByText("E12926")).toBeTruthy();
    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("107")).toBeTruthy();
  });

  it("renders an honest empty state", async () => {
    load([], 0);
    render(<MechanicalSealStock />);
    expect(await screen.findByText("No mechanical seal stock found")).toBeTruthy();
  });

  it("passes server search and verification filters", async () => {
    load();
    render(<MechanicalSealStock />);
    await screen.findByText("T48MP");
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "E12926" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "CONFIRMED" } });
    await waitFor(() => expect(getMechanicalSealStock).toHaveBeenLastCalledWith({ limit: 25, offset: 0, search: "E12926", verificationStatus: "CONFIRMED" }));
  });

  it("does not contain sample fallback data", async () => {
    const source = await import("fs");
    const text = source.readFileSync("src/modules/ltsa/pages/MechanicalSealStock.jsx", "utf8");
    expect(text).not.toMatch(/sample|mock/i);
  });
});
