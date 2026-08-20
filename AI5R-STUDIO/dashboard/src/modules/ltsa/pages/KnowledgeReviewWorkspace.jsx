import { EmptyState, PageHeader } from "../../../design-system";
import KnowledgeReviewWorkspaceView from "../components/KnowledgeReviewWorkspaceView";
import "./LTSAOpenDesign.css";

const EMPTY_PACKAGE = { pumps: [], seals: [], installations: [], documents: [], validation: null };

/**
 * MWO-LTSA-078 -- Knowledge Review Workspace. A new LTSA workspace (no
 * prior implementation existed) for reviewing an already-validated
 * Knowledge Package (CORE-SERVICES/API/import_validator.py's
 * ImportPackage entity lists plus its ValidatedImportPackage validation
 * result, "COMPLETE. Reuse it."). Display only -- no editing, no
 * importing, no upload; this file performs no fetch and defines no
 * mutation of any kind.
 *
 * No backend call changes, per this MWO's explicit rule: no router
 * exposes ValidatedImportPackage yet (confirmed by repository archaeology
 * before writing this file -- import_validator.py has no consumer
 * anywhere in CORE-SERVICES/BACKEND-API/routers/), so `knowledgePackage`
 * stays an injectable prop, defaulting to a genuine empty package (never
 * fabricated sample data) -- the same Foundation-only discipline
 * DocumentWorkspace.jsx/DrawingWorkspace.jsx originally shipped with
 * before their own later backend-wiring MWOs. A future MWO that adds a
 * real endpoint can supply this prop without any change to this file.
 */
export default function KnowledgeReviewWorkspace({ onNavigate, knowledgePackage = EMPTY_PACKAGE }) {
  const hasAnyRecords =
    (knowledgePackage.pumps?.length ?? 0) > 0 ||
    (knowledgePackage.seals?.length ?? 0) > 0 ||
    (knowledgePackage.installations?.length ?? 0) > 0 ||
    (knowledgePackage.documents?.length ?? 0) > 0;

  return (
    <div>
      <PageHeader title="Knowledge Review Workspace" subtitle="LTSA Engineering — Knowledge Package Validation Review" />

      {hasAnyRecords ? (
        <KnowledgeReviewWorkspaceView knowledgePackage={knowledgePackage} onNavigate={onNavigate} />
      ) : (
        <EmptyState
          title="No Knowledge Package loaded"
          description="A Knowledge Package has no pump, seal, installation, or document records to review yet."
        />
      )}
    </div>
  );
}
