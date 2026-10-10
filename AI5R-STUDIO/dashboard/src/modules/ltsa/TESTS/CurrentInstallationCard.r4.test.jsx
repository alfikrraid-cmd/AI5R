import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import React from "react";
import CurrentInstallationCard from "../components/CurrentInstallationCard";
import { getPumpCurrentInstallation } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getPumpCurrentInstallation: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

const singlePumpConfirmed = {
  success: true,
  pump_tag: "101-P-2A",
  pump_type: "OH2",
  status: "CONFIRMED",
  positions: {
    SINGLE: {
      equipment_side: "SINGLE",
      seal_type: "T48LP",
      seal_size: '2.375"',
      drawing_no: "GA-243047",
      material_code: "X49 P147 1 X49 D81 H 316/HC",
      assembly_gpn: "GPN-101-2A",
      source_type: "INSTALLATION_REPORT",
      source_reference: "INSTL-024-2026",
      source_date: "2026-05-05",
      resolution_status: "CONFIRMED",
      confidence_status: "CONFIRMED",
      installed_at: "2026-05-05T00:00:00+00:00",
      installed_seal: {
        seal_type: "T48LP",
        seal_size: '2.375"',
        drawing_no: "GA-243047",
        material_code: "X49 P147 1 X49 D81 H 316/HC",
        assembly_gpn: "GPN-101-2A",
      },
    },
  },
  unpositioned_evidence: [],
};

const bbPumpConfirmed = {
  success: true,
  pump_tag: "211-P-1A",
  pump_type: "BB2",
  status: "CONFIRMED",
  positions: {
    DE: {
      equipment_side: "DE",
      seal_type: "T8B1-RS",
      seal_size: '4.1/2"',
      drawing_no: "GA-243050",
      material_code: "MAT-DE-8B1",
      assembly_gpn: "GPN-DE-001",
      source_type: "INSTALLATION_REPORT",
      source_reference: "INSTL-033-2026",
      source_date: "2026-05-22",
      resolution_status: "CONFIRMED",
      confidence_status: "CONFIRMED",
      installed_at: "2026-05-22T00:00:00+00:00",
      installed_seal: {
        seal_type: "T8B1-RS",
        seal_size: '4.1/2"',
        drawing_no: "GA-243050",
        material_code: "MAT-DE-8B1",
        assembly_gpn: "GPN-DE-001",
      },
    },
    NDE: {
      equipment_side: "NDE",
      seal_type: "T8B1-RS",
      seal_size: '4.1/2"',
      drawing_no: "GA-243050",
      material_code: "MAT-NDE-8B1",
      assembly_gpn: "GPN-NDE-001",
      source_type: "INSTALLATION_REPORT",
      source_reference: "INSTL-033-2026",
      source_date: "2026-05-22",
      resolution_status: "CONFIRMED",
      confidence_status: "CONFIRMED",
      installed_at: "2026-05-22T00:00:00+00:00",
      installed_seal: {
        seal_type: "T8B1-RS",
        seal_size: '4.1/2"',
        drawing_no: "GA-243050",
        material_code: "MAT-NDE-8B1",
        assembly_gpn: "GPN-NDE-001",
      },
    },
  },
  unpositioned_evidence: [],
};

const emptyPump = {
  success: true,
  pump_tag: "101-P-2B",
  pump_type: "OH2",
  status: "NO_CURRENT_RECORD",
  positions: {
    SINGLE: {
      equipment_side: "SINGLE",
      resolution_status: "NO_AUTHORITATIVE_EVIDENCE",
      installed_seal: null,
    },
  },
  unpositioned_evidence: [],
};

const reviewPump = {
  success: true,
  pump_tag: "101-P-6A",
  pump_type: "OH2",
  status: "NO_CURRENT_RECORD",
  positions: {
    SINGLE: {
      equipment_side: "SINGLE",
      resolution_status: "NO_AUTHORITATIVE_EVIDENCE",
      installed_seal: null,
    },
  },
  unpositioned_evidence: [
    {
      source_reference: "INSTL-006-2026",
      resolution_status: "REVIEW_REQUIRED",
      source_date: "2026-01-15",
    },
  ],
};

