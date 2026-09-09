import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KnowledgeCompatibleSeals from "./KnowledgeCompatibleSeals";
import { resolveAreaMA, normalizeAreaToken } from "../utils/areaMapping";

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

  it("renders seal name, code, and resolves authorized pump count", () => {
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
      "Compatible with 2 pumps"
    );
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

