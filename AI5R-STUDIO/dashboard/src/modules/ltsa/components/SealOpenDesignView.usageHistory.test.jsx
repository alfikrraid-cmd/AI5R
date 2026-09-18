import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SealOpenDesignView from "./SealOpenDesignView";

// MWO-LTSA-SEAL-USAGE-HISTORY-READ-MODEL-001 (R2J) -- component-level
// tests for the new Usage History tab, driven directly by props
// (mirroring SealOpenDesignView.drawingsBom.test.jsx's own convention:
// this component never fetches, Seal.jsx resolves usageHistory/
// usageHistoryLoading/usageHistoryError and passes them down -- see
// Seal.test.jsx's own "Usage History fetch wiring (R2J)" describe block
// for the fetch-side single-call/error-state coverage). Every fixture
// below is synthetic, matching the real R2I backend event shape
// (mechanical_seal_usage_history_service.py's project_usage_history_event
// return dict) -- never derived from the R2C/R2G diagnostic CSVs.

const SEAL = {
  code: "SC-101", sealId: "MS-JC-0101", name: "John Crane Type 21",
  type: "T48MP", manufacturer: "John Crane", model: null, shaftSize: 50,
  material: "Carbon/Silicon Carbide", temperatureLimit: 120, pressureLimit: 16,
  kimapPertamina: null, gpnJohnCrane: null, updatedAt: null, updatedBy: null,
  status: "ACTIVE", compatiblePumps: [], compatibleSeals: [], recommendation: null,
};

function openUsageHistoryTab() {
  fireEvent.click(screen.getByRole("tab", { name: "Usage History" }));
}

function openHistoryTab() {
  fireEvent.click(screen.getByRole("tab", { name: "History" }));
}

function usageHistorySection() {
  return document.querySelector('[data-od-id="usage-history-list"]');
}

// Base confirmed event -- individual tests override only what they need,
// same convention as Seal.test.jsx's own base-record helpers elsewhere
// in this codebase.
function confirmedEvent(overrides = {}) {
  return {
    event_id: "INSTL-100-2026",
    event_date: "2026-01-05",
    pump_tag: "211-P-8A",
    master_seal_code: "LTSA-SEAL-T48MP-2-1-8",
    master_seal_id: "N/A",
    master_association_status: "CONFIRMED",
    master_association_approvable: true,
    classifier_class: "A",
    intervention_type: "REPLACEMENT",
    intervention_actions: ["COMPLETE_SEAL_REPLACE"],
    detail: null,
    source_type: "INSTALLATION_REPORT",
    source_id: "INSTL-100-2026",
    provenance_status: "CLEAR",
    physical_seal_unit_id: null,
    physical_unit_identity_status: "NOT_PROVABLE",
    warranty_status: "N/A",
    running_days: 120,
    review: { intervention: "NOT_DERIVABLE_FROM_STRUCTURED_DATA", master_association: "RESOLVED", provenance: "CLEAR" },
    ...overrides,
  };
}

describe("Mechanical Seal Workspace -- Usage History tab exists and is distinct from History (R2J)", () => {
  it("renders a selectable 'Usage History' tab", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[]} />);

    expect(screen.getByRole("tab", { name: "Usage History" })).toBeTruthy();
  });

  it("keeps the pre-existing 'History' tab present and distinct from the new tab", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[]} />);

    expect(screen.getByRole("tab", { name: "History" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Usage History" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "History" })).not.toBe(screen.getByRole("tab", { name: "Usage History" }));
  });

  it("regression: the existing History tab still renders Related PM/CM/WorkOrder content, unreplaced by the new tab", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent()]}
        pmRecords={[{ id: "PM-100", nextDue: "2026-02-01", status: "OPEN" }]}
        cmRecords={[{ id: "CM-200", failureDescription: "Leak observed", status: "OPEN" }]}
        workOrderRecords={[{ id: "WO-300", title: "Replace seal", status: "OPEN" }]}
      />
    );
    openHistoryTab();

    expect(screen.getByText("PM-100")).toBeTruthy();
    expect(screen.getByText("CM-200")).toBeTruthy();
    expect(screen.getByText("WO-300")).toBeTruthy();
    // The confirmed Usage History event's own id must never leak into the
    // unrelated History tab's Related Engineering groups.
    expect(screen.queryByText("INSTL-100-2026")).toBeNull();
  });
});

