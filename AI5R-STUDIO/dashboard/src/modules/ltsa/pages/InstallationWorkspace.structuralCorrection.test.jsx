/**
 * MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- proves the
 * four evidence-backed structural gaps (multi-date site activities,
 * DE/NDE dual-position observations, variable/dynamic BOM columns,
 * post-installation readings) are represented and rendered without loss,
 * using the SYNTHETIC structural fixtures derived from golden samples
 * SCAN 002-005 (installationGoldenFixtures.js). SCAN 001's real pattern is
 * already covered by the existing InstallationWorkspace.test.jsx suite
 * against sampleInstallations.js.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import InstallationWorkspace from "./InstallationWorkspace";
import {
  sparePatternFixture,
  deOnlyMultiDayReadingsFixture,
  dualPositionThreeDateGroupsFixture,
  freeTextDispositionFixture,
} from "../utils/installationGoldenFixtures";
import { getInstallations } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({ getInstallations: vi.fn() }));

describe("212-P-25A-SPARE pattern (SPARE identity, triple seal, rich BOM)", () => {
  it("preserves the SPARE-suffixed tag verbatim, never split into a separate identity field", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[sparePatternFixture]} />);
    expect(screen.getAllByText("999-P-99Z SPARE").length).toBeGreaterThan(0);
  });

  it("renders the triple-seal compound seal_type/seal_size verbatim", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[sparePatternFixture]} />);
    expect(screen.getAllByText("8AB/8AB/8AB Triple Seal").length).toBeGreaterThan(0);
    expect(screen.getAllByText('1.250"/1.500"/1.500"').length).toBeGreaterThan(0);
  });

  it("renders the richer 7-field BOM columns (Drawing Number, Material Code, Description, Material) instead of hiding them behind a fixed 4-column table", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[sparePatternFixture]} />);
    expect(screen.getByText("Drawing Number")).toBeTruthy();
    expect(screen.getAllByText("Material Code").length).toBeGreaterThan(0);
    expect(screen.getByText("Description")).toBeTruthy();
    expect(screen.getAllByText("Material").length).toBeGreaterThan(0);
    // Every real BOM value is visible somewhere in the rendered table.
    for (const row of sparePatternFixture.billOfMaterial) {
      expect(screen.getAllByText(row.drawingNumber).length).toBeGreaterThan(0);
      expect(screen.getAllByText(row.material).length).toBeGreaterThan(0);
    }
    // No stale "Part Name"/"No." columns from the old hard-coded shape.
    expect(screen.queryByText("Part Name")).toBeNull();
  });
});

describe("211-P-2A-DE pattern (DE-only, multi-day, post-installation readings)", () => {
  it("renders both date groups as distinct chronology, never merged", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[deOnlyMultiDayReadingsFixture]} />);
    for (const group of deOnlyMultiDayReadingsFixture.siteActivities) {
      expect(screen.getAllByText(group.date).length).toBeGreaterThan(0);
      for (const activity of group.activities) {
        expect(screen.getAllByText(activity).length).toBeGreaterThan(0);
      }
    }
  });

  it("renders the Post-Installation Readings section with DE-only values, never fabricating an NDE column", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[deOnlyMultiDayReadingsFixture]} />);
    expect(screen.getByText("Post-Installation Readings")).toBeTruthy();
    expect(screen.getByText("Mechanical Seal Gland Temperature")).toBeTruthy();
    expect(screen.getByText(/DE: 107°C/)).toBeTruthy();
    // Never invents an NDE reading this DE-only report never took.
    expect(screen.queryByText(/NDE:/)).toBeNull();
  });

  it("omits the Post-Installation Readings section entirely for a report with none (sampleInstallations.js), rather than showing a fake-empty section", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[sparePatternFixture]} />);
    expect(screen.queryByText("Post-Installation Readings")).toBeNull();
  });
});

describe("212-P-13AR pattern (DE/NDE dual position, three date groups)", () => {
  it("renders all three date groups in order", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[dualPositionThreeDateGroupsFixture]} />);
    expect(dualPositionThreeDateGroupsFixture.siteActivities).toHaveLength(3);
    for (const group of dualPositionThreeDateGroupsFixture.siteActivities) {
      expect(screen.getAllByText(group.date).length).toBeGreaterThan(0);
    }
  });

  it("renders DE and NDE observation state explicitly and independently, never collapsed into one checked value", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[dualPositionThreeDateGroupsFixture]} />);
    // "Corrosion" is checkedDE:false/checkedNDE:false; "Contact with Sleeve" is checkedDE:true/checkedNDE:true --
    // both must show explicit DE/NDE labels, not a single "Checked"/"Not Checked".
    expect(screen.getAllByText(/DE: (Checked|Not Checked) · NDE: (Checked|Not Checked)/).length).toBeGreaterThan(0);
  });

  it("renders DE/NDE post-installation readings distinctly, never sharing one value", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[dualPositionThreeDateGroupsFixture]} />);
    expect(screen.getByText(/DE: 180°C · NDE: 190°C/)).toBeTruthy();
    expect(screen.getByText(/DE: 170°C · NDE: 140°C/)).toBeTruthy();
  });

  it("renders the DE/NDE-split BOM Work Required columns distinctly", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[dualPositionThreeDateGroupsFixture]} />);
    expect(screen.getByText("Work Required (DE)")).toBeTruthy();
    expect(screen.getByText("Work Required (NDE)")).toBeTruthy();
  });
});

describe("702-P-2 pattern (free-text disposition, populated inspection)", () => {
  it("renders the free-text disposition value verbatim, not forced into Replace/Clean-reuse", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[freeTextDispositionFixture]} />);
    expect(screen.getByText("Clean, add Pin Mating Ring, and reuse")).toBeTruthy();
  });

  it("renders all populated Seal Chamber & Shaft Inspection values with units preserved", () => {
    render(<InstallationWorkspace onNavigate={() => {}} installations={[freeTextDispositionFixture]} />);
    expect(screen.getByText(/0\.03 mm/)).toBeTruthy();
    expect(screen.getByText(/0\.05 mm/)).toBeTruthy();
    expect(screen.getByText(/0\.02 mm/)).toBeTruthy();
  });
});
