import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SealOpenDesignView from "./SealOpenDesignView";

// R2B (Mechanical Seal Engineering Drawing + Revision BOM Real Read
// Path) -- component-level tests for the Drawings/BOM tabs, driven
// directly by props (mirroring how Seal.jsx already resolves and
// passes linkedDrawings/drawingBomGroups) rather than re-mocking the
// whole fetch chain here. Never asserts anything about real Postgres
// content -- these prove rendering/state logic only.

const SEAL = {
  code: "SC-101", sealId: "MS-JC-0101", name: "John Crane Type 21",
  type: "T48MP", manufacturer: "John Crane", model: null, shaftSize: 50,
  material: "Carbon/Silicon Carbide", temperatureLimit: 120, pressureLimit: 16,
  kimapPertamina: null, gpnJohnCrane: null, updatedAt: null, updatedBy: null,
  status: "ACTIVE", compatiblePumps: [], compatibleSeals: [], recommendation: null,
};

function openDrawingsTab() {
  fireEvent.click(screen.getByRole("tab", { name: "Drawings" }));
}

function openBomTab() {
  fireEvent.click(screen.getByRole("tab", { name: "BOM" }));
}

describe("Mechanical Seal Workspace -- Drawings tab (R2B)", () => {
  it("shows a loading state while linked drawings are being fetched", () => {
    render(<SealOpenDesignView seal={SEAL} linkedDrawingsLoading />);
    openDrawingsTab();

    expect(screen.getByTestId("seal-drawings-loading")).toBeTruthy();
  });

  it("shows an honest empty state when no drawing is linked to this seal", () => {
    render(<SealOpenDesignView seal={SEAL} linkedDrawings={[]} />);
    openDrawingsTab();

    expect(screen.getByTestId("seal-drawings-empty")).toBeTruthy();
    expect(screen.getByText(/no linked engineering drawings/i)).toBeTruthy();
  });

  it("shows an error state distinct from the empty state on fetch failure", () => {
    render(<SealOpenDesignView seal={SEAL} linkedDrawingsError="Engineering drawings could not be loaded." />);
    openDrawingsTab();

    expect(screen.getByTestId("seal-drawings-error")).toBeTruthy();
    expect(screen.queryByTestId("seal-drawings-empty")).toBeNull();
  });

  it("renders every real linked drawing with its number and current revision code", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        linkedDrawings={[
          { drawing_code: "DWG-1", drawing_number: "211-P-8A-SEAL-01", title: "Seal Assembly", current_revision_code: "REV-1" },
        ]}
      />
    );
    openDrawingsTab();

    expect(screen.getByText("Seal Assembly")).toBeTruthy();
    expect(screen.getByText(/211-P-8A-SEAL-01/)).toBeTruthy();
    expect(screen.getByText(/Rev REV-1/)).toBeTruthy();
  });

  it("never fabricates a row inside the drawings list when linkedDrawings is empty", () => {
    render(<SealOpenDesignView seal={SEAL} linkedDrawings={[]} />);
    openDrawingsTab();

    // Scoped to the Drawings tab's own list container -- the unrelated,
    // pre-existing "Buka Drawing" drawer (a different, Pump-scoped
    // feature, always present in the DOM at data-open="false") is
    // deliberately not asserted against here.
    const list = document.querySelector('[data-od-id="drawings-list"]');
    expect(list.textContent).not.toMatch(/Belum ada data drawing/i);
    expect(list.querySelectorAll(".part-item").length).toBe(0);
  });
});

