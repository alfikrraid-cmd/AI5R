import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Seal from "./Seal";
import {
  getSealCompatibility, getSealStock, postEngineeringAI,
  getPMSchedules, getCMReports, getWorkOrders, updateSealIdentifiers,
  getSealUnits,
  getSealUnitLifecycle,
  getSealUnitInspections,
  getSealUnitRepairs,
  getSealUnitWarranty,
  getSealUnitInstallationReports,
  getSealUnitHistory,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";
import sampleSeals from "../data/sampleSeals";

// MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- KIMAP Pertamina / GPN John
// Crane manual completion. A separate file from Seal.test.jsx, same
// convention as Seal.engineeringAI.test.jsx (a distinct feature area,
// reusing that file's own mock/fixture setup rather than editing it).
vi.mock("../../../api/ai5rClient", () => ({
  getSeals: vi.fn(),
  getSealCompatibility: vi.fn(),
  getSealStock: vi.fn(),
  postEngineeringAI: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
  getWorkOrders: vi.fn(),
  updateSealIdentifiers: vi.fn(),
  getSealUnits: vi.fn(),
  getSealUnitLifecycle: vi.fn(),
  getSealUnitInspections: vi.fn(),
  getSealUnitRepairs: vi.fn(),
  getSealUnitWarranty: vi.fn(),
  getSealUnitInstallationReports: vi.fn(),
  getSealUnitHistory: vi.fn(),
  onUnauthorized: vi.fn(),
}));

beforeEach(() => {
  postEngineeringAI.mockResolvedValue({
    summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
    risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
    token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
  });
  getSealCompatibility.mockResolvedValue([]);
  getSealStock.mockResolvedValue([]);
  getPMSchedules.mockResolvedValue([]);
  getCMReports.mockResolvedValue([]);
  getWorkOrders.mockResolvedValue([]);
  getSealUnits.mockResolvedValue([]);
  getSealUnitLifecycle.mockResolvedValue([]);
  getSealUnitInspections.mockResolvedValue([]);
  getSealUnitRepairs.mockResolvedValue([]);
  getSealUnitWarranty.mockResolvedValue([]);
  getSealUnitInstallationReports.mockResolvedValue([]);
  getSealUnitHistory.mockResolvedValue([]);
});

afterEach(() => {
  vi.clearAllMocks();
});

// Renders inside an AuthProvider with a fake authClient -- permissions=null
// simulates "no real session" (getSession resolves null, status stays
// unauthenticated -- this component would never actually be reachable
// unauthenticated in the real app, but the point here is only to prove
// canEditIdentifiers correctly resolves to false via useOptionalAuth()
// when session.permissions doesn't grant master.edit).
function renderWithSession(permissions) {
  const client = {
    getSession: () =>
      Promise.resolve(
        permissions
          ? {
              user: { name: "Test User" },
              organization: { displayName: "TAP" },
              role: "TAP_ADMIN",
              permissions,
            }
          : null
      ),
  };
  return render(
    <AuthProvider client={client}>
      <Seal seals={sampleSeals} />
    </AuthProvider>
  );
}

describe("Seal Identifiers -- view mode (honest empty state, every role)", () => {
  it("renders 'Not yet completed' for KIMAP and GPN when neither has been set", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.getAllByText("Not yet completed").length).toBeGreaterThanOrEqual(2);
  });

  it("renders a real KIMAP/GPN value when the seal record already carries one", () => {
    const seals = sampleSeals.map((s) =>
      s.code === "SC-001" ? { ...s, kimapPertamina: "KIMAP-9001", gpnJohnCrane: "GPN-JC-4002" } : s
    );
    render(<Seal seals={seals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.getByText("KIMAP-9001")).toBeTruthy();
    expect(screen.getByText("GPN-JC-4002")).toBeTruthy();
  });

  it("shows 'Imported / system data' for Updated By when no actor is recorded", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.getByText("Imported / system data")).toBeTruthy();
  });

  it("shows the raw actor id for Updated By when one is recorded (no display-name resolution -- disclosed gap)", () => {
    const seals = sampleSeals.map((s) =>
      s.code === "SC-001" ? { ...s, updatedBy: "actor-uuid-123", updatedAt: "2026-08-17T10:00:00" } : s
    );
    render(<Seal seals={seals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.getByText("actor-uuid-123")).toBeTruthy();
    expect(screen.getByText("2026-08-17 10:00:00")).toBeTruthy();
  });
});

