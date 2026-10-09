import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DrawingViewerPanel from "../components/DrawingViewerPanel";
import DrawingMetadataPanel from "../components/DrawingMetadataPanel";
import DrawingLibraryPanel from "../components/DrawingLibraryPanel";
import KnowledgeDrawingSection from "../components/KnowledgeDrawingSection";
import DrawingWorkspace from "../pages/DrawingWorkspace";
import * as ai5rClient from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(() => Promise.resolve([
    { tag_number: "101-P-8A", area: "Area 01" },
    { tag_number: "101-P-8B", area: "Area 01" },
    { tag_number: "101-P-8C", area: "Area 01" },
    { tag_number: "211-P-26A", area: "Area 02" },
  ])),
  getDrawings: vi.fn(),
  getDrawing: vi.fn(),
  getDrawingContentBlob: vi.fn(),
  downloadDrawingFile: vi.fn(),
  getPumpKnowledge: vi.fn(() => Promise.resolve({ success: true, data: { drawings: [] } })),
  getSealCompatibility: vi.fn(() => Promise.resolve([])),
  getSeals: vi.fn(() => Promise.resolve([])),
  getDocuments: vi.fn(() => Promise.resolve([])),
}));

describe("LTSA Drawing Viewer UI (R9E Acceptance Suite)", () => {
  let createdUrls = [];
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    createdUrls = [];
    URL.createObjectURL = vi.fn((blob) => {
      const url = `blob:http://localhost/mock-blob-${Math.random().toString(36).substring(7)}`;
      createdUrls.push(url);
      return url;
    });
    URL.revokeObjectURL = vi.fn();
    vi.clearAllMocks();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  describe("Gate R9E.1 — DrawingViewerPanel Rendering & Security", () => {
    it("renders neutral notice for Reference-Only drawing without broken iframe or red alert", () => {
      const refDrawing = {
        id: "GA-214072-1",
        documentCode: "GA-214072-1",
        drawingNumber: "GA-214072-1",
        title: "GENERAL ARRANGEMENT 101-P-8A/B",
        storageAvailable: false,
        confidenceStatus: "CONFIRMED",
        drawingGeneration: "STANDARD",
        equipmentSide: null,
      };

      const { container } = render(<DrawingViewerPanel drawing={refDrawing} />);

      expect(screen.getByText("Drawing file not available")).toBeInTheDocument();
      expect(screen.getByText(/Authoritative drawing reference is confirmed/i)).toBeInTheDocument();
      expect(container.querySelector("iframe")).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();

      // Zero credential or private storage leaks
      expect(container.innerHTML).not.toContain("minio");
      expect(container.innerHTML).not.toContain("ltsa-drawings");
      expect(container.innerHTML).not.toContain("object_key");
    });

    it("renders authenticated iframe for PDF when storageAvailable is true", async () => {
      const mockBlob = new Blob(["%PDF-1.4 test binary"], { type: "application/pdf" });
      ai5rClient.getDrawingContentBlob.mockResolvedValueOnce({
        blob: mockBlob,
        url: "blob:http://localhost/test-pdf-blob",
        contentType: "application/pdf",
        filename: "GA-230821.pdf",
      });

      const pdfDrawing = {
        id: "GA-230821",
        documentCode: "GA-230821",
        drawingNumber: "GA-230821",
        title: "SEAL ARRANGEMENT DE",
        storageAvailable: true,
        contentType: "application/pdf",
        fileName: "GA-230821.pdf",
        fileSizeBytes: 1048576,
      };

      const { container } = render(<DrawingViewerPanel drawing={pdfDrawing} />);

      await waitFor(() => {
        expect(container.querySelector("iframe")).toBeInTheDocument();
      });

      const iframe = container.querySelector("iframe");
      expect(iframe.src).toContain("blob:http://localhost/test-pdf-blob");
      expect(ai5rClient.getDrawingContentBlob).toHaveBeenCalledWith("GA-230821");

      // Verify no direct MinIO URLs
      expect(iframe.src).not.toContain("9000");
      expect(iframe.src).not.toContain("minio");
    });

    it("renders img element for raster image drawings", async () => {
      const mockBlob = new Blob(["image data"], { type: "image/png" });
      ai5rClient.getDrawingContentBlob.mockResolvedValueOnce({
        blob: mockBlob,
        url: "blob:http://localhost/test-image-blob",
        contentType: "image/png",
        filename: "seal_dwg.png",
      });

      const imgDrawing = {
        id: "IMG-001",
        documentCode: "IMG-001",
        title: "Seal Section",
        storageAvailable: true,
        contentType: "image/png",
        fileName: "seal_dwg.png",
      };

      const { container } = render(<DrawingViewerPanel drawing={imgDrawing} />);

      await waitFor(() => {
        expect(container.querySelector("img")).toBeInTheDocument();
      });

      const img = container.querySelector("img");
      expect(img.src).toContain("blob:http://localhost/test-image-blob");
    });

    it("renders CAD binary card for DWG/DXF files", async () => {
      ai5rClient.getDrawingContentBlob.mockResolvedValueOnce({
        blob: new Blob(["dwg data"]),
        url: "blob:http://localhost/test-cad-blob",
        contentType: "application/acad",
        filename: "pump_model.dwg",
      });

      const cadDrawing = {
        id: "CAD-001",
        documentCode: "CAD-001",
        title: "CAD Model",
        storageAvailable: true,
        contentType: "application/acad",
        fileName: "pump_model.dwg",
      };

      render(<DrawingViewerPanel drawing={cadDrawing} />);

      await waitFor(() => {
        expect(screen.getByText("CAD Model")).toBeInTheDocument();
      });
      expect(screen.getByText(/pump_model\.dwg/i)).toBeInTheDocument();
      expect(screen.getByText(/Download CAD File/i)).toBeInTheDocument();
    });

    it("calls revokeObjectURL when unmounted to prevent memory leaks", async () => {
      ai5rClient.getDrawingContentBlob.mockResolvedValueOnce({
        blob: new Blob(["pdf data"], { type: "application/pdf" }),
        url: "blob:http://localhost/cleanup-test-blob",
        contentType: "application/pdf",
        filename: "doc.pdf",
      });

      const drawing = {
        id: "CLEAN-01",
        documentCode: "CLEAN-01",
        storageAvailable: true,
        contentType: "application/pdf",
      };

      const { unmount } = render(<DrawingViewerPanel drawing={drawing} />);

      await waitFor(() => {
        expect(ai5rClient.getDrawingContentBlob).toHaveBeenCalled();
      });

      unmount();
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:http://localhost/cleanup-test-blob");
    });

    it("triggers download action when download button is clicked", async () => {
      ai5rClient.getDrawingContentBlob.mockResolvedValueOnce({
        blob: new Blob(["pdf data"], { type: "application/pdf" }),
        url: "blob:http://localhost/download-test-blob",
        contentType: "application/pdf",
        filename: "GA-230821.pdf",
      });

      const linkClickSpy = vi.fn();
      const origCreate = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation((tag) => {
        const el = origCreate(tag);
        if (tag === "a") {
          el.click = linkClickSpy;
        }
        return el;
      });

      const drawing = {
        id: "GA-230821",
        documentCode: "GA-230821",
        storageAvailable: true,
        contentType: "application/pdf",
      };

      render(<DrawingViewerPanel drawing={drawing} />);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: "Download" }));
      expect(linkClickSpy).toHaveBeenCalled();
    });
  });

  describe("Gate R9E.2 — DrawingMetadataPanel Authoritative Fields", () => {
    it("renders DE side, revision, generation, and storage availability without leaking secrets", () => {
      const drawing = {
        id: "GA-230821",
        documentCode: "GA-230821",
        drawingNumber: "GA-230821",
        title: "SEAL ARRANGEMENT DE",
        drawingType: "DRAWING",
        equipmentTag: "211-P-26A",
        equipmentSide: "DE",
        drawingGeneration: "STANDARD",
        confidenceStatus: "CONFIRMED",
        evidenceMethod: "MANUAL_INGESTION",
        sealModel: "5620",
        apiPlan: "PLAN 53A",
        currentRevision: "B",
        status: "APPROVED",
        storageAvailable: true,
        fileName: "GA-230821_RevB.pdf",
        fileSizeBytes: 2097152, // 2.00 MB
      };

      const { container } = render(<DrawingMetadataPanel drawing={drawing} />);

      expect(screen.getByText("GA-230821")).toBeInTheDocument();
      expect(screen.getByText("SEAL ARRANGEMENT DE")).toBeInTheDocument();
      expect(screen.getByText("DE")).toBeInTheDocument();
      expect(screen.getByText("STANDARD")).toBeInTheDocument();
      expect(screen.getByText("CONFIRMED")).toBeInTheDocument();
      expect(screen.getByText("Archived in Storage")).toBeInTheDocument();
      expect(screen.getByText("2.00 MB")).toBeInTheDocument();
      expect(screen.getByText("GA-230821_RevB.pdf")).toBeInTheDocument();

      // Ensure no raw object_key or hashes are in DOM
      expect(container.innerHTML).not.toContain("object_key");
      expect(container.innerHTML).not.toContain("minio");
      expect(container.innerHTML).not.toContain("sha256");
    });

    it("renders Reference Only badge when storageAvailable is false", () => {
      const drawing = {
        id: "GA-214072-1",
        documentCode: "GA-214072-1",
        drawingNumber: "GA-214072-1",
        title: "GENERAL ARRANGEMENT 101-P-8A/B",
        equipmentTag: "101-P-8A",
        storageAvailable: false,
        confidenceStatus: "CONFIRMED",
      };

      render(<DrawingMetadataPanel drawing={drawing} />);
      expect(screen.getByText("Reference Only (No File)")).toBeInTheDocument();
    });
  });

  describe("Gate R9E.3 — DrawingLibraryPanel Side & Availability Badges", () => {
    it("renders DE/NDE side badges and FILE/REF indicators", () => {
      const drawings = [
        {
          id: "GA-230821",
          documentNumber: "GA-230821",
          title: "SEAL DE",
          equipmentTag: "211-P-26A",
          equipmentSide: "DE",
          storageAvailable: true,
          revisions: [{ current: true }],
        },
        {
          id: "GA-230826",
          documentNumber: "GA-230826",
          title: "SEAL NDE",
          equipmentTag: "211-P-26A",
          equipmentSide: "NDE",
          storageAvailable: false,
          revisions: [{ current: true }],
        },
      ];

      render(
        <DrawingLibraryPanel
          drawings={drawings}
          selectedDrawingId="GA-230821"
          onSelectDrawing={vi.fn()}
        />
      );

      expect(screen.getByText("DE")).toBeInTheDocument();
      expect(screen.getByText("NDE")).toBeInTheDocument();
      expect(screen.getByText("FILE")).toBeInTheDocument();
      expect(screen.getByText("REF")).toBeInTheDocument();
    });
  });

  describe("Gate R9E.4 — DrawingWorkspace Target Filtering & Deep Linking", () => {
    it("101-P-8A loads GA-214072-1 as confirmed reference-only drawing", async () => {
      ai5rClient.getDrawings.mockResolvedValueOnce([
        {
          document_code: "GA-214072-1",
          drawing_number: "GA-214072-1",
          title: "GENERAL ARRANGEMENT 101-P-8A/B",
          target_code: "101-P-8A",
          equipment_side: null,
          confidence_status: "CONFIRMED",
          evidence_method: "SYSTEM_OWNER_EXCEPTION",
          drawing_generation: "STANDARD",
          storage_available: false,
          status: "APPROVED",
        },
      ]);

      render(
        <DrawingWorkspace
          onNavigate={vi.fn()}
          navContext={{ assetTag: "101-P-8A" }}
        />
      );

      await waitFor(() => {
        expect(ai5rClient.getDrawings).toHaveBeenCalledWith({ targetCode: "101-P-8A" });
      });

      await waitFor(() => {
        expect(screen.getAllByText("GA-214072-1").length).toBeGreaterThan(0);
      });

      await waitFor(() => {
        expect(screen.getByText("Drawing file not available")).toBeInTheDocument();
      });
    });

    it("101-P-8C does NOT load GA-214072-1 (System-Owner Exception Rule)", async () => {
      ai5rClient.getDrawings.mockResolvedValueOnce([
        {
          document_code: "GA-320688",
          drawing_number: "GA-320688",
          title: "GA 101-P-8C PROPOSED",
          target_code: "101-P-8C",
          storage_available: true,
          status: "APPROVED",
        },
      ]);

      render(
        <DrawingWorkspace
          onNavigate={vi.fn()}
          navContext={{ assetTag: "101-P-8C" }}
        />
      );

      await waitFor(() => {
        expect(ai5rClient.getDrawings).toHaveBeenCalledWith({ targetCode: "101-P-8C" });
      });

      await waitFor(() => {
        expect(screen.getAllByText("GA-320688").length).toBeGreaterThan(0);
      });

      expect(screen.queryByText("GA-214072-1")).not.toBeInTheDocument();
    });

    it("211-P-26A independently displays GA-230821 (DE) and GA-230826 (NDE)", async () => {
      ai5rClient.getDrawings.mockResolvedValueOnce([
        {
          document_code: "GA-230821",
          drawing_number: "GA-230821",
          title: "SEAL DE",
          target_code: "211-P-26A",
          equipment_side: "DE",
          storage_available: true,
          status: "APPROVED",
        },
        {
          document_code: "GA-230826",
          drawing_number: "GA-230826",
          title: "SEAL NDE",
          target_code: "211-P-26A",
          equipment_side: "NDE",
          storage_available: true,
          status: "APPROVED",
        },
      ]);

      render(
        <DrawingWorkspace
          onNavigate={vi.fn()}
          navContext={{ assetTag: "211-P-26A" }}
        />
      );

      await waitFor(() => {
        expect(ai5rClient.getDrawings).toHaveBeenCalledWith({ targetCode: "211-P-26A" });
      });

      await waitFor(() => {
        expect(screen.getAllByText("GA-230821").length).toBeGreaterThan(0);
        expect(screen.getAllByText("GA-230826").length).toBeGreaterThan(0);
      });

      expect(screen.getAllByText("DE").length).toBeGreaterThan(0);
      expect(screen.getAllByText("NDE").length).toBeGreaterThan(0);
    });

    it("navContext.drawingId auto-selects specific drawing (Deep Linking)", async () => {
      ai5rClient.getDrawings.mockResolvedValueOnce([
        {
          document_code: "GA-230821",
          drawing_number: "GA-230821",
          title: "SEAL DE",
          target_code: "211-P-26A",
          equipment_side: "DE",
          storage_available: true,
        },
        {
          document_code: "GA-230826",
          drawing_number: "GA-230826",
          title: "SEAL NDE",
          target_code: "211-P-26A",
          equipment_side: "NDE",
          storage_available: true,
        },
      ]);

      render(
        <DrawingWorkspace
          onNavigate={vi.fn()}
          navContext={{ assetTag: "211-P-26A", drawingId: "GA-230826" }}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText("GA-230826").length).toBeGreaterThan(0);
      });

      // The metadata panel should display GA-230826's title and side NDE
      expect(screen.getAllByText("SEAL NDE").length).toBeGreaterThan(0);
      expect(screen.getAllByText("NDE").length).toBeGreaterThan(0);
    });
  });

  describe("Gate R9E.5 — KnowledgeDrawingSection Asset 360 Deep Link", () => {
    it("calls onOpenViewer callback when Buka Viewer button is clicked", () => {
      const onOpenViewer = vi.fn();
      const drawings = [
        {
          id: "GA-230821",
          documentNumber: "GA-230821",
          title: "SEAL DE",
          revision: "0",
          status: "APPROVED",
          uploadedAt: "2026-03-01",
        },
      ];

      render(<KnowledgeDrawingSection items={drawings} onOpenViewer={onOpenViewer} />);

      const button = screen.getByRole("button", { name: "Buka Viewer" });
      fireEvent.click(button);

      expect(onOpenViewer).toHaveBeenCalledWith(drawings[0]);
    });
  });
});
