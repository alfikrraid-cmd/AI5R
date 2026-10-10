import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-034 -- KnowledgeDrawingSection: Drawings body (KnowledgeCard
// variant="row-list"), replacing the generic RefRows placeholder that
// previously rendered this section. Reuses the exact row shell
// (.part-item/.part-row/.part-name/.part-meta) every other row-list
// section already uses (PM/CM/Breakdown History, Compatible Seals) --
// no new visual language. Metadata only, per this MWO's explicit scope:
// title, document number, revision, status, uploaded date, and a Viewer
// button. No CAD rendering, no PDF rendering -- the Viewer button is a
// placeholder action (no-op), same disclosed-gap posture as every other
// "not yet wired" affordance in this workspace (KnowledgeAIInsight's
// disabled CTA, the Open Design's own placeholder-navigation note for
// row items).

// LTSA_ASSET360_DRAWING_READ_PATH_REPAIR_R2 -- a governed asset link's
// confidence, shown as stored; rows without a link (seal documents, the
// Documents section) carry no confidence and show no label.
const CONFIDENCE_LABEL = {
  CONFIRMED: "Terkonfirmasi",
  REFERENCE_ONLY: "Hanya referensi",
};

function DrawingRow({ drawing, onOpenViewer }) {
  return (
    <div className="part-item" data-testid="knowledge-drawing-item">
      <div className="part-row">
        <span className="part-name">{drawing.title ?? "Unavailable"}</span>
        <span className="stock-flag" data-testid="knowledge-drawing-status">
          {drawing.status ?? "Unavailable"}
        </span>
        {drawing.confidenceStatus ? (
          <span className="stock-flag" data-testid="knowledge-drawing-confidence">
            {CONFIDENCE_LABEL[drawing.confidenceStatus] ?? drawing.confidenceStatus}
          </span>
        ) : null}
        {drawing.equipmentSide ? (
          <span className="stock-flag" data-testid="knowledge-drawing-side">
            {drawing.equipmentSide}
          </span>
        ) : null}
      </div>
      <div className="part-meta">
        <span data-testid="knowledge-drawing-document-number">{drawing.documentNumber ?? "Unavailable"}</span>
        {" · Rev "}
        <span data-testid="knowledge-drawing-revision">{drawing.revision ?? "-"}</span>
        {" · Diunggah "}
        <span data-testid="knowledge-drawing-uploaded">{drawing.uploadedAt ?? "-"}</span>
      </div>
      <button
        type="button"
        className="btn-link"
        onClick={() => onOpenViewer?.(drawing)}
      >
        Buka Viewer
      </button>
    </div>
  );
}

export default function KnowledgeDrawingSection({ items = [], onOpenViewer }) {
  if (!items.length) {
    return <EmptySection title="Belum ada gambar teknik" />;
  }

  return (
    <div data-testid="knowledge-drawing-section">
      {items.map((drawing, index) => (
        <DrawingRow
          key={`${drawing.id ?? drawing.documentNumber ?? index}-${drawing.equipmentSide ?? ""}`}
          drawing={drawing}
          onOpenViewer={onOpenViewer}
        />
      ))}
    </div>
  );
}
