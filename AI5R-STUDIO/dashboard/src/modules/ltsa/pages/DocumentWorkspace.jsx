import { useEffect, useState } from "react";
import { EmptyState, PageHeader } from "../../../design-system";
import DocumentLibraryPanel from "../components/DocumentLibraryPanel";
import DocumentOpenDesignView from "../components/DocumentOpenDesignView";
import { getDocuments, getSealCompatibility } from "../../../api/ai5rClient";
import { mapDocumentRecord } from "../utils/documentMapping";
import "./DocumentWorkspace.css";
import "./LTSAOpenDesign.css";

/**
 * MWO-LTSA-052A -- Document Workspace, migrated to the same LTSA Open
 * Design information hierarchy Pump Workspace (PumpOpenDesignView.jsx,
 * MWO-LTSA-050) and Mechanical Seal Workspace (SealOpenDesignView.jsx,
 * MWO-LTSA-042A, the original) already use. This is a migration, not a
 * redesign: the Document Library (left, unchanged) still owns
 * search/scope/type-filter/selection exactly as RC-004 built it;
 * DocumentOpenDesignView.jsx (right) replaces the old
 * DocumentViewerPanel + DocumentMetadataPanel + DocumentRevisionPanel +
 * DocumentNavigationPanel + DocumentReferencePanel stack with one
 * unified Open Design view, per DocumentOpenDesignView.jsx's own header
 * comment for exactly how each old panel's responsibility was carried
 * forward or consciously not.
 *
 * MWO-LTSA-062 -- Document & Drawing Productionization. `documents` stays
 * an injectable prop (MWO-LTSA-036L discipline) that always wins when
 * passed -- every existing prop-driven test is unaffected. Only when no
 * `documents` prop is given does this component now self-fetch via the
 * existing GET /api/ltsa/documents (getDocuments(), SealEngineeringDocumentGateway,
 * the same real seal_engineering_document table/workflow Drawing Workspace
 * already reads) plus getSealCompatibility() (already real, already used
 * by Seal.jsx) to resolve each document's Equipment/Reference category and
 * linked pump -- mapped through documentMapping.js's mapDocumentRecord()
 * into exactly the shape DocumentOpenDesignView.jsx/DocumentLibraryPanel.jsx
 * already expect, the same hybrid prop/fetch pattern
 * Pump.jsx/Seal.jsx/DrawingWorkspace.jsx/InstallationWorkspace.jsx already
 * use. sampleDocuments.js is no longer a runtime dependency of this file.
 *
 * navContext is now honored (previously unused, a real gap given
 * DrawingNavigationPanel.jsx/DocumentOpenDesignView's own Action Bar
 * already send onNavigate("document", { assetTag })): selectId
 * direct-matches a document id (deep-link convention every other
 * workspace already uses); assetTag auto-selects the first document
 * whose resolved equipmentTag matches, mirroring PM.jsx/CM.jsx's own
 * MWO-LTSA-053/054 fix for the identical gap.
 *
 * MWO-LTSA-052C -- Open PM / Open CM / Open Work Order added alongside
 * Open Pump / Open Drawing, reusing the exact same
 * onNavigate(key, { assetTag }) contract DrawingNavigationPanel.jsx
 * already proves and PM.jsx/CM.jsx already listen for (their own
 * MWO-LTSA-053/054 comments record the original, since-deleted
 * DocumentNavigationPanel.jsx already sent this same call). No new
 * navigation mechanism, no new route.
 */
export default function DocumentWorkspace({ onNavigate, navContext, documents: documentsProp }) {
  const [fetchedDocuments, setFetchedDocuments] = useState([]);
  const documents = documentsProp ?? fetchedDocuments;

  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [documentTypeFilter, setDocumentTypeFilter] = useState("");

  useEffect(() => {
    if (documentsProp) {
      return;
    }

    let active = true;

    Promise.all([getDocuments(), getSealCompatibility()])
      .then(([documentRecords, compatibilityRecords]) => {
        if (active) {
          // MWO-LTSA-072 -- documentRecords (the full raw list) is passed
          // as mapDocumentRecord()'s third argument so real multi-row
          // Version/Revision history (sibling rows sharing document_number)
          // can be resolved -- one already-fetched list, no second call.
          setFetchedDocuments(
            documentRecords.map((record) => mapDocumentRecord(record, compatibilityRecords, documentRecords))
          );
        }
      })
      .catch(() => {
        if (active) {
          setFetchedDocuments([]);
        }
      });

    return () => {
      active = false;
    };
  }, [documentsProp]);

  useEffect(() => {
    setSelectedDocumentId((current) => {
      if (current && documents.some((document) => document.id === current)) {
        return current;
      }
      if (navContext?.selectId) {
        return navContext.selectId;
      }
      if (navContext?.assetTag) {
        const match = documents.find((document) => document.equipmentTag === navContext.assetTag);
        if (match) {
          return match.id;
        }
      }
      return documents[0]?.id ?? null;
    });
  }, [documents, navContext]);

  const selectedDocument = documents.find((document) => document.id === selectedDocumentId) ?? null;

  function selectDocument(id) {
    setSelectedDocumentId(id);
  }

  // MWO-LTSA-052A -- Open Pump / Open Drawing reuse the exact same
  // onNavigate(key, context) mechanism Pump.jsx/Seal.jsx already use for
  // their own cross-workspace links (Seal.jsx's handleOpenPump/
  // handleOpenDrawing are the direct template) -- same "pump"/"drawing"
  // tab keys LTSAWorkspace.jsx already registers, no new navigation
  // pattern, no new route. Preserves the Pump -> Seal -> Drawing ->
  // Document navigation chain this MWO's own Navigation section requires.
  function handleOpenPump(equipmentTag) {
    onNavigate?.("pump", { selectId: equipmentTag });
  }

  function handleOpenDrawing(equipmentTag) {
    onNavigate?.("drawing", { assetTag: equipmentTag });
  }

  function handleOpenPM(equipmentTag) {
    onNavigate?.("pm", { assetTag: equipmentTag });
  }

  function handleOpenCM(equipmentTag) {
    onNavigate?.("cm", { assetTag: equipmentTag });
  }

  function handleOpenWorkOrder(equipmentTag) {
    onNavigate?.("workorder", { assetTag: equipmentTag });
  }

  return (
    <div>
      <PageHeader title="Document Workspace" subtitle="LTSA Engineering — Document Library" />

      <div className="document-workspace-layout">
        <div className="document-workspace-library">
          <DocumentLibraryPanel
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelectDocument={selectDocument}
            documentTypeFilter={documentTypeFilter}
            onDocumentTypeFilterChange={setDocumentTypeFilter}
          />
        </div>

        <div className="document-workspace-detail">
          {selectedDocument ? (
            <DocumentOpenDesignView
              document={selectedDocument}
              documentTypeFilter={documentTypeFilter}
              onDocumentTypeFilterChange={setDocumentTypeFilter}
              onOpenPump={handleOpenPump}
              onOpenDrawing={handleOpenDrawing}
              onOpenPM={handleOpenPM}
              onOpenCM={handleOpenCM}
              onOpenWorkOrder={handleOpenWorkOrder}
            />
          ) : (
            <EmptyState
              title="No document selected"
              description="Select a document from the library to view its details."
            />
          )}
        </div>
      </div>
    </div>
  );
}