describe("Mechanical Seal Workspace -- Usage History loading/error/empty states (R2J)", () => {
  it("shows the existing loading pattern while usage history is being fetched", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistoryLoading />);
    openUsageHistoryTab();

    expect(screen.getByTestId("seal-usage-history-loading")).toBeTruthy();
  });

  it("shows an explicit, recoverable error state on fetch failure -- never silently converted to an empty history", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[]} usageHistoryError="Seal Usage History API unavailable" />);
    openUsageHistoryTab();

    expect(screen.getByTestId("seal-usage-history-error")).toBeTruthy();
    expect(screen.getByText("Seal Usage History API unavailable")).toBeTruthy();
    expect(screen.queryByText(/no usage history recorded/i)).toBeNull();
  });

  it("shows a genuine empty state (not an error, not fake demo rows) when the API returns zero events", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[]} />);
    openUsageHistoryTab();

    expect(screen.getByText("No usage history recorded for this mechanical seal.")).toBeTruthy();
    expect(screen.queryByTestId("seal-usage-history-error")).toBeNull();
    expect(screen.queryByTestId("seal-usage-history-loading")).toBeNull();
  });
});

describe("Mechanical Seal Workspace -- Usage History event rendering (R2J)", () => {
  it("renders a CONFIRMED event's date/pump/event/detail/running days/source/status columns from real structured fields", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[confirmedEvent()]} />);
    openUsageHistoryTab();

    const section = within(usageHistorySection());
    expect(section.getByText("2026-01-05")).toBeTruthy();
    expect(section.getByText("211-P-8A")).toBeTruthy();
    expect(section.getByText("Mechanical Seal Replacement")).toBeTruthy();
    expect(section.getByText("Complete mechanical seal replaced")).toBeTruthy();
    expect(section.getByText("120")).toBeTruthy();
    expect(section.getByText("Installation Report")).toBeTruthy();
    expect(section.getByText("Confirmed")).toBeTruthy();
  });

  it("renders exactly one row per event, never duplicated or dropped", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[
          confirmedEvent({ event_id: "INSTL-1", event_date: "2026-01-01" }),
          confirmedEvent({ event_id: "INSTL-2", event_date: "2026-02-01" }),
          confirmedEvent({ event_id: "INSTL-3", event_date: "2026-03-01" }),
        ]}
      />
    );
    openUsageHistoryTab();

    const rows = usageHistorySection().querySelectorAll("tbody tr");
    expect(rows.length).toBe(3);
  });

  it("renders UNKNOWN intervention_type as 'Intervention Not Classified', never as an error", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[confirmedEvent({ intervention_type: "UNKNOWN", intervention_actions: [], detail: null })]} />);
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("Intervention Not Classified")).toBeTruthy();
    expect(screen.queryByTestId("seal-usage-history-error")).toBeNull();
  });

  it("never renders a COMPONENT_REPLACE action as a complete mechanical seal replacement", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ intervention_type: "REPAIR", intervention_actions: ["COMPONENT_REPLACE"], detail: null })]}
      />
    );
    openUsageHistoryTab();

    const section = within(usageHistorySection());
    expect(section.getByText("Components replaced")).toBeTruthy();
    expect(section.queryByText(/complete mechanical seal replaced/i)).toBeNull();
  });

  it("renders COMPLETE_SEAL_REPLACE as 'Complete mechanical seal replaced' (allowed wording)", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ intervention_type: "REPLACEMENT", intervention_actions: ["COMPLETE_SEAL_REPLACE"], detail: null })]}
      />
    );
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("Complete mechanical seal replaced")).toBeTruthy();
  });

  it("falls back to a derived action-based detail only when the backend detail text is absent -- never invents narrative text", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ detail: null, intervention_actions: ["CLEAN", "LAPPING"] })]}
      />
    );
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("Cleaned, Lapping")).toBeTruthy();
  });

  it("uses the backend's own detail text verbatim when present, instead of deriving one", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ detail: "Manual engineering review required.", intervention_actions: ["COMPONENT_REPLACE"] })]}
      />
    );
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("Manual engineering review required.")).toBeTruthy();
  });

  it("shows 'N/A' for running_days when null, never a client-computed number", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[confirmedEvent({ running_days: null })]} />);
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("N/A")).toBeTruthy();
  });

  it("keeps an UNRESOLVED master association visible as 'Master Unresolved', never hidden", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ master_association_status: "UNRESOLVED", master_seal_code: null, classifier_class: "C" })]}
      />
    );
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("Master Unresolved")).toBeTruthy();
  });

  it("keeps an AMBIGUOUS master association visible as 'Review Required'", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ master_association_status: "AMBIGUOUS", master_seal_code: null, classifier_class: "B" })]}
      />
    );
    openUsageHistoryTab();

    expect(within(usageHistorySection()).getByText("Review Required")).toBeTruthy();
  });

  it("keeps a PROVENANCE_HOLD event visible with an always-visible warning caption -- never hover-only, never hidden even with a clean type/size match", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[
          confirmedEvent({
            master_association_status: "PROVENANCE_HOLD",
            provenance_status: "HOLD",
            review: { intervention: "NOT_DERIVABLE_FROM_STRUCTURED_DATA", master_association: "NEEDS_REVIEW", provenance: "CONTRADICTION_FOUND" },
          }),
        ]}
      />
    );
    openUsageHistoryTab();

    const section = within(usageHistorySection());
    expect(section.getByText("Provenance Hold")).toBeTruthy();
    // Rendered unconditionally in the DOM (no hover/focus simulation
    // needed to reveal it) -- proves it is not a hover-only tooltip.
    expect(section.getByTestId("seal-usage-history-provenance-warning")).toBeTruthy();
  });
});

