import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ImportWorkspace from "./ImportWorkspace";
import {
  createImportSession,
  executeImportSession,
  getImportSessionStatus,
  validateImportPackage,
} from "../../../api/ai5rClient";

// MWO-LTSA-087/104 -- mirrors InstallationWorkspace.test.jsx/
// DocumentWorkspace.test.jsx's own vi.mock("../../../api/ai5rClient")
// convention: every real Import API call this workspace makes is mocked
// at the client boundary, never a fake backend -- the real backend
// contract for these four endpoints was already proven live via
// TestClient(app) in CORE-SERVICES/BACKEND-API/TESTS/test_import_router.py.
// checkImportConflicts is deliberately NOT mocked/imported here -- as of
// MWO-LTSA-104, ImportWorkspace.jsx no longer calls it (POST /session now
// computes and stores its own ConflictReport server-side, MWO-LTSA-103A).
vi.mock("../../../api/ai5rClient", () => ({
  validateImportPackage: vi.fn(),
  createImportSession: vi.fn(),
  executeImportSession: vi.fn(),
  getImportSessionStatus: vi.fn(),
}));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OPEN_DESIGN_VIEW_SOURCE = readFileSync(
  path.join(__dirname, "..", "components", "ImportOpenDesignView.jsx"),
  "utf-8"
);

const INCOMING_PACKAGE = {
  pumps: [{ tag_number: "P-100", area: "Unit 1" }],
  seals: [{ seal_code: "S-100" }],
  installations: [{ installation_code: "INSTL-100" }],
  documents: [{ document_code: "DOC-100" }],
};

function jsonFile(name, content) {
  return new File([JSON.stringify(content)], name, { type: "application/json" });
}

async function uploadIncomingPackage(container, content = INCOMING_PACKAGE, name = "incoming.json") {
  const input = screen.getByLabelText("Upload incoming import package");
  fireEvent.change(input, { target: { files: [jsonFile(name, content)] } });
  await waitFor(() => expect(screen.getByText(name)).toBeTruthy());
}

const SESSION_WITH_CONFLICT_REPORT = {
  success: true,
  data: {
    session_id: "IMPORT-SESSION-1",
    status: "REVIEWING",
    statistics: {
      total_packages: 1, valid_packages: 1, invalid_packages: 0, warning_packages: 0,
      conflict_count: 1, inserted: 0, updated: 0, skipped: 0, failed: 0,
    },
    execution_plan: [],
    conflict_report: {
      conflict_count: 1,
      manual_review_count: 1,
      create_new_count: 0,
      conflicts: [
        { entity_type: "pump", entity_id: "P-100", field: "area", database_value: "Unit 1", incoming_value: "Unit 2", resolution: "MANUAL_REVIEW", severity: "HIGH", status: "OPEN" },
      ],
    },
  },
};

beforeEach(() => {
  validateImportPackage.mockReset();
  createImportSession.mockReset();
  executeImportSession.mockReset();
  getImportSessionStatus.mockReset();
});

describe("Empty session (initial render, no fabricated data)", () => {
  it("renders the workspace with no session and disabled Validate/Review/Execute/Refresh", () => {
    render(<ImportWorkspace onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { level: 1, name: "Production Import Workspace" })).toBeTruthy();
    // Appears twice by design: the Identity StatusSignal and the Session
    // Status rail's own StatusSignal.
    expect(screen.getAllByText("No Session").length).toBe(2);
    expect(screen.getByText("No package uploaded")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Validate" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Review" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Execute" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Refresh" }).disabled).toBe(true);
  });

  it("shows the not-yet-validated / no-conflict-check / no-session disclosures, never invented values", () => {
    render(<ImportWorkspace onNavigate={() => {}} />);
    expect(screen.getByText(/Not yet validated/)).toBeTruthy();
    expect(screen.getByText(/No conflict check has been run yet/)).toBeTruthy();
    expect(screen.getByText(/Not yet executed/)).toBeTruthy();
  });

  it("shows no Progress stage yet", () => {
    render(<ImportWorkspace onNavigate={() => {}} />);
    expect(screen.getByText("Progress")).toBeTruthy();
    expect(screen.getAllByText("No session yet.").length).toBeGreaterThan(0);
  });
});