describe("Mechanical Seal Workspace -- BOM tab (R2B, revision-scoped)", () => {
  it("shows 'No linked engineering drawings' when the seal has no linked drawing at all", () => {
    render(<SealOpenDesignView seal={SEAL} linkedDrawings={[]} drawingBomGroups={[]} />);
    openBomTab();

    expect(screen.getByTestId("seal-bom-empty-no-drawing")).toBeTruthy();
  });

  it("distinguishes 'drawing exists but no BOM' from 'no linked drawing'", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        linkedDrawings={[{ drawing_code: "DWG-1", title: "Seal Assembly", current_revision_code: "REV-1" }]}
        drawingBomGroups={[
          { drawing: { drawing_code: "DWG-1", title: "Seal Assembly" }, revision: { revision_code: "REV-1", revision: "A" }, bomLines: [] },
        ]}
      />
    );
    openBomTab();

    expect(screen.getByTestId("seal-bom-empty-no-lines")).toBeTruthy();
    expect(screen.queryByTestId("seal-bom-empty-no-drawing")).toBeNull();
  });

  it("shows a distinct state when a linked drawing has no current revision set", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        linkedDrawings={[{ drawing_code: "DWG-1", title: "Seal Assembly", current_revision_code: null }]}
        drawingBomGroups={[{ drawing: { drawing_code: "DWG-1", title: "Seal Assembly" }, revision: null, bomLines: [] }]}
      />
    );
    openBomTab();

    expect(screen.getByTestId("seal-bom-no-current-revision")).toBeTruthy();
  });

  it("renders real BOM lines (position/component/qty/material) for a revision that has them", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        linkedDrawings={[{ drawing_code: "DWG-1", title: "Seal Assembly", current_revision_code: "REV-1" }]}
        drawingBomGroups={[
          {
            drawing: { drawing_code: "DWG-1", title: "Seal Assembly" },
            revision: { revision_code: "REV-1", revision: "A" },
            bomLines: [
              { bom_line_code: "BOM-1", item_position: "10", component_description: "Rotating Face", component_id: "COMP-1", quantity: 1, material_or_specification: "Silicon Carbide" },
            ],
          },
        ]}
      />
    );
    openBomTab();

    expect(screen.getByText("Rotating Face")).toBeTruthy();
    expect(screen.getByText("Silicon Carbide")).toBeTruthy();
    expect(screen.getByText("10")).toBeTruthy();
  });

  it("never fabricates a GPN/part number -- always shows N/A, regardless of component_id", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        linkedDrawings={[{ drawing_code: "DWG-1", title: "Seal Assembly", current_revision_code: "REV-1" }]}
        drawingBomGroups={[
          {
            drawing: { drawing_code: "DWG-1", title: "Seal Assembly" },
            revision: { revision_code: "REV-1", revision: "A" },
            bomLines: [
              { bom_line_code: "BOM-1", item_position: "10", component_id: "COMP-JC-9999", quantity: 1, material_or_specification: "Steel" },
            ],
          },
        ]}
      />
    );
    openBomTab();

    // component_id is real and shown (as the component fallback), but a
    // GPN/part number is never derived from it -- N/A, not COMP-JC-9999
    // dressed up as a part number.
    expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
  });

  it("keeps BOM lines from different drawings in separate, non-flattened groups", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        linkedDrawings={[
          { drawing_code: "DWG-1", title: "Seal Assembly A", current_revision_code: "REV-1" },
          { drawing_code: "DWG-2", title: "Seal Assembly B", current_revision_code: "REV-9" },
        ]}
        drawingBomGroups={[
          {
            drawing: { drawing_code: "DWG-1", title: "Seal Assembly A" },
            revision: { revision_code: "REV-1", revision: "A" },
            bomLines: [{ bom_line_code: "BOM-1", item_position: "1", component_description: "Part A", quantity: 1, material_or_specification: "M1" }],
          },
          {
            drawing: { drawing_code: "DWG-2", title: "Seal Assembly B" },
            revision: { revision_code: "REV-9", revision: "C" },
            bomLines: [{ bom_line_code: "BOM-2", item_position: "1", component_description: "Part B", quantity: 2, material_or_specification: "M2" }],
          },
        ]}
      />
    );
    openBomTab();

    expect(screen.getByText("Seal Assembly A")).toBeTruthy();
    expect(screen.getByText("Seal Assembly B")).toBeTruthy();
    expect(screen.getByText("Revision A")).toBeTruthy();
    expect(screen.getByText("Revision C")).toBeTruthy();
    expect(screen.getByText("Part A")).toBeTruthy();
    expect(screen.getByText("Part B")).toBeTruthy();
  });
});

describe("Mechanical Seal Workspace -- R2A Documents tab still works (R2B regression check)", () => {
  it("still renders real documents grouped by type, unaffected by the new Drawings/BOM tabs", () => {
    render(
      <SealOpenDesignView
        seal={SEAL}
        documents={[{ id: "DOC-1", title: "Datasheet", documentType: "DATASHEET", documentNumber: "DS-1", sealCode: "SC-101" }]}
      />
    );
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));

    expect(screen.getByText("Datasheet")).toBeTruthy();
    expect(screen.getByText("DATASHEET")).toBeTruthy();
  });
});