describe("Seal Identifiers -- search (Phase 11)", () => {
  it("finds a seal by KIMAP Pertamina", () => {
    const seals = sampleSeals.map((s) => (s.code === "SC-001" ? { ...s, kimapPertamina: "KIMAP-9001" } : s));
    render(<Seal seals={seals} />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "KIMAP-9001" } });

    expect(screen.getByText("SC-001")).toBeTruthy();
    expect(screen.queryByText("SC-002")).toBeNull();
  });

  it("finds a seal by GPN John Crane", () => {
    const seals = sampleSeals.map((s) => (s.code === "SC-001" ? { ...s, gpnJohnCrane: "GPN-JC-4002" } : s));
    render(<Seal seals={seals} />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "GPN-JC-4002" } });

    expect(screen.getByText("SC-001")).toBeTruthy();
    expect(screen.queryByText("SC-002")).toBeNull();
  });

  it("finds a seal by compatible Pump Tag", () => {
    render(<Seal seals={sampleSeals} />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "PMP-002" } });

    expect(screen.getByText("SC-001")).toBeTruthy();
    expect(screen.queryByText("SC-002")).toBeNull();
  });

  it("does not crash searching when kimapPertamina/gpnJohnCrane are absent (undefined, not null)", () => {
    expect(() => {
      render(<Seal seals={sampleSeals} />);
      fireEvent.change(screen.getByRole("searchbox"), { target: { value: "anything" } });
    }).not.toThrow();
  });
});

describe("Seal Identifiers -- manual completion authorization (Phase 6/13/14)", () => {
  it("shows no edit control when rendered with no AuthProvider at all (every pre-existing Seal.jsx test's own shape)", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.queryByText("Edit KIMAP / GPN →")).toBeNull();
  });

  it("shows no edit control for a session without master.edit (e.g. JOHN_CRANE_ENGINEER/PERTAMINA_*)", async () => {
    renderWithSession(["seal.read", "inventory.read"]);
    await waitFor(() => expect(screen.getByText("SC-001")).toBeTruthy());
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.queryByText("Edit KIMAP / GPN →")).toBeNull();
  });

  it("shows the edit control for a session with master.edit (TAP_ADMIN/SUPERUSER)", async () => {
    renderWithSession(["seal.read", "master.edit"]);
    await waitFor(() => expect(screen.getByText("SC-001")).toBeTruthy());
    fireEvent.click(screen.getByText("SC-001"));

    expect(screen.getByText("Edit KIMAP / GPN →")).toBeTruthy();
  });
});

describe("Seal Identifiers -- manual completion (Golden Scenarios A/B)", () => {
  it("submits the current form values to updateSealIdentifiers and reflects the result", async () => {
    updateSealIdentifiers.mockResolvedValue({
      data: {
        seal_code: "SC-001", kimap_pertamina: "KIMAP-9001", gpn_john_crane: null,
        created_by: null, updated_by: "actor-1",
        created_at: "2026-01-01T00:00:00", updated_at: "2026-08-17T12:00:00",
      },
    });
    renderWithSession(["seal.read", "master.edit"]);
    await waitFor(() => expect(screen.getByText("SC-001")).toBeTruthy());
    fireEvent.click(screen.getByText("SC-001"));
    fireEvent.click(screen.getByText("Edit KIMAP / GPN →"));

    fireEvent.change(screen.getByLabelText("KIMAP Pertamina"), { target: { value: "KIMAP-9001" } });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() =>
      expect(updateSealIdentifiers).toHaveBeenCalledWith("SC-001", {
        kimapPertamina: "KIMAP-9001",
        gpnJohnCrane: "",
      })
    );
    expect(await screen.findByText("KIMAP-9001")).toBeTruthy();
    // Stock quantity is never part of this form -- no such field exists to submit.
    expect(screen.queryByLabelText(/quantity/i)).toBeNull();
  });

  it("surfaces a verbatim backend error instead of swallowing it, and keeps the form open", async () => {
    updateSealIdentifiers.mockRejectedValueOnce(new Error("master.edit required"));
    renderWithSession(["seal.read", "master.edit"]);
    await waitFor(() => expect(screen.getByText("SC-001")).toBeTruthy());
    fireEvent.click(screen.getByText("SC-001"));
    fireEvent.click(screen.getByText("Edit KIMAP / GPN →"));

    fireEvent.click(screen.getByText("Save"));

    expect(await screen.findByTestId("seal-identifiers-error")).toHaveProperty(
      "textContent",
      "master.edit required"
    );
    expect(screen.getByText("Save")).toBeTruthy(); // form still open
  });

  it("cancel closes the form without calling updateSealIdentifiers", async () => {
    renderWithSession(["seal.read", "master.edit"]);
    await waitFor(() => expect(screen.getByText("SC-001")).toBeTruthy());
    fireEvent.click(screen.getByText("SC-001"));
    fireEvent.click(screen.getByText("Edit KIMAP / GPN →"));

    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByText("Save")).toBeNull();
    expect(updateSealIdentifiers).not.toHaveBeenCalled();
  });
});