describe("Mechanical Seal Workspace -- Usage History source display (R2J)", () => {
  it("renders the source as a clickable 'Installation Report' link when a navigation handler is supplied", () => {
    const onOpenInstallationSource = vi.fn();
    render(<SealOpenDesignView seal={SEAL} usageHistory={[confirmedEvent()]} onOpenInstallationSource={onOpenInstallationSource} />);
    openUsageHistoryTab();

    const link = within(usageHistorySection()).getByRole("button", { name: "Installation Report" });
    fireEvent.click(link);

    expect(onOpenInstallationSource).toHaveBeenCalledTimes(1);
    expect(onOpenInstallationSource).toHaveBeenCalledWith("INSTL-100-2026");
  });

  it("renders the source as a plain, non-clickable label when no navigation handler is supplied", () => {
    render(<SealOpenDesignView seal={SEAL} usageHistory={[confirmedEvent()]} />);
    openUsageHistoryTab();

    const section = within(usageHistorySection());
    expect(section.getByText("Installation Report")).toBeTruthy();
    expect(section.queryByRole("button", { name: "Installation Report" })).toBeNull();
  });
});

describe("Mechanical Seal Workspace -- Usage History never implies physical seal identity (R2J)", () => {
  it("never displays master_seal_id, a synthesized MS-JC id, or physical_seal_unit_id anywhere in the tab", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        usageHistory={[confirmedEvent({ master_seal_id: "N/A", physical_seal_unit_id: null, physical_unit_identity_status: "NOT_PROVABLE" })]}
      />
    );
    openUsageHistoryTab();

    const section = usageHistorySection();
    expect(section.textContent).not.toMatch(/MS-JC-\d+/);
    expect(section.textContent).not.toMatch(/PHYS-/);
  });
});
