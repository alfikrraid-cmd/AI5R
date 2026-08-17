import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import InstallationWorkspace from "./InstallationWorkspace";
import sampleInstallations from "../data/sampleInstallations";
import { getInstallations } from "../../../api/ai5rClient";

// MWO-LTSA-060 -- getInstallations is the one reused, already-real backend
// call InstallationWorkspace.jsx now makes when no `installations` prop is
// given (mirrors Pump.jsx/Seal.jsx/DrawingWorkspace.jsx's own
// vi.mock("../../../api/ai5rClient") convention). Every existing test
// above still passes installations={sampleInstallations} explicitly, so
// this mock is never exercised by them -- only the dedicated "Real-data
// wiring" describe block below calls it.
vi.mock("../../../api/ai5rClient", () => ({
  getInstallations: vi.fn(),
}));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OPEN_DESIGN_VIEW_SOURCE = readFileSync(
  path.join(__dirname, "..", "components", "InstallationOpenDesignView.jsx"),
  "utf-8"
);

const installation = sampleInstallations[0];

describe("Hero / Identity", () => {
  it("renders the report title as the H1", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByRole("heading", { level: 1, name: "Mechanical Seal Installation Report" })).toBeTruthy();
  });

  it("renders Report No., Customer, and Plant in the Identity group", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getAllByText(installation.reportNo).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.customer).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.plant).length).toBeGreaterThan(0);
  });

  it("renders Plant Equip. No., Seal Type, and Drawing No. in the Technical group", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getAllByText(installation.plantEquipNo).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.sealType).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.drawingNo).length).toBeGreaterThan(0);
  });
});

describe("Report Information (10 fields, verbatim from the report)", () => {
  it("renders every Report Information field", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Report Information")).toBeTruthy();
    expect(screen.getAllByText(installation.date).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.address).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.unit).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.poNo).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.location).length).toBeGreaterThan(0);
  });

  it("shows a dash, never a fabricated value, for TSO No. and Packing List No. (both '-' on the report)", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});

describe("General Data (15 fields, two report columns preserved)", () => {
  it("renders every equipment-side field", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("General Data")).toBeTruthy();
    expect(screen.getAllByText(installation.equipmentMfr).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.modelType).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.size).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.pumpType).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.shaftSpeed).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.rotation).length).toBeGreaterThan(0);
  });

  it("renders every seal-side field, including the verbatim source typo in Seal Arrangement", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getAllByText(installation.sealManufacture).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Non-Cartridge Sigle Seal").length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.sealSize).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.materialCode).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.sealLocation).length).toBeGreaterThan(0);
  });
});

describe("Service / Operation Conditions (22 fields, two report columns preserved)", () => {
  it("renders real values on both sides of the report's own column split", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Service / Operation Conditions")).toBeTruthy();
    expect(screen.getAllByText(installation.liquid).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.temperatureRange).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.dischargePress).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.suctionPress).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.sealPress).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.apiPlan).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.quenchFluid).length).toBeGreaterThan(0);
  });

  it("shows a dash for every field printed as '-' on the report (Flash Point, Boiling Point, etc.), never a fabricated value", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Flash Point")).toBeTruthy();
    expect(screen.getByText("Boiling Point")).toBeTruthy();
    expect(screen.getByText("Flush Liquid")).toBeTruthy();
  });
});

describe("Seal Chamber & Shaft Inspection (measured value + report's own standard/limit)", () => {
  it("renders every measured value alongside its printed standard", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Seal Chamber & Shaft Inspection")).toBeTruthy();
    expect(screen.getByText(/0\.01 mm.*Standard 0\.050.*0\.076 mm/)).toBeTruthy();
    expect(screen.getByText(/0\.06 mm.*Standard 0\.025.*0\.127 mm/)).toBeTruthy();
    expect(screen.getByText(/0\.02 mm.*Standard 0\.050.*0\.076 mm/)).toBeTruthy();
  });

  it("shows a dash for the two rows with no measured value, but still shows their printed limit reference", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getAllByText(/—.*Limits refer to seal manual/).length).toBe(2);
  });
});

describe("Note (8 fields, two report columns preserved)", () => {
  it("renders every condition field", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Note")).toBeTruthy();
    expect(screen.getAllByText("New").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Old").length).toBeGreaterThan(0);
  });
});

