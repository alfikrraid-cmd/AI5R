import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KnowledgeCompatibleSeals from "./KnowledgeCompatibleSeals";
import { resolveAreaMA } from "../utils/areaMapping";

describe("areaMapping -- canonical Area -> MA derivation", () => {
  it("maps HOC to MA1", () => {
    expect(resolveAreaMA("HOC")).toBe("MA1");
    expect(resolveAreaMA("hoc")).toBe("MA1");
  });

  it("maps HSC, S_PAKNING, HCC and variants to MA2", () => {
    expect(resolveAreaMA("HSC")).toBe("MA2");
    expect(resolveAreaMA("HCC")).toBe("MA2");
    expect(resolveAreaMA("S_PAKNING")).toBe("MA2");
    expect(resolveAreaMA("S. PAKNING")).toBe("MA2");
    expect(resolveAreaMA("S.PAKNING")).toBe("MA2");
    expect(resolveAreaMA("SPK")).toBe("MA2");
  });

  it("maps UTL and UTILITIES to MA3", () => {
    expect(resolveAreaMA("UTL")).toBe("MA3");
    expect(resolveAreaMA("UTILITIES")).toBe("MA3");
  });

  it("maps OM and OIL MOVEMENT to MA4", () => {
    expect(resolveAreaMA("OM")).toBe("MA4");
    expect(resolveAreaMA("OIL MOVEMENT")).toBe("MA4");
  });

  it("returns dash for unmapped, null, or empty areas without fabricating", () => {
    expect(resolveAreaMA(null)).toBe("—");
    expect(resolveAreaMA("")).toBe("—");
    expect(resolveAreaMA("UNKNOWN_AREA")).toBe("—");
  });
});

