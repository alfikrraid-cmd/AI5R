import { useEffect, useState } from "react";
import { Badge, Card, PageHeader } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import DrawingLibraryPanel from "../components/DrawingLibraryPanel";
import DrawingViewerPanel from "../components/DrawingViewerPanel";
import DrawingMetadataPanel from "../components/DrawingMetadataPanel";
import DrawingRevisionPanel from "../components/DrawingRevisionPanel";
import DrawingNavigationPanel from "../components/DrawingNavigationPanel";
import DrawingHealthCard from "../components/DrawingHealthCard";
import SealComponentNavigator from "../components/SealComponentNavigator";
import OEMKnowledgePanel from "../components/OEMKnowledgePanel";
import DrawingBomTable from "../components/DrawingBomTable";
import DrawingFutureCapabilitiesPanel from "../components/DrawingFutureCapabilitiesPanel";
import DrawingIntelligencePanel from "../components/DrawingIntelligencePanel";
import PumpTagSelector from "../components/PumpTagSelector";
import { getPumps, getDrawings, getPumpKnowledge, getSealCompatibility, getSeals, getDocuments } from "../../../api/ai5rClient";
import { mapDrawingRecord } from "../utils/drawingMapping";
import { resolveCompatibleSeals } from "../utils/sealMapping";
import "./DrawingWorkspace.css";

/**
 * LTSA Drawing Workspace (R9E).
 * Exposes authoritative engineering drawings for pumps via the Drawing API.
 * Supports active pump selection, deep-linking via navContext, side badges (DE/NDE),
 * reference-only handling, and authenticated content viewing/downloading.
 */