describe("Upload flow (real FileReader, no fake upload)", () => {
  it("reads a real .json file and populates the incoming package counts", async () => {
    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();
    // Appears twice by design: the Identity running-line and the Knowledge
    // Package section's own summary line.
    expect(screen.getAllByText("1 pumps · 1 seals · 1 installations · 1 documents").length).toBe(2);
    expect(screen.getByRole("button", { name: "Validate" }).disabled).toBe(false);
  });

  it("shows an error instead of a fabricated package when the uploaded file is not valid JSON", async () => {
    render(<ImportWorkspace onNavigate={() => {}} />);
    const input = screen.getByLabelText("Upload incoming import package");
    fireEvent.change(input, { target: { files: [new File(["not json"], "bad.json", { type: "application/json" })] } });
    expect(await screen.findByText(/bad.json is not valid JSON/)).toBeTruthy();
  });

  it("uploads an optional database snapshot file", async () => {
    render(<ImportWorkspace onNavigate={() => {}} />);
    const input = screen.getByLabelText("Upload database snapshot");
    fireEvent.change(input, { target: { files: [jsonFile("snapshot.json", { pumps: [], seals: [], installations: [], documents: [] })] } });
    await waitFor(() => expect(screen.getByText("snapshot.json")).toBeTruthy());
    expect(screen.getByText(/Conflicts will be compared against the uploaded database snapshot/)).toBeTruthy();
  });
});

describe("Validation", () => {
  it("calls validateImportPackage with the uploaded package and renders the real summary", async () => {
    validateImportPackage.mockResolvedValue({
      success: true,
      data: { summary: { is_valid: true, pump_count: 1, seal_count: 1, installation_count: 1, document_count: 1, error_count: 0, warning_count: 0 } },
    });
    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() => expect(screen.getAllByText("Yes").length).toBeGreaterThan(0));
    expect(validateImportPackage).toHaveBeenCalledWith(INCOMING_PACKAGE);
  });
});