describe("KnowledgeCompatibleSeals -- reverse compatibility discovery", () => {
  const SAMPLE_ITEMS = [
    { id: "LTSA-SEAL-T48MP-2-3-8", name: "T48MP", meta: "LTSA-SEAL-T48MP-2-3-8" },
  ];

  const SAMPLE_COMPATIBILITY = [
    { seal_code: "LTSA-SEAL-T48MP-2-3-8", pump_tag_number: "101-P-10A" },
    { seal_code: "LTSA-SEAL-T48MP-2-3-8", pump_tag_number: "102-P-20B" },
    { seal_code: "LTSA-SEAL-T48MP-2-3-8", pump_tag_number: "UNAUTHORIZED-PUMP" },
    { seal_code: "OTHER-SEAL-001", pump_tag_number: "103-P-30C" },
  ];

  const AUTHORIZED_PUMPS = [
    { tag_number: "101-P-10A", area: "HOC", status: "ACTIVE" },
    { tag_number: "102-P-20B", area: "S_PAKNING", status: "STANDBY" },
    { tag_number: "103-P-30C", area: "UTL", status: "ACTIVE" },
  ];

  it("renders empty state when items is empty", () => {
    render(<KnowledgeCompatibleSeals items={[]} emptyTitle="No compatible seals" />);
    expect(screen.getByText("No compatible seals")).toBeInTheDocument();
  });

  it("renders seal name, variant code, and resolves distinct variant and family counts", () => {
    render(
      <KnowledgeCompatibleSeals
        items={SAMPLE_ITEMS}
        compatibilityRecords={SAMPLE_COMPATIBILITY}
        pumps={AUTHORIZED_PUMPS}
      />
    );

    expect(screen.getByText("T48MP")).toBeInTheDocument();
    expect(screen.getByText("LTSA-SEAL-T48MP-2-3-8")).toBeInTheDocument();
    // UNAUTHORIZED-PUMP is excluded from the count (fleet leak prevention!)
    expect(screen.getByTestId("compat-count-LTSA-SEAL-T48MP-2-3-8")).toHaveTextContent(
      "Compatible with 2 pumps (variant LTSA-SEAL-T48MP-2-3-8)"
    );
    expect(screen.getByTestId("compat-family-count-LTSA-SEAL-T48MP-2-3-8")).toHaveTextContent(
      "T48MP family: 2 distinct pumps in scope"
    );
  });

  it("deduplicates multi-variant pumps and raw duplicates across variant and family scopes", () => {
    const multiVariantCompatibility = [
      // Pump 101-P-10B has TWO distinct T48MP variants
      { seal_code: "LTSA-SEAL-T48MP-2-3-8", pump_tag_number: "101-P-10B" },
      { seal_code: "LTSA-SEAL-T48MP-1-3-8", pump_tag_number: "101-P-10B" },
      // Duplicate raw record for 101-P-10A with same variant
      { seal_code: "LTSA-SEAL-T48MP-2-3-8", pump_tag_number: "101-P-10A" },
      { seal_code: "LTSA-SEAL-T48MP-2-3-8", pump_tag_number: "101-P-10A" },
      // Distinct pump on another variant of the same family
      { seal_code: "LTSA-SEAL-T48MP-1-3-8", pump_tag_number: "103-P-30C" },
      // Unauthorized pump
      { seal_code: "LTSA-SEAL-T48MP-1-3-8", pump_tag_number: "UNAUTHORIZED-PUMP" },
    ];

    const authorizedFleet = [
      { tag_number: "101-P-10A", area: "HOC", status: "ACTIVE" },
      { tag_number: "101-P-10B", area: "HOC", status: "ACTIVE" },
      { tag_number: "103-P-30C", area: "UTL", status: "STANDBY" },
    ];

    const sealRegistry = [
      { seal_code: "LTSA-SEAL-T48MP-2-3-8", seal_name: "T48MP" },
      { seal_code: "LTSA-SEAL-T48MP-1-3-8", seal_name: "T48MP" },
    ];

    render(
      <KnowledgeCompatibleSeals
        items={SAMPLE_ITEMS}
        compatibilityRecords={multiVariantCompatibility}
        pumps={authorizedFleet}
        seals={sealRegistry}
      />
    );

    // Variant LTSA-SEAL-T48MP-2-3-8 maps to 101-P-10A and 101-P-10B (2 pumps, despite duplicate raw row for 101-P-10A)
    expect(screen.getByTestId("compat-count-LTSA-SEAL-T48MP-2-3-8")).toHaveTextContent(
      "Compatible with 2 pumps (variant LTSA-SEAL-T48MP-2-3-8)"
    );

    // T48MP family maps to 101-P-10A, 101-P-10B, and 103-P-30C = 3 distinct pumps (101-P-10B only counted once!)
    expect(screen.getByTestId("compat-family-count-LTSA-SEAL-T48MP-2-3-8")).toHaveTextContent(
      "T48MP family: 3 distinct pumps in scope"
    );

    // Expand table
    fireEvent.click(screen.getByTestId("compat-toggle-LTSA-SEAL-T48MP-2-3-8"));

    // Check tabs appear because familyCount (3) > variantCount (2)
    const variantTab = screen.getByTestId("compat-tab-variant-LTSA-SEAL-T48MP-2-3-8");
    const familyTab = screen.getByTestId("compat-tab-family-LTSA-SEAL-T48MP-2-3-8");
    expect(variantTab).toHaveTextContent("Variant (2)");
    expect(familyTab).toHaveTextContent("All T48MP Family (3)");

    // In default variant view: 101-P-10A and 101-P-10B are present, 103-P-30C is NOT in variant
    expect(screen.getByText("101-P-10A")).toBeInTheDocument();
    expect(screen.getByText("101-P-10B")).toBeInTheDocument();
    expect(screen.queryByText("103-P-30C")).toBeNull();

    // Switch to Family tab
    fireEvent.click(familyTab);
    expect(screen.getByText("103-P-30C")).toBeInTheDocument();
    expect(screen.getByText("101-P-10B")).toBeInTheDocument();
    expect(screen.queryByText("UNAUTHORIZED-PUMP")).toBeNull();
  });

  it("toggles the compatible pumps table drawer on click", () => {
    render(
      <KnowledgeCompatibleSeals
        items={SAMPLE_ITEMS}
        compatibilityRecords={SAMPLE_COMPATIBILITY}
        pumps={AUTHORIZED_PUMPS}
      />
    );

    const toggle = screen.getByTestId("compat-toggle-LTSA-SEAL-T48MP-2-3-8");
    expect(toggle).toHaveTextContent("View all ▾");
    expect(screen.queryByTestId("compat-pumps-table-LTSA-SEAL-T48MP-2-3-8")).toBeNull();

    // Expand
    fireEvent.click(toggle);
    expect(toggle).toHaveTextContent("Hide pumps ▴");
    const table = screen.getByTestId("compat-pumps-table-LTSA-SEAL-T48MP-2-3-8");
    expect(table).toBeInTheDocument();

    // Verify columns and values
    expect(screen.getByText("101-P-10A")).toBeInTheDocument();
    expect(screen.getByText("HOC")).toBeInTheDocument();
    expect(screen.getByText("MA1")).toBeInTheDocument();

    expect(screen.getByText("102-P-20B")).toBeInTheDocument();
    expect(screen.getByText("S_PAKNING")).toBeInTheDocument();
    expect(screen.getByText("MA2")).toBeInTheDocument();

    // Unauthorized pump is strictly excluded
    expect(screen.queryByText("UNAUTHORIZED-PUMP")).toBeNull();

    // Collapse again
    fireEvent.click(toggle);
    expect(screen.queryByTestId("compat-pumps-table-LTSA-SEAL-T48MP-2-3-8")).toBeNull();
  });
});