const conflictPump = {
  success: true,
  pump_tag: "101-P-3B",
  pump_type: "OH2",
  status: "NO_CURRENT_RECORD",
  positions: {
    SINGLE: {
      equipment_side: "SINGLE",
      resolution_status: "NO_AUTHORITATIVE_EVIDENCE",
      installed_seal: null,
    },
  },
  unpositioned_evidence: [
    {
      source_reference: "INSTL-018-2026",
      resolution_status: "CONFLICT",
      source_date: "2026-03-10",
    },
  ],
};

const sampleDrawings = [
  {
    id: "GA-243047",
    documentNumber: "GA-243047",
    title: "Mechanical Seal Drawing 101-P-2A",
  },
  {
    id: "GA-243050",
    documentNumber: "GA-243050",
    title: "Mechanical Seal Drawing 211-P-1A",
  },
];

describe("LTSA_CURRENT_INSTALLATION_ASSET360_UI_R4 Test Suite", () => {
  // Test 1: SINGLE pump confirmed
  it("Test 1: SINGLE pump confirmed renders SINGLE position with seal type, size, drawing, source ref, date", async () => {
    getPumpCurrentInstallation.mockResolvedValue(singlePumpConfirmed);

    render(
      <CurrentInstallationCard
        tag="101-P-2A"
        drawings={sampleDrawings}
        configuredSeal={{ sealType: "T48LP" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());

    const singleBlock = screen.getByTestId("position-single");
    expect(singleBlock).toBeInTheDocument();
    expect(within(singleBlock).getByText("SINGLE")).toBeInTheDocument();
    expect(within(singleBlock).getByTestId("installed-seal-type")).toHaveTextContent("T48LP");
    expect(within(singleBlock).getByTestId("installed-seal-size")).toHaveTextContent('2.375"');
    expect(within(singleBlock).getByTestId("installed-date")).toHaveTextContent("2026-05-05");
    expect(within(singleBlock).getByTestId("installed-source-ref")).toHaveTextContent("INSTL-024-2026");
    expect(within(singleBlock).getByText("Installation Report")).toBeInTheDocument();
    expect(within(singleBlock).getByTestId("installed-assembly-gpn")).toHaveTextContent("GPN-101-2A");
    expect(within(singleBlock).getByTestId("installed-material-code")).toHaveTextContent("X49 P147 1 X49 D81 H 316/HC");
    expect(within(singleBlock).getByTestId("position-status-single")).toHaveTextContent("Confirmed");
  });

  // Test 2: BB pump confirmed (DE and NDE rendered independently)
  it("Test 2: BB pump confirmed renders DE and NDE independently with respective seal details", async () => {
    getPumpCurrentInstallation.mockResolvedValue(bbPumpConfirmed);

    render(
      <CurrentInstallationCard
        tag="211-P-1A"
        drawings={sampleDrawings}
        configuredSeal={{ sealType: "T8B1-RS" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());

    const deBlock = screen.getByTestId("position-de");
    const ndeBlock = screen.getByTestId("position-nde");
    expect(deBlock).toBeInTheDocument();
    expect(ndeBlock).toBeInTheDocument();

    // DE position verification
    expect(within(deBlock).getByText("DE")).toBeInTheDocument();
    expect(within(deBlock).getByTestId("installed-seal-type")).toHaveTextContent("T8B1-RS");
    expect(within(deBlock).getByTestId("installed-seal-size")).toHaveTextContent('4.1/2"');
    expect(within(deBlock).getByTestId("installed-date")).toHaveTextContent("2026-05-22");
    expect(within(deBlock).getByTestId("installed-source-ref")).toHaveTextContent("INSTL-033-2026");
    expect(within(deBlock).getByTestId("installed-material-code")).toHaveTextContent("MAT-DE-8B1");

    // NDE position verification
    expect(within(ndeBlock).getByText("NDE")).toBeInTheDocument();
    expect(within(ndeBlock).getByTestId("installed-seal-type")).toHaveTextContent("T8B1-RS");
    expect(within(ndeBlock).getByTestId("installed-seal-size")).toHaveTextContent('4.1/2"');
    expect(within(ndeBlock).getByTestId("installed-date")).toHaveTextContent("2026-05-22");
    expect(within(ndeBlock).getByTestId("installed-source-ref")).toHaveTextContent("INSTL-033-2026");
    expect(within(ndeBlock).getByTestId("installed-material-code")).toHaveTextContent("MAT-NDE-8B1");

    // Ensure DE and NDE are not merged
    expect(screen.getAllByTestId(/position-(de|nde)/).length).toBe(2);
  });

  // Test 3: Empty pump (NO_CURRENT_RECORD)
  it("Test 3: Empty pump renders 'Not recorded' and 'No authoritative current installation record is available.'", async () => {
    getPumpCurrentInstallation.mockResolvedValue(emptyPump);

    render(
      <CurrentInstallationCard
        tag="101-P-2B"
        configuredSeal={{ sealType: "T48" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-empty")).toBeInTheDocument());

    expect(screen.getByTestId("current-installation-status")).toHaveTextContent(/not recorded/i);
    expect(screen.getByText("No authoritative current installation record is available.")).toBeInTheDocument();
    // Configured seal must NOT be substituted into installed seal
    expect(screen.queryByTestId("installed-seal-type")).toBeNull();
  });

  // Test 4: Review pump (101-P-6A)
  it("Test 4: Review pump (101-P-6A) renders 'Not confirmed' / 'Installation evidence requires review', no fabricated seal", async () => {
    getPumpCurrentInstallation.mockResolvedValue(reviewPump);

    render(
      <CurrentInstallationCard
        tag="101-P-6A"
        configuredSeal={{ sealType: "T48" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-review")).toBeInTheDocument());

    expect(screen.getByTestId("current-installation-status")).toHaveTextContent(/not confirmed/i);
    expect(screen.getByText("Installation evidence requires review.")).toBeInTheDocument();
    expect(screen.queryByTestId("installed-seal-type")).toBeNull();
  });

  // Test 5: Conflict pump (101-P-3B)
  it("Test 5: Conflict pump (101-P-3B) renders 'Not confirmed' / 'Installation evidence requires review', no fabricated seal", async () => {
    getPumpCurrentInstallation.mockResolvedValue(conflictPump);

    render(
      <CurrentInstallationCard
        tag="101-P-3B"
        configuredSeal={{ sealType: "T48" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-review")).toBeInTheDocument());

    expect(screen.getByTestId("current-installation-status")).toHaveTextContent(/not confirmed/i);
    expect(screen.getByText("Installation evidence requires review.")).toBeInTheDocument();
    expect(screen.queryByTestId("installed-seal-type")).toBeNull();
  });

  // Test 6: Variant difference (configured != installed shows neutral badge)
  it("Test 6: configured != installed shows 'Different from configured design' neutral indicator without error labels", async () => {
    getPumpCurrentInstallation.mockResolvedValue(singlePumpConfirmed);

    // Pump configured seal is "T48", but installed seal is variant "T48LP"
    render(
      <CurrentInstallationCard
        tag="101-P-2A"
        configuredSeal={{ sealType: "T48" }}
        drawings={sampleDrawings}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());

    const diffBadge = screen.getByTestId("configured-diff-indicator");
    expect(diffBadge).toBeInTheDocument();
    expect(diffBadge).toHaveTextContent("Different from configured design");

    // Must NEVER display ERROR, WRONG SEAL, or NON-COMPLIANT
    expect(screen.queryByText(/error/i)).toBeNull();
    expect(screen.queryByText(/wrong seal/i)).toBeNull();
    expect(screen.queryByText(/non-compliant/i)).toBeNull();
  });

  // Test 7: Strict no-fallback
  it("Test 7: when installed seal is null, configured seal NEVER appears in installed seal fields", async () => {
    getPumpCurrentInstallation.mockResolvedValue(emptyPump);

    render(
      <CurrentInstallationCard
        tag="101-P-2B"
        configuredSeal={{ sealType: "DESIGN-SPECIAL-999" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-empty")).toBeInTheDocument());

    // Configured seal DESIGN-SPECIAL-999 must not appear anywhere in installed card
    expect(screen.queryByText("DESIGN-SPECIAL-999")).toBeNull();
  });

  // Test 8: API error isolation
  it("Test 8: API error displays 'Current installation unavailable' and does not crash", async () => {
    getPumpCurrentInstallation.mockRejectedValue(new Error("Network connection failed"));

    render(
      <CurrentInstallationCard
        tag="101-P-2A"
        configuredSeal={{ sealType: "T48" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-error")).toBeInTheDocument());

    expect(screen.getByText(/current installation unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/network connection failed/i)).toBeInTheDocument();
    // Does not fall back to configured seal
    expect(screen.queryByText("T48")).toBeNull();
  });

  // Test 9: Stale state cleared on pump change
  it("Test 9: switching tag prop clears old installation immediately", async () => {
    getPumpCurrentInstallation.mockResolvedValueOnce(singlePumpConfirmed);

    const { rerender } = render(
      <CurrentInstallationCard
        tag="101-P-2A"
        configuredSeal={{ sealType: "T48LP" }}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());
    expect(screen.getByText("T48LP")).toBeInTheDocument();

    // Now mock a delayed response for pump B and change tag
    let resolveB;
    const promiseB = new Promise((resolve) => {
      resolveB = resolve;
    });
    getPumpCurrentInstallation.mockReturnValueOnce(promiseB);

    rerender(
      <CurrentInstallationCard
        tag="101-P-2B"
        configuredSeal={{ sealType: "T48" }}
      />
    );

    // Old pump A's installed seal type (T48LP) must immediately be cleared and loading shown
    expect(screen.queryByText("T48LP")).toBeNull();
    expect(screen.getByTestId("current-installation-loading")).toBeInTheDocument();

    // Resolve B with empty pump data
    resolveB(emptyPump);
    await waitFor(() => expect(screen.getByTestId("current-installation-empty")).toBeInTheDocument());
  });

  // Test 10: Source provenance displayed
  it("Test 10: source provenance displays Installation Report, reference code, and date", async () => {
    getPumpCurrentInstallation.mockResolvedValue(singlePumpConfirmed);

    render(
      <CurrentInstallationCard
        tag="101-P-2A"
        drawings={sampleDrawings}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());

    expect(screen.getByText("Installation Report")).toBeInTheDocument();
    expect(screen.getByTestId("installed-source-ref")).toHaveTextContent("INSTL-024-2026");
    expect(screen.getByTestId("installed-date")).toHaveTextContent("2026-05-05");
  });

  // Test 11: Drawing navigation (clickable when in registry, plain text when reference only)
  it("Test 11: drawing navigation is clickable when in registry and plain text when reference only", async () => {
    const onNavigateMock = vi.fn();
    getPumpCurrentInstallation.mockResolvedValue(singlePumpConfirmed);

    // Scenario A: drawing GA-243047 exists in registry -> View Drawing button is present and clickable
    const { unmount } = render(
      <CurrentInstallationCard
        tag="101-P-2A"
        drawings={sampleDrawings}
        onNavigate={onNavigateMock}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());

    const viewDrawingBtn = screen.getByRole("button", { name: /view drawing/i });
    expect(viewDrawingBtn).toBeInTheDocument();
    fireEvent.click(viewDrawingBtn);
    expect(onNavigateMock).toHaveBeenCalledTimes(1);
    expect(onNavigateMock).toHaveBeenCalledWith("drawing", {
      assetTag: "101-P-2A",
      drawingId: "GA-243047",
    });

    unmount();

    // Scenario B: drawing is NOT in registry (e.g. empty drawings array) -> plain text reference only
    getPumpCurrentInstallation.mockResolvedValue(singlePumpConfirmed);
    render(
      <CurrentInstallationCard
        tag="101-P-2A"
        drawings={[]} // No matching drawing
        onNavigate={onNavigateMock}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /view drawing/i })).toBeNull();
    expect(screen.getByText("GA-243047 (reference only)")).toBeInTheDocument();
  });

  // Test 12: Responsive DE/NDE layout maintains position separation
  it("Test 12: responsive layout uses positions-grid container maintaining DE and NDE separation", async () => {
    getPumpCurrentInstallation.mockResolvedValue(bbPumpConfirmed);

    const { container } = render(
      <CurrentInstallationCard
        tag="211-P-1A"
        drawings={sampleDrawings}
      />
    );

    await waitFor(() => expect(screen.getByTestId("current-installation-card")).toBeInTheDocument());

    const grid = container.querySelector(".positions-grid");
    expect(grid).toBeInTheDocument();
    const blocks = grid.querySelectorAll(".position-block");
    expect(blocks.length).toBe(2);
    expect(within(blocks[0]).getByText("DE")).toBeInTheDocument();
    expect(within(blocks[1]).getByText("NDE")).toBeInTheDocument();
  });
});