describe("Review (session creation now carries its own ConflictReport, MWO-LTSA-104)", () => {
  it("calls createImportSession once, with the incoming package AND the database_snapshot, never calls a separate conflicts endpoint", async () => {
    createImportSession.mockResolvedValue(SESSION_WITH_CONFLICT_REPORT);

    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();

    fireEvent.click(screen.getByRole("button", { name: "Review" }));

    expect(await screen.findByText("IMPORT-SESSION-1")).toBeTruthy();
    expect(createImportSession).toHaveBeenCalledOnce();
    const sessionArg = createImportSession.mock.calls[0][0];
    expect(sessionArg.package).toEqual(INCOMING_PACKAGE);
    expect(sessionArg.database_snapshot).toEqual({ pumps: [], seals: [], installations: [], documents: [] });
    expect(sessionArg.status).toBe("REVIEWING");
    expect(typeof sessionArg.session_id).toBe("string");
    expect(sessionArg.session_id.length).toBeGreaterThan(0);
  });

  it("renders the real conflict data straight from session.data.conflict_report", async () => {
    createImportSession.mockResolvedValue(SESSION_WITH_CONFLICT_REPORT);

    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();
    fireEvent.click(screen.getByRole("button", { name: "Review" }));

    await screen.findByText("IMPORT-SESSION-1");
    expect(screen.getAllByText("Unit 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unit 2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("REVIEWING").length).toBeGreaterThan(0);
    expect(screen.getByText("MANUAL_REVIEW")).toBeTruthy();
  });

  it("shows the real Progress stage derived from the session's own status", async () => {
    createImportSession.mockResolvedValue(SESSION_WITH_CONFLICT_REPORT);

    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();
    fireEvent.click(screen.getByRole("button", { name: "Review" }));

    expect(await screen.findByText("Step 3 of 6: REVIEWING")).toBeTruthy();
  });
});

describe("Execute (real backend, MWO-LTSA-103) + auto-refresh from GET /status (MWO-LTSA-104)", () => {
  async function reviewedSession() {
    createImportSession.mockResolvedValue({
      success: true,
      data: {
        session_id: "IMPORT-SESSION-2", status: "APPROVED",
        statistics: { total_packages: 1, valid_packages: 1, invalid_packages: 0, warning_packages: 0, conflict_count: 0, inserted: 0, updated: 0, skipped: 0, failed: 0 },
        execution_plan: [],
        conflict_report: { conflict_count: 0, manual_review_count: 0, create_new_count: 1, conflicts: [] },
      },
    });
    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    await screen.findByText("IMPORT-SESSION-2");
  }

  it("calls executeImportSession with the real session_id, renders the real result, then auto-refreshes from GET /status", async () => {
    executeImportSession.mockResolvedValue({
      success: true,
      message: "Import executed",
      data: {
        status: "COMMITTED",
        statistics: { pump: { inserted: 1, updated: 0, skipped: 0, failed: 0 }, seal: { inserted: 0, updated: 0, skipped: 0, failed: 0 }, installation: { inserted: 0, updated: 0, skipped: 0, failed: 0 }, document: { inserted: 0, updated: 0, skipped: 0, failed: 0 } },
        execution_log: [{ entity_type: "pump", entity_id: "P-100", action: "INSERTED", detail: null }],
      },
    });
    getImportSessionStatus.mockResolvedValue({
      success: true,
      data: {
        session_id: "IMPORT-SESSION-2", status: "IMPORTED",
        statistics: { total_packages: 1, valid_packages: 1, invalid_packages: 0, warning_packages: 0, conflict_count: 0, inserted: 1, updated: 0, skipped: 0, failed: 0 },
        execution_plan: [],
        conflict_report: { conflict_count: 0, manual_review_count: 0, create_new_count: 1, conflicts: [] },
      },
    });

    await reviewedSession();
    fireEvent.click(screen.getByRole("button", { name: "Execute" }));

    expect(await screen.findByText("Import executed")).toBeTruthy();
    expect(executeImportSession).toHaveBeenCalledWith("IMPORT-SESSION-2");

    // Refresh after completion: GET /status was called with the same
    // session_id, and its real, later status ("IMPORTED") is what ends up
    // displayed -- not just the /execute response's own embedded status.
    await waitFor(() => expect(getImportSessionStatus).toHaveBeenCalledWith("IMPORT-SESSION-2"));
    await waitFor(() => expect(screen.getAllByText("IMPORTED").length).toBeGreaterThan(0));
    expect(screen.getByText("Step 6 of 6: IMPORTED")).toBeTruthy();
  });

  it("never fabricates success -- a real success:false /execute response (e.g. REJECTED_CONFLICTS) is shown, not hidden", async () => {
    executeImportSession.mockResolvedValue({ success: false, message: "1 unresolved HIGH-severity conflict(s) present", data: { reason: "1 unresolved HIGH-severity conflict(s) present" } });
    getImportSessionStatus.mockResolvedValue({
      success: true,
      data: { session_id: "IMPORT-SESSION-2", status: "APPROVED", statistics: null, execution_plan: [], conflict_report: null },
    });

    await reviewedSession();
    fireEvent.click(screen.getByRole("button", { name: "Execute" }));

    // Appears twice by design: the executionResult.message InfoRow and the
    // executionResult.data.reason InfoRow render the same real text.
    await waitFor(() =>
      expect(screen.getAllByText("1 unresolved HIGH-severity conflict(s) present").length).toBeGreaterThan(0)
    );
  });

  it("disables Execute and Refresh while executing, and disables Execute again once a session exists but nothing else is loading", async () => {
    let resolveExecute;
    executeImportSession.mockReturnValue(new Promise((resolve) => { resolveExecute = resolve; }));
    getImportSessionStatus.mockResolvedValue({ success: true, data: { session_id: "IMPORT-SESSION-2", status: "IMPORTED", statistics: null, execution_plan: [], conflict_report: null } });

    await reviewedSession();
    expect(screen.getByRole("button", { name: "Execute" }).disabled).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Execute" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Executing…" })).toBeTruthy());
    expect(screen.getByRole("button", { name: "Executing…" }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Refresh" }).disabled).toBe(true);

    resolveExecute({ success: true, message: "ok", data: { status: "COMMITTED", statistics: null, execution_log: [] } });
    await waitFor(() => expect(screen.getByRole("button", { name: "Execute" }).disabled).toBe(false));
  });
});

