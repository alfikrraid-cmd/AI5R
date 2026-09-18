import { useEffect, useState } from "react";
import { PageHeader, EmptyState, Panel } from "../../../design-system";
import InstallationOpenDesignView from "../components/InstallationOpenDesignView";
import InstallationRegistryPanel from "../components/InstallationRegistryPanel";
import { getInstallations, getPumps } from "../../../api/ai5rClient";
import { mapInstallationRecord } from "../utils/installationMapping";
import "./InstallationWorkspace.css";
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
 * MWO-LTSA-INSTALLATION-UI-PHASE-1 -- the "no registry, exactly one real
 * record" reasoning above no longer holds: production now has 42 real
 * installation_report rows across 39 pumps (verified read-only audit
 * before this change). InstallationRegistryPanel now provides the
 * registry/selector that reasoning always anticipated needing once more
 * than one record existed, built on DocumentWorkspace.jsx's own
 * fetch-both/select-by-id template (getInstallations() + getPumps() via
 * Promise.all, selection as real state instead of a derived "first or
 * navContext.selectId" expression) -- not a new pattern.
 *
 * Area is resolved via the SAME canonical pump/asset area every other
 * LTSA workspace already reads (getPumps(), pumpMapping.js's own
 * `area: record.area`) -- installation_report has no area column of its
 * own, and this reuses the existing source rather than building a second
 * one. `navContext?.selectId` is still honored (matching every other
 * cross-workspace navigation call site's `{ selectId }` contract), now
 * via real selection state rather than a derived expression, so a deep
 * link into a specific report continues to work exactly as before.
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
 *
 * MWO-INSTALLATION-DIRECT-DB-READ-PATH-R1 -- the previous
 * Promise.all([getInstallations(), getPumps()]).catch(() => setFetchedInstallations([]))
 * had a real defect: EITHER call rejecting (not just getInstallations())
 * silently zeroed out real installation data with no error shown --
 * indistinguishable from a genuine empty result. Promise.allSettled()
 * replaces it so the two calls fail independently: a getPumps() failure
 * degrades gracefully (pumpAreaByTag stays an empty Map, so every row's
 * area resolves to its own already-existing `?? null` fallback -- N/A,
 * never fabricated), while installations render regardless. Only a
 * genuine getInstallations() failure sets installationsError and skips
 * rendering the registry/detail layout entirely (mirroring Pump.jsx's own
 * loading/listError pattern) -- so "0 rows" on screen only ever means a
 * real, successful, empty API response, never a swallowed failure.
 */
export default function InstallationWorkspace({ onNavigate, navContext, installations: installationsProp }) {
  const [fetchedInstallations, setFetchedInstallations] = useState([]);
  const installations = installationsProp ?? fetchedInstallations;

  const [installationsLoading, setInstallationsLoading] = useState(!installationsProp);
  const [installationsError, setInstallationsError] = useState(null);

  const [selectedInstallationId, setSelectedInstallationId] = useState(null);

  useEffect(() => {
    if (installationsProp) {
      return;
    }

    let active = true;

    // MWO-INSTALLATION-DIRECT-DB-READ-PATH-R1 -- allSettled, not all(): a
    // failed getPumps() must never erase successfully-fetched installation
    // records (see this file's own header comment).
    Promise.allSettled([getInstallations(), getPumps()]).then(([installationsResult, pumpsResult]) => {
      if (!active) return;

      if (installationsResult.status === "rejected") {
        setInstallationsError("Installations could not be loaded.");
        setInstallationsLoading(false);
        return;
      }

      const pumpRecords = pumpsResult.status === "fulfilled" ? pumpsResult.value : [];
      const pumpAreaByTag = new Map(pumpRecords.map((pump) => [pump.tag_number, pump.area]));
      setFetchedInstallations(installationsResult.value.map((record) => mapInstallationRecord(record, pumpAreaByTag)));
      setInstallationsError(null);
      setInstallationsLoading(false);
    });

    return () => {
      active = false;
    };
  }, [installationsProp]);

  useEffect(() => {
    setSelectedInstallationId((current) => {
      if (current && installations.some((installation) => installation.id === current)) {
        return current;
      }
      if (navContext?.selectId) {
        return navContext.selectId;
      }
      return installations[0]?.id ?? null;
    });
  }, [installations, navContext]);

  const selectedInstallation = installations.find((installation) => installation.id === selectedInstallationId) ?? null;

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

      {installationsLoading ? (
        <Panel>
          <p>Loading installation reports...</p>
        </Panel>
      ) : installationsError ? (
        <Panel>
          <p role="alert">{installationsError}</p>
        </Panel>
      ) : (
        <div className="installation-workspace-layout">
          <div className="installation-workspace-registry">
            <InstallationRegistryPanel
              installations={installations}
              selectedInstallationId={selectedInstallationId}
              onSelectInstallation={setSelectedInstallationId}
            />
          </div>

          <div className="installation-workspace-detail">
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
        </div>
      )}
    </div>
  );
}
