import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "../../../design-system";
import InstallationOpenDesignView from "../components/InstallationOpenDesignView";
import { getInstallations } from "../../../api/ai5rClient";
import { mapInstallationRecord } from "../utils/installationMapping";
import "./LTSAOpenDesign.css";

/**
 * MWO-LTSA-056 -- Installation Workspace. A new LTSA workspace (no prior
 * panel-based implementation existed) translating one real, signed
 * engineering document -- "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf" --
 * into LTSA Open Design. See InstallationOpenDesignView.jsx's own header
 * comment for the full report-to-section mapping and every domain
 * adaptation.
 *
 * MWO-LTSA-060 -- production persistence path. `installations` stays an
 * injectable prop (same MWO-LTSA-036L discipline every LTSA workspace
 * follows) that always wins when passed -- every existing prop-driven test
 * is unaffected. Only when no `installations` prop is given does this
 * component now self-fetch via the existing GET /api/ltsa/installations
 * (getInstallations(), InstallationGateway, BP-INSTALLATION), mapped
 * through installationMapping.js into exactly the shape
 * InstallationOpenDesignView.jsx already expects -- the same hybrid
 * prop/fetch pattern Pump.jsx/Seal.jsx/DrawingWorkspace.jsx already use.
 * `sampleInstallations.js` is no longer a runtime dependency of this file
 * (it remains only as the test fixture InstallationWorkspace.test.jsx
 * already uses, and as the source data/002_seed.sql's real seed was
 * transcribed from) -- a real user now sees the real, persisted record.
 *
 * No library/selector panel: unlike Document/Drawing (which browse many
 * records), Installation has exactly one real record today and no registry
 * to browse -- adding a selector here would be inventing browsing UX this
 * MWO's single-document source doesn't call for ("No scope expansion").
 * `navContext?.selectId` is still honored (matching every other
 * cross-workspace navigation call site's `{ selectId }` contract) so a
 * deep link into a specific report keeps working once more than one
 * exists.
 *
 * MWO-LTSA-068 -- Installation Workspace Enhancement ("Engineering
 * Document Viewer"). Adds Open Lifecycle (handleOpenLifecycle) alongside
 * the existing Open Pump/Open Drawing handlers, reusing the exact same
 * onNavigate(key, context) mechanism -- no new navigation pattern, no new
 * backend call, no schema change. Pump remains the Aggregate Root and
 * Installation remains an Engineering Document; neither this file nor
 * InstallationOpenDesignView.jsx touches the Pump Lifecycle Engine or
 * EquipmentTimelineService -- "Open Lifecycle" only navigates to their
 * existing, already-wired frontend consumer (KnowledgeWorkspace/Asset
 * 360, the "history" route).
 */
export default function InstallationWorkspace({ onNavigate, navContext, installations: installationsProp }) {
  const [fetchedInstallations, setFetchedInstallations] = useState([]);
  const installations = installationsProp ?? fetchedInstallations;

  useEffect(() => {
    if (installationsProp) {
      return;
    }

    let active = true;

    getInstallations()
      .then((records) => {
        if (active) {
          setFetchedInstallations(records.map(mapInstallationRecord));
        }
      })
      .catch(() => {
        if (active) {
          setFetchedInstallations([]);
        }
      });

    return () => {
      active = false;
    };
  }, [installationsProp]);

  const selectedInstallation =
    installations.find((installation) => installation.id === navContext?.selectId) ?? installations[0] ?? null;

  // MWO-LTSA-056 -- Open Pump / Open Drawing reuse the exact same
  // onNavigate(key, context) mechanism every other LTSA workspace's
  // Action Bar already uses (Document.jsx's handleOpenPump/
  // handleOpenDrawing are the direct template) -- same "pump"/"drawing"
  // tab keys LTSAWorkspace.jsx already registers, no new navigation
  // pattern, no new route.
  function handleOpenPump(equipmentTag) {
    onNavigate?.("pump", { selectId: equipmentTag });
  }

  function handleOpenDrawing(equipmentTag) {
    onNavigate?.("drawing", { assetTag: equipmentTag });
  }

  // MWO-LTSA-068 -- Open Lifecycle reuses the exact onNavigate("history",
  // { assetTag }) call every other "View History"/"Open Asset 360" button
  // in LTSA already makes (Pump.jsx's own "View History" is the direct
  // template) -- KnowledgeWorkspace (Asset 360) is the existing
  // "everything about this equipment" surface; no new route, no new
  // backend call, Pump Lifecycle Engine/EquipmentTimelineService untouched.
  function handleOpenLifecycle(equipmentTag) {
    onNavigate?.("history", { assetTag: equipmentTag });
  }

  return (
    <div>
      <PageHeader title="Installation Workspace" subtitle="LTSA Engineering — Mechanical Seal Installation Report" />

      {selectedInstallation ? (
        <InstallationOpenDesignView
          installation={selectedInstallation}
          onOpenPump={handleOpenPump}
          onOpenDrawing={handleOpenDrawing}
          onOpenLifecycle={handleOpenLifecycle}
        />
      ) : (
        <EmptyState
          title="No installation report selected"
          description="Select an installation report to view its details."
        />
      )}
    </div>
  );
}