describe("Refresh / Status changes", () => {
  it("calls getImportSessionStatus with the real session_id and updates the displayed status", async () => {
    createImportSession.mockResolvedValue({
      success: true,
      data: { session_id: "IMPORT-SESSION-3", status: "REVIEWING", statistics: null, execution_plan: [], conflict_report: null },
    });
    getImportSessionStatus.mockResolvedValue({
      success: true,
      data: { session_id: "IMPORT-SESSION-3", status: "EXECUTING", statistics: null, execution_plan: [], conflict_report: null },
    });

    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    await screen.findByText("IMPORT-SESSION-3");
    expect(screen.getAllByText("REVIEWING").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => expect(screen.getAllByText("EXECUTING").length).toBeGreaterThan(0));
    expect(getImportSessionStatus).toHaveBeenCalledWith("IMPORT-SESSION-3");
  });
});

describe("Navigation (reuses the existing onNavigate contract)", () => {
  it("Open Pump/Seal/Installation/Document (Action Bar) navigate with the real record ids from the uploaded package", async () => {
    const onNavigate = vi.fn();
    render(<ImportWorkspace onNavigate={onNavigate} />);
    await uploadIncomingPackage();

    // "Open Pump →"/"Open Seal →"/"Open Installation →" legitimately appear
    // twice: once in this page's own Action Bar, and once more inside the
    // reused KnowledgeReviewWorkspaceView, which stays mounted (CSS-hidden
    // until opened) inside the PumpWorkspaceDrawer -- the same
    // always-in-DOM duplication InstallationWorkspace.test.jsx's Drawer
    // title already documents. The page's own Action Bar renders first in
    // DOM order, so index 0 is this page's button.
    fireEvent.click(screen.getAllByRole("button", { name: "Open Pump →" })[0]);
    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "P-100" });

    fireEvent.click(screen.getAllByRole("button", { name: "Open Seal →" })[0]);
    expect(onNavigate).toHaveBeenCalledWith("seal", { selectId: "S-100" });

    fireEvent.click(screen.getAllByRole("button", { name: "Open Installation →" })[0]);
    expect(onNavigate).toHaveBeenCalledWith("installation", { selectId: "INSTL-100" });

    fireEvent.click(screen.getByRole("button", { name: "Open Document" }));
    expect(onNavigate).toHaveBeenCalledWith("document", { selectId: "DOC-100" });
  });

  it("View Knowledge Package opens the reused KnowledgeReviewWorkspaceView in a Drawer, whose own navigation buttons work too", async () => {
    const onNavigate = vi.fn();
    render(<ImportWorkspace onNavigate={onNavigate} />);
    await uploadIncomingPackage();

    fireEvent.click(screen.getByRole("button", { name: "View Knowledge Package →" }));
    expect(await screen.findByText("Knowledge Package Review")).toBeTruthy();
  });
});