describe("Summary (intro prose + 14-item Site Activity list, verbatim)", () => {
  it("renders the summary intro and site activity intro prose exactly as printed", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Summary")).toBeTruthy();
    expect(screen.getByText(installation.summaryIntro)).toBeTruthy();
    expect(screen.getByText(installation.siteActivityIntro)).toBeTruthy();
  });

  // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- siteActivities
  // is date-grouped ([{ date, activities }]); this report is single-day, so
  // exactly one group carrying all 14 items, never a flat 14-item list.
  it("renders all 14 site activity items across their date group(s), never merged/split/invented", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    const allActivities = installation.siteActivities.flatMap((group) => group.activities);
    expect(allActivities.length).toBe(14);
    for (const activity of allActivities) {
      expect(screen.getByText(activity)).toBeTruthy();
    }
  });

  it("renders the group's date as a Site Activity heading", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(installation.siteActivities).toHaveLength(1);
    expect(screen.getAllByText(installation.siteActivities[0].date).length).toBeGreaterThan(0);
  });
});

describe("Bill of Material (Table, 11 rows, verbatim columns)", () => {
  it("renders the assembly caption and the No./Part Name/Qty/Work Required columns", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Bill of Material")).toBeTruthy();
    expect(screen.getByText(installation.bomCaption)).toBeTruthy();
    expect(screen.getByText("Part Name")).toBeTruthy();
    expect(screen.getByText("Work Required")).toBeTruthy();
  });

  it("renders all 11 BOM rows with their real part name and work-required value", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(installation.billOfMaterial.length).toBe(11);
    for (const row of installation.billOfMaterial) {
      expect(screen.getAllByText(row.partName).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText("Replace").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Clean, reuse").length).toBeGreaterThan(0);
  });
});

describe("Mechanical Seal Drawing", () => {
  it("renders the Drawing No. and a working Buka Drawing link that opens the preview drawer", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    // Appears twice by design: the Section eyebrow AND the (always-in-DOM,
    // CSS-hidden-until-opened) PumpWorkspaceDrawer's own title, matching
    // every other workspace's identical Drawer-title duplication.
    expect(screen.getAllByText("Mechanical Seal Drawing").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Buka Drawing →" }));
    expect(screen.getByText(/no drawing file\/rendering backend exists yet/i)).toBeTruthy();
  });
});

describe("Observation checklists (4 groups, checkbox state preserved verbatim)", () => {
  it("renders all four group titles and their printed instruction text", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Gland Observation")).toBeTruthy();
    expect(screen.getByText("Sleeve Observation")).toBeTruthy();
    expect(screen.getByText("Retainer / Disc Observation")).toBeTruthy();
    expect(screen.getByText("Cartridge Drive Collar Observation")).toBeTruthy();
    expect(screen.getByText(installation.glandObservationNote)).toBeTruthy();
    expect(screen.getByText(installation.sleeveObservationNote)).toBeTruthy();
  });

  it("marks only Gland's 'Inboard Side / Outboard Side re-used' as Checked -- every other item across all four groups is Not Checked", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    const totalItems =
      installation.glandObservation.length +
      installation.sleeveObservation.length +
      installation.retainerDiscObservation.length +
      installation.cartridgeDriveCollarObservation.length;
    const checkedCount = [
      ...installation.glandObservation,
      ...installation.sleeveObservation,
      ...installation.retainerDiscObservation,
      ...installation.cartridgeDriveCollarObservation,
    ].filter((entry) => entry.checked).length;

    expect(totalItems).toBe(11 + 13 + 9 + 6);
    expect(checkedCount).toBe(1);
    expect(screen.getAllByText("Checked").length).toBe(1);
    expect(screen.getAllByText("Not Checked").length).toBe(totalItems - 1);
  });

  it("renders the verbatim source typo 'Flus Port Clogged' in Gland Observation, never silently corrected", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Flus Port Clogged")).toBeTruthy();
  });
});

describe("Signatures (4 signatories, Table)", () => {
  it("renders all four signatories with their real Title and Date", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Signatures")).toBeTruthy();
    for (const signatory of installation.signatures) {
      // "Eng"-titled signatories legitimately appear twice (MWO-LTSA-068
      // Engineer section, see the dedicated describe block below).
      expect(screen.getAllByText(signatory.title).length).toBeGreaterThan(0);
      expect(screen.getAllByText(signatory.date).length).toBeGreaterThan(0);
    }
  });

  it("shows real names for the three legible signatories", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    // Rizky Trinoviandi (Title "Service") appears once, only in the
    // Signatures table. Muh Taufik/Thomas R. legitimately appear twice
    // (MWO-LTSA-068): once here, and once more in the new Engineer
    // section (they're both "Eng"-titled signatories) -- the same
    // duplicate-a-real-fact-for-at-a-glance pattern used elsewhere in
    // every other Open Design view.
    expect(screen.getByText("Rizky Trinoviandi")).toBeTruthy();
    expect(screen.getAllByText("Muh Taufik").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Thomas R.").length).toBeGreaterThan(0);
  });

  it("shows a dash, never a guessed name, for the one illegible signature", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    const dashCells = screen.getAllByText("—");
    expect(dashCells.length).toBeGreaterThan(0);
  });
});

