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
import { getPumpKnowledge, getSealCompatibility, getSeals, getDocuments } from "../../../api/ai5rClient";
import { mapDrawingRecord } from "../utils/drawingMapping";
import { resolveCompatibleSeals } from "../utils/sealMapping";
import "./DrawingWorkspace.css";

/**
 * LTSA Drawing Workspace — Foundation (RC-003A) + Knowledge Hub (RC-003B)
 * + Drawing Intelligence (RC-003C, final phase), extending the approved
 * Open Design (DESIGN/LTSA/DRAWING_WORKSPACE/drawing-workspace-spec.html
 * + drawing-workspace-refinement.html). RC-003A's shell, Library, Viewer,
 * Metadata, Revision, and Navigation panels are unmodified in position
 * and behavior. RC-003B's five panels (Drawing Health, Seal Component
 * Navigator, OEM Knowledge, BOM, Future Capabilities) are unmodified.
 * RC-003C's DrawingIntelligencePanel (AI Analysis, Relationship Graph,
 * Knowledge Graph, OCR, Drawing Highlight, Digital Twin, Future
 * Integration Panel -- all disclosed placeholders) is appended to the
 * same right-hand data column, in the same three-column grid RC-003A
 * already established -- no layout redesign. Engineering AI, Graphiti,
 * OCR, Knowledge Graph, Relationship Engine, Digital Twin, Recommendation
 * Engine, backend, API, database, drawing overlay, and drawing annotation
 * are all explicitly out of scope for this RC and are not implemented
 * here.
 *
 * MWO-LTSA-051A: no new backend, API, or database query was added for
 * Drawing. The existing, already-real GET /api/ltsa/pumps/{tag}/knowledge endpoint
 * (getPumpKnowledge(), already used by Pump.jsx/Seal.jsx) already returns
 * a `drawings` field (LTSAKnowledgeService._build_drawings()) -- this is
 * the one reused source of real drawing data. `drawings` stays an
 * injectable prop (MWO-LTSA-036L) that always wins when passed, exactly
 * as before -- every existing prop-driven caller/test is unaffected. Only
 * when no `drawings` prop is given does this component now self-fetch,
 * mirroring the same hybrid prop/fetch pattern Pump.jsx/Seal.jsx already
 * use: if `navContext.assetTag` is present, it calls the existing
 * getPumpKnowledge(tag) and maps `data.drawings` through
 * mapDrawingRecord(); otherwise it falls back to the same genuine empty
 * state as before (every panel below already has one, nothing
 * fabricated).
 *
 * MWO-LTSA-062 -- Seal/Document relationships. The Knowledge endpoint's
 * drawing rows still carry no seal_code (a frozen, deliberately narrow
 * shape from MWO-LTSA-033 -- not reopened by this MWO, see
 * drawingMapping.js's own header comment). Instead, alongside
 * getPumpKnowledge(), this effect now also calls the existing
 * getSealCompatibility() (already real, already used by Seal.jsx) to
 * resolve which seal_code(s) are compatible with this pump
 * (resolveCompatibleSeals(), sealMapping.js), the existing getSeals() to
 * look up those seals' real model name, and the existing getDocuments()
 * (the same real seal_engineering_document list Document Workspace now
 * reads) to find every non-DRAWING document sharing one of those
 * seal_code(s) -- passed into mapDrawingRecord()'s optional third
 * argument. Every drawing shown for this pump gets the same
 * pump-level-resolved sealModel/relatedDocuments (no per-drawing
 * seal_code exists to resolve them any more precisely) -- an honest,
 * real relationship, not a fabricated one.
 */
export default function DrawingWorkspace({ onNavigate, navContext, drawings: drawingsProp }) {
  const [fetchedDrawings, setFetchedDrawings] = useState([]);
  const drawings = drawingsProp ?? fetchedDrawings;

  const [selectedDrawingId, setSelectedDrawingId] = useState(drawings[0]?.id ?? null);
  const [openedRevision, setOpenedRevision] = useState(null);

  const selectedDrawing = drawings.find((drawing) => drawing.id === selectedDrawingId) ?? null;

  useEffect(() => {
    if (drawingsProp) {
      return;
    }

    const assetTag = navContext?.assetTag;

    if (!assetTag) {
      setFetchedDrawings([]);
      return;
    }

    let active = true;

    Promise.all([getPumpKnowledge(assetTag), getSealCompatibility(), getSeals(), getDocuments()])
      .then(([knowledgeResponse, compatibilityRecords, sealRecords, documentRecords]) => {
        if (!active) {
          return;
        }

        const compatibleSealCodes = resolveCompatibleSeals(assetTag, compatibilityRecords);

        const sealModel = compatibleSealCodes
          .map((sealCode) => sealRecords.find((seal) => seal.seal_code === sealCode)?.model)
          .filter(Boolean)
          .join(", ") || null;

        const relatedDocuments = documentRecords.filter(
          (document) =>
            document.document_type !== "DRAWING" && compatibleSealCodes.includes(document.seal_code)
        );

        const records = knowledgeResponse?.data?.drawings ?? [];
        setFetchedDrawings(
          records.map((record) => mapDrawingRecord(record, assetTag, { sealModel, relatedDocuments }))
        );
      })
      .catch(() => {
        if (active) {
          setFetchedDrawings([]);
        }
      });

    return () => {
      active = false;
    };
  }, [drawingsProp, navContext?.assetTag]);

  useEffect(() => {
    setSelectedDrawingId((current) =>
      current && drawings.some((drawing) => drawing.id === current) ? current : drawings[0]?.id ?? null
    );
  }, [drawings]);

  useEffect(() => {
    setOpenedRevision(null);
  }, [selectedDrawingId]);

  function selectDrawing(id) {
    setSelectedDrawingId(id);
  }

  return (
    <div>
      <PageHeader title="Drawing Workspace" subtitle="LTSA Engineering — Mechanical Seal Drawing Library" />

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