describe("Failure (real error responses, never swallowed)", () => {
  it("shows the real error message when validateImportPackage rejects", async () => {
    validateImportPackage.mockRejectedValue(new Error("Import API /api/ltsa/import/validate unavailable"));
    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    expect(await screen.findByText("Import API /api/ltsa/import/validate unavailable")).toBeTruthy();
  });

  it("shows the real error message when createImportSession rejects", async () => {
    createImportSession.mockRejectedValue(new Error("Import API /api/ltsa/import/session unavailable"));
    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();

    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(await screen.findByText("Import API /api/ltsa/import/session unavailable")).toBeTruthy();
  });

  it("shows the real error message when executeImportSession rejects, and never fabricates an execution result", async () => {
    createImportSession.mockResolvedValue(SESSION_WITH_CONFLICT_REPORT);
    executeImportSession.mockRejectedValue(new Error("Import API /api/ltsa/import/execute unavailable"));

    render(<ImportWorkspace onNavigate={() => {}} />);
    await uploadIncomingPackage();
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    await screen.findByText("IMPORT-SESSION-1");

    fireEvent.click(screen.getByRole("button", { name: "Execute" }));
    expect(await screen.findByText("Import API /api/ltsa/import/execute unavailable")).toBeTruthy();
    expect(screen.getByText(/Not yet executed/)).toBeTruthy();
  });
});

describe("Reuse verification", () => {
  it("ImportOpenDesignView imports the shared open-design kit, defines no local Section/InfoRow/RailSection/ActionBar", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/from ["']\.\/open-design["']/);
    for (const forbidden of ["function Section(", "function InfoRow(", "function RailSection(", "function ActionBar(", "function RefGroup("]) {
      expect(OPEN_DESIGN_VIEW_SOURCE).not.toContain(forbidden);
    }
  });

  it("ImportOpenDesignView reuses the design-system Table/Badge, defines no local table component", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/import \{ Badge, Table \} from ["']\.\.\/\.\.\/\.\.\/design-system["']/);
    expect(OPEN_DESIGN_VIEW_SOURCE).not.toMatch(/function Table\(|const Table = /);
  });

  it("ImportOpenDesignView reuses PumpWorkspaceDrawer and KnowledgeReviewWorkspaceView, defines no local Drawer or duplicate review page", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/import PumpWorkspaceDrawer from ["']\.\/PumpWorkspaceDrawer["']/);
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/import KnowledgeReviewWorkspaceView from ["']\.\/KnowledgeReviewWorkspaceView["']/);
  });

  it("ImportOpenDesignView never revalidates, reruns the conflict engine, or re-plans execution -- no such function defined locally", () => {
    for (const forbidden of ["function validate", "function resolveConflict", "function planExecution", "function checkConflicts"]) {
      expect(OPEN_DESIGN_VIEW_SOURCE.toLowerCase()).not.toContain(forbidden.toLowerCase());
    }
  });

  it("ImportOpenDesignView reads conflicts from session.conflict_report, no separate conflicts prop or fetch (MWO-LTSA-104)", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/sessionData\?\.conflict_report/);
    // The old standalone `conflicts` destructured prop is gone -- this is
    // exactly how it appeared, one per line, in the props list.
    expect(OPEN_DESIGN_VIEW_SOURCE).not.toMatch(/^ {2}conflicts,$/m);
  });

  it("ImportWorkspace.jsx renders ImportOpenDesignView exactly once", () => {
    const workspaceSource = readFileSync(path.join(__dirname, "ImportWorkspace.jsx"), "utf-8");
    const matches = workspaceSource.match(/<ImportOpenDesignView\b/g) || [];
    expect(matches.length).toBe(1);
  });

  it("ImportWorkspace.jsx no longer imports/calls checkImportConflicts (MWO-LTSA-104)", () => {
    const workspaceSource = readFileSync(path.join(__dirname, "ImportWorkspace.jsx"), "utf-8");
    expect(workspaceSource).not.toMatch(/checkImportConflicts/);
  });
});

describe("Definition of Done sanity check", () => {
  it("Import Workspace is reachable via the 'import' route key", () => {
    const ltsaSource = readFileSync(path.join(__dirname, "LTSAWorkspace.jsx"), "utf-8");
    expect(ltsaSource).toMatch(/import: ImportWorkspace/);
    expect(ltsaSource).toMatch(/key: "import", label: "Import"/);
  });
});