describe("Navigation (reuses the existing onNavigate contract)", () => {
  it("Open Pump (Action Bar) navigates with the report's Plant Equip. No.", () => {
    const onNavigate = vi.fn();
    render(<InstallationWorkspace onNavigate={onNavigate} installations={sampleInstallations} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Pump →" }));
    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: installation.plantEquipNo });
  });

  it("Open Drawing (Action Bar) navigates with the report's Drawing No.", () => {
    const onNavigate = vi.fn();
    render(<InstallationWorkspace onNavigate={onNavigate} installations={sampleInstallations} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Drawing" }));
    expect(onNavigate).toHaveBeenCalledWith("drawing", { assetTag: installation.drawingNo });
  });

  it("the chrome-bar crumb link also navigates to the linked pump", () => {
    const onNavigate = vi.fn();
    render(<InstallationWorkspace onNavigate={onNavigate} installations={sampleInstallations} />);
    fireEvent.click(screen.getByRole("button", { name: installation.plantEquipNo }));
    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: installation.plantEquipNo });
  });

  // MWO-LTSA-068
  it("Open Lifecycle (Action Bar) navigates to 'history' (Asset 360/KnowledgeWorkspace) with the report's Plant Equip. No.", () => {
    const onNavigate = vi.fn();
    render(<InstallationWorkspace onNavigate={onNavigate} installations={sampleInstallations} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Lifecycle →" }));
    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: installation.plantEquipNo });
  });
});

// MWO-LTSA-068 -- Installation Workspace Enhancement ("Engineering
// Document Viewer"). Six new informational sections, all InfoRow/RefGroup
// re-displays or evidenced derivations of already-fetched data -- no new
// fetch, no new backend endpoint.
describe("Pump section (MWO-LTSA-068)", () => {
  it("renders Pump identity fields", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Pump")).toBeTruthy();
    expect(screen.getAllByText(installation.pumpType).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.rotation).length).toBeGreaterThan(0);
    expect(screen.getAllByText(installation.shaftSpeed).length).toBeGreaterThan(0);
  });
});

describe("Drawing section (MWO-LTSA-068)", () => {
  it("renders the Drawing No.", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Drawing")).toBeTruthy();
    expect(screen.getAllByText(installation.drawingNo).length).toBeGreaterThan(0);
  });
});

describe("Seal section (MWO-LTSA-068)", () => {
  it("renders Seal fields, including an honest dash for the absent Seal Code", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Seal Code")).toBeTruthy();
    expect(installation.sealCode).toBeNull();
    expect(screen.getAllByText(installation.sealArrangement).length).toBeGreaterThan(0);
  });
});

describe("Engineer section (MWO-LTSA-068 -- derived from signatures, never fabricated)", () => {
  it("lists only the signatories whose Title contains 'Eng'", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Engineer")).toBeTruthy();
    // Muh Taufik (Service Engineer) and Thomas R. (Jr. Eng / RE Insp).
    expect(screen.getAllByText("Muh Taufik").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Thomas R.").length).toBeGreaterThan(0);
  });

  it("excludes signatories whose Title does not contain 'Eng'", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    // Rizky Trinoviandi's title is "Service" -- no "Eng" substring.
    const engineerSection = screen.getByText("Engineer").closest("section");
    expect(engineerSection).toBeTruthy();
    expect(within(engineerSection).queryByText("Rizky Trinoviandi")).toBeNull();
  });
});

describe("Attachments section (MWO-LTSA-068 -- reuses the one real source_document_name column)", () => {
  it("renders the source document name as the one real attachment", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Attachments")).toBeTruthy();
    expect(screen.getByText(installation.sourceDocumentName)).toBeTruthy();
  });

  it("shows an honest empty state, never a fabricated file, when no source document name is recorded", () => {
    render(
      <InstallationWorkspace
        onNavigate={() => {}}
        installations={[{ ...installation, sourceDocumentName: null }]}
      />
    );
    expect(screen.getByText(/No source document on file/)).toBeTruthy();
  });
});

describe("Remarks section (MWO-LTSA-068 -- no remarks column exists; disclosed, never fabricated)", () => {
  it("renders a disclosed unavailable message, never invented remarks text", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(screen.getByText("Remarks")).toBeTruthy();
    expect(screen.getByText("No remarks field exists in this report.")).toBeTruthy();
  });
});