export default function DrawingWorkspace({ onNavigate, navContext, drawings: drawingsProp }) {
  const [activeTag, setActiveTag] = useState(navContext?.assetTag ?? null);
  const [pumps, setPumps] = useState([]);
  const [pumpsLoading, setPumpsLoading] = useState(false);
  const [pumpsError, setPumpsError] = useState(null);

  const [fetchedDrawings, setFetchedDrawings] = useState([]);
  const drawings = drawingsProp ?? fetchedDrawings;

  const [selectedDrawingId, setSelectedDrawingId] = useState(drawings[0]?.id ?? null);
  const [openedRevision, setOpenedRevision] = useState(null);

  const selectedDrawing = drawings.find((drawing) => drawing.id === selectedDrawingId) ?? null;

  useEffect(() => {
    let active = true;
    setPumpsLoading(true);
    getPumps()
      .then((items) => {
        if (active) setPumps(items || []);
      })
      .catch((err) => {
        if (active) setPumpsError(err);
      })
      .finally(() => {
        if (active) setPumpsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (navContext?.assetTag && navContext.assetTag !== activeTag) {
      setActiveTag(navContext.assetTag);
    }
  }, [navContext?.assetTag]);

  useEffect(() => {
    if (drawingsProp) {
      return;
    }

    if (!activeTag) {
      setFetchedDrawings([]);
      return;
    }

    let active = true;

    Promise.all([
      getDrawings({ targetCode: activeTag }).catch(() => []),
      getPumpKnowledge(activeTag).catch(() => null),
      getSealCompatibility().catch(() => []),
      getSeals().catch(() => []),
      getDocuments().catch(() => []),
    ])
      .then(([drawingRecords, knowledgeResponse, compatibilityRecords, sealRecords, documentRecords]) => {
        if (!active) {
          return;
        }

        const compatibleSealCodes = resolveCompatibleSeals(activeTag, compatibilityRecords || []);

        const sealModel =
          (compatibleSealCodes || [])
            .map((sealCode) => (sealRecords || []).find((seal) => seal.seal_code === sealCode)?.model)
            .filter(Boolean)
            .join(", ") || null;

        const relatedDocuments = (documentRecords || []).filter(
          (document) =>
            document.document_type !== "DRAWING" && compatibleSealCodes.includes(document.seal_code)
        );

        const records =
          drawingRecords && drawingRecords.length > 0
            ? drawingRecords
            : knowledgeResponse?.data?.drawings ?? [];

        const mapped = records.map((record) =>
          mapDrawingRecord(record, activeTag, { sealModel, relatedDocuments })
        );

        setFetchedDrawings(mapped);

        let targetId = mapped[0]?.id ?? null;
        if (navContext?.drawingId) {
          const matched = mapped.find(
            (d) =>
              d.id === navContext.drawingId ||
              d.documentCode === navContext.drawingId ||
              d.drawingNumber === navContext.drawingId
          );
          if (matched) {
            targetId = matched.id;
          }
        }
        setSelectedDrawingId(targetId);
      })
      .catch(() => {
        if (active) {
          setFetchedDrawings([]);
          setSelectedDrawingId(null);
        }
      });

    return () => {
      active = false;
    };
  }, [drawingsProp, activeTag, navContext?.drawingId]);

  useEffect(() => {
    setSelectedDrawingId((current) => {
      if (navContext?.drawingId) {
        const found = drawings.find(
          (d) =>
            d.id === navContext.drawingId ||
            d.documentCode === navContext.drawingId ||
            d.drawingNumber === navContext.drawingId
        );
        if (found) return found.id;
      }
      return current && drawings.some((drawing) => drawing.id === current)
        ? current
        : drawings[0]?.id ?? null;
    });
  }, [drawings, navContext?.drawingId]);

  useEffect(() => {
    setOpenedRevision(null);
  }, [selectedDrawingId]);

  function selectDrawing(id) {
    setSelectedDrawingId(id);
  }

  return (
    <div>
      <PageHeader
        title="Drawing Workspace"
        subtitle={
          activeTag
            ? `LTSA Engineering — Mechanical Seal Drawing Library · Pump ${activeTag}`
            : "LTSA Engineering — Mechanical Seal Drawing Library"
        }
        actions={
          <PumpTagSelector
            pumps={pumps}
            currentTag={activeTag}
            loading={pumpsLoading}
            error={pumpsError}
            onSelect={(tag) => setActiveTag(tag)}
          />
        }
      />

      <div className="drawing-workspace-layout">
        <div className="drawing-workspace-library">
          <DrawingLibraryPanel
            drawings={drawings}
            selectedDrawingId={selectedDrawingId}
            onSelectDrawing={selectDrawing}
          />
        </div>

        <div className="drawing-workspace-viewer">
          <DrawingViewerPanel drawing={selectedDrawing} />
        </div>

        <div className="drawing-workspace-data">
          <DrawingMetadataPanel drawing={selectedDrawing} />
          <DrawingRevisionPanel
            drawing={selectedDrawing}
            openedRevision={openedRevision}
            onOpenRevision={setOpenedRevision}
          />
          <DrawingNavigationPanel drawing={selectedDrawing} onNavigate={onNavigate} />

          {/* RC-003B: Engineering Knowledge Panel additions, appended
              after the unmodified RC-003A stack above -- same column,
              same grid, no redesign. */}
          <DrawingHealthCard drawing={selectedDrawing} />
          <SealComponentNavigator drawing={selectedDrawing} />
          <OEMKnowledgePanel drawing={selectedDrawing} />
          <DrawingBomTable drawing={selectedDrawing} />
          <DrawingFutureCapabilitiesPanel />

          {/* RC-003C: Drawing Intelligence -- the final phase, appended
              after the unmodified RC-003A/RC-003B stack above -- same
              column, same grid, no redesign. */}
          <DrawingIntelligencePanel />

          {/* MWO-LTSA-051A: Engineering Notes is explicitly out of scope
              -- the canonical Open Design (drawing-workspace-refinement.html
              §12) names it a Phase-2/Later knowledge concept with no
              approved data model, distinct from the Revision History
              panel's existing per-revision Description field. Rendered
              inline here (no new component file) reusing the exact
              Reserved/Future Capability visual language
              DrawingIntelligencePanel's "AI Analysis" card already
              established -- never fabricated content. */}
          <Card title="Engineering Notes">
            <div
              style={{
                border: `1px dashed ${colors.border}`,
                borderRadius: 8,
                padding: spacing.sm,
                marginBottom: spacing.sm,
              }}
            >
              <div style={{ fontWeight: "bold", color: colors.text }}>Engineering Notes</div>
            </div>
            <Badge variant="info">Reserved</Badge>{" "}
            <Badge variant="info">Future Capability</Badge>
          </Card>
        </div>
      </div>
    </div>
  );
}