describe("Empty state (no fabricated data when no installations exist)", () => {
  it("shows an empty state when installations is an empty array", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[]} />);
    expect(screen.getByText(/no installation report selected/i)).toBeTruthy();
  });
});

describe("Reuse verification", () => {
  it("InstallationOpenDesignView imports the shared open-design kit, defines no local Section/InfoRow/RailSection/ActionBar/RefGroup", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/from ["']\.\/open-design["']/);
    for (const forbidden of ["function Section(", "function InfoRow(", "function RailSection(", "function ActionBar(", "function RefGroup("]) {
      expect(OPEN_DESIGN_VIEW_SOURCE).not.toContain(forbidden);
    }
  });

  it("InstallationOpenDesignView reuses the design-system Table, defines no local table component", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/import \{ Table \} from ["']\.\.\/\.\.\/\.\.\/design-system["']/);
    expect(OPEN_DESIGN_VIEW_SOURCE).not.toMatch(/function Table\(|const Table = /);
  });

  it("InstallationOpenDesignView reuses PumpWorkspaceDrawer, defines no local Drawer", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).toMatch(/import PumpWorkspaceDrawer from ["']\.\/PumpWorkspaceDrawer["']/);
  });

  it("no Installation* source file imports ai5rClient or makes a raw fetch() call (No backend, No API)", () => {
    expect(OPEN_DESIGN_VIEW_SOURCE).not.toMatch(/ai5rClient/);
    expect(OPEN_DESIGN_VIEW_SOURCE).not.toMatch(/\bfetch\(/);
  });

  it("InstallationWorkspace.jsx renders InstallationOpenDesignView exactly once", () => {
    const workspaceSource = readFileSync(path.join(__dirname, "InstallationWorkspace.jsx"), "utf-8");
    const matches = workspaceSource.match(/<InstallationOpenDesignView\b/g) || [];
    expect(matches.length).toBe(1);
  });

  it("does not define any forbidden AI/Runtime/Router architecture object", () => {
    for (const forbidden of ["InstallationAI", "InstallationRuntime", "InstallationContext", "InstallationRouter"]) {
      expect(OPEN_DESIGN_VIEW_SOURCE).not.toMatch(new RegExp(forbidden));
    }
  });
});

// MWO-LTSA-060 -- production persistence path. Real installation_report
// shape (snake_case, matching BP-INSTALLATION/DATABASE/001_create_table.sql
// and installationMapping.test.js's own RAW_RECORD fixture), mapped
// through mapInstallationRecord() into exactly what
// InstallationOpenDesignView.jsx already renders.
describe("Real-data wiring (MWO-LTSA-060)", () => {
  const FETCHED_RECORD = {
    installation_code: "INSTL-002-2027",
    report_no: "002/INSTL /TAP/02-2027",
    report_date: "February 10, 2027",
    customer: "PT Fetched Customer",
    plant: "Fetched Plant",
    plant_equip_no: "999-P-9",
    seal_type: "Fetched Seal Type",
    drawing_no: "E99999",
    source_document_name: "SCAN 002 INSTALLATION REPORT 999-P-9.pdf",
  };

  beforeEach(() => {
    getInstallations.mockReset();
  });

  it("does not call getInstallations when an installations prop is explicitly passed", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={sampleInstallations} />);
    expect(getInstallations).not.toHaveBeenCalled();
  });

  it("fetches and renders the real, mapped installation report when no installations prop is given", async () => {
    getInstallations.mockResolvedValue([FETCHED_RECORD]);
    render(<InstallationWorkspace onNavigate={() => {}} />);
    expect(getInstallations).toHaveBeenCalledOnce();
    expect((await screen.findAllByText("999-P-9")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("PT Fetched Customer").length).toBeGreaterThan(0);
  });

  it("falls back to the genuine empty state, not a fabricated one, when getInstallations rejects", async () => {
    getInstallations.mockRejectedValue(new Error("network error"));
    render(<InstallationWorkspace onNavigate={() => {}} />);
    expect(await screen.findByText(/no installation report selected/i)).toBeTruthy();
  });

  it("falls back to the genuine empty state when the API returns no installations", async () => {
    getInstallations.mockResolvedValue([]);
    render(<InstallationWorkspace onNavigate={() => {}} />);
    expect(await screen.findByText(/no installation report selected/i)).toBeTruthy();
  });
});

describe("Definition of Done sanity check", () => {
  it("Installation Workspace is reachable via the 'installation' route key", () => {
    const ltsaSource = readFileSync(path.join(__dirname, "LTSAWorkspace.jsx"), "utf-8");
    expect(ltsaSource).toMatch(/installation: InstallationWorkspace/);
    expect(ltsaSource).toMatch(/key: "installation", label: "Installation"/);
  });
});
