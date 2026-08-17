import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import { Table } from "../../../design-system";
import { Section, InfoRow, RailSection, ActionBar, RefGroup } from "./open-design";
import { computeBomColumns, resolveBomRowKey } from "../utils/installationBomColumns";

/**
 * MWO-LTSA-056 -- Installation Workspace, a new LTSA Open Design
 * workspace (not a migration -- no prior panel-based implementation
 * existed for Installation). Built entirely from the shared
 * components/open-design/ Kit (Section/InfoRow/RailSection/ActionBar/
 * RefGroup, MWO-LTSA-050B) plus the design-system Table (already reused
 * for Document's Revision History and Drawing's BOM) and
 * PumpWorkspaceDrawer -- no new design language, no new CSS, no new
 * table component.
 *
 * SOURCE OF TRUTH: "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf" (see
 * data/sampleInstallations.js's own header for the full transcription
 * discipline). Every Section below is a 1:1 translation of one printed
 * report section -- REPORT INFORMATION, GENERAL DATA, SERVICE /
 * OPERATION CONDITIONS, SEAL CHAMBER & SHAFT INSPECTION, NOTE, SUMMARY,
 * BILL OF MATERIAL, MECHANICAL SEAL DRAWING, the four component reuse
 * observation checklists, and the signature block -- never merged, never
 * split, never renamed, never invented.
 *
 * SECTION ORDER (main column, top to bottom) mirrors the report's own
 * page order exactly:
 *   Hero (Identity) -> Report Information -> General Data ->
 *   Service / Operation Conditions -> Seal Chamber & Shaft Inspection ->
 *   Note -> Summary -> Bill of Material -> Mechanical Seal Drawing ->
 *   Gland Observation -> Sleeve Observation -> Retainer / Disc
 *   Observation -> Cartridge Drive Collar Observation -> Signatures.
 *
 * Domain adaptation from Pump/Seal/PM/WorkOrder/Document's hierarchy
 * (documented, not silent -- every deviation below is because the
 * report itself has no equivalent fact, never a simplification):
 * - No Engineering AI section: the report has no AI/recommendation
 *   concept at all (unlike Pump/Seal/WorkOrder's real Engineering AI or
 *   PM's disclosed placeholder) -- adding one here would be presenting a
 *   capability this canonical document never claims to have.
 * - No LTSA Coverage section and no StatusSignal anywhere on this page:
 *   the report has no status/coverage field of any kind (it is a
 *   completed, signed record, not a live registry item with a
 *   condition). This is the same "no defined mapping -> omit the whole
 *   slot rather than invent a placeholder" discipline
 *   PumpOpenDesignView.jsx's own header comment already establishes for
 *   its omitted Lifecycle Stepper.
 * - No "Recent Activities" Inspector Rail section: Pump/PM/WorkOrder all
 *   have a real (if often-empty) `timeline` field their Rail renders;
 *   Installation has no timeline concept at all in this data model, so
 *   rendering an always-empty "No recent activity available." row would
 *   be a UI affordance for a fact this document doesn't carry -- omitted
 *   rather than faked-empty, exactly the distinction MWO-LTSA-052B's own
 *   audit drew between a real empty field and a fabricated one.
 * - Report Information / General Data / Service Operation Conditions /
 *   Note render the report's own left/right column groupings verbatim
 *   (using the same `.assessment-columns` two-column layout mechanism
 *   Pump/Seal/PM/WorkOrder's own Engineering Overview sections already
 *   use), but WITHOUT an inner sub-eyebrow caption on either column --
 *   the report itself prints no sub-heading over either half of these
 *   tables, and inventing one (e.g. "Equipment Data"/"Seal Data") would
 *   be introducing terminology the source document doesn't have. Report
 *   Information itself prints as a single column on the report and is
 *   rendered as one column here, not split into two.
 * - Hero repeats a short Identity/Technical summary (Report No./Customer/
 *   Plant, then Plant Equip. No./Seal Type/Drawing No.), and the
 *   Inspector Rail repeats Equipment/Seal/Report Date -- these are the
 *   same "duplicate a real fact for at-a-glance visibility" pattern
 *   every other Open Design workspace already uses (e.g. StatusSignal
 *   shown in both Hero and Rail); no new fact is introduced, only
 *   already-transcribed report fields are re-shown.
 * - Two report values are transcribed with the source's own apparent
 *   clerical typo intact (`sealArrangement: "Non-Cartridge Sigle Seal"`,
 *   the Gland item `"Flus Port Clogged"`) -- see
 *   data/sampleInstallations.js's header for why they are not silently
 *   corrected. The signature block's printed column label ("Tittle") is,
 *   by contrast, UI chrome authored fresh for this page (not a
 *   transcribed report VALUE), so it is rendered correctly as "Title"
 *   below.
 * - The report prints no heading above its four-signatory sign-off
 *   block. "Signatures" is a minimal, purely structural caption added so
 *   the block has a Section id/title (Section.jsx requires one) -- it
 *   introduces no new fact, only names an otherwise-untitled block
 *   already present on the report.
 * - Bill of Material and the observation checklists reuse the exact
 *   RefGroup/Table shapes Document/Pump/PM/Drawing already use for
 *   list-of-named-items and tabular row data respectively -- no new
 *   list-rendering or table pattern.
 * - Action Bar offers "Open Pump" (plantEquipNo, "211-P-14B", is the same
 *   kind of real asset tag every other workspace's Action Bar already
 *   navigates from), "Open Drawing" (drawingNo, "E12914"), and "Open
 *   Lifecycle" (MWO-LTSA-068) -- the exact onOpenPump/onOpenDrawing/
 *   onOpenLifecycle contract Document/Pump/Seal/PM/WorkOrder already use
 *   (onOpenLifecycle reuses onNavigate("history", { assetTag }), the same
 *   call every other "View History"/"Open Asset 360" button in LTSA
 *   already makes -- KnowledgeWorkspace/Asset 360 is the existing
 *   "everything about this equipment" surface this MWO's "Open Lifecycle"
 *   points at; no new route, no new backend call, and neither the Pump
 *   Lifecycle Engine nor EquipmentTimelineService is touched by this
 *   file -- it only navigates to their existing, already-wired frontend
 *   consumer).
 *
 * MWO-LTSA-068 -- Installation Workspace Enhancement ("Engineering
 * Document Viewer"). Architecture-frozen, additive-only change: Pump
 * remains the Aggregate Root, Installation remains an Engineering
 * Document (unchanged relationship), no backend/API/schema touched. Adds
 * six small, informational Sections (Pump/Drawing/Seal/Engineer/
 * Attachments/Remarks) directly under the Hero, before the existing
 * Report Information section -- report-fidelity sections below (Report
 * Information, General Data, ..., Signatures) are completely unchanged
 * from MWO-LTSA-056/060, satisfying this MWO's own "Report Information"
 * and "Signatures" requirements without moving or renaming them.
 * - Pump/Drawing/Seal are plain InfoRow re-displays of fields already
 *   mapped and already rendered elsewhere on this page (Hero/General
 *   Data) -- the same "duplicate a real fact for at-a-glance visibility"
 *   pattern this file's own header already documents elsewhere, just
 *   applied to the new Document-Viewer-style overview. No new fetch: the
 *   already-fetched `installation` prop is the only data source.
 * - Engineer is DERIVED, not a new field: filters the already-fetched
 *   `installation.signatures` (Table further down) for signatories whose
 *   Title contains "Eng" -- a real, evidenced subset of existing data,
 *   never a fabricated role assignment.
 * - Attachments reuses the one real, already-existing
 *   `source_document_name` column (installation_report, NOT NULL) via
 *   `installationMapping.js`'s new `sourceDocumentName` field -- no file
 *   list exists in this schema, so this section honestly shows the one
 *   real attachment (the scanned source document's own name), via
 *   RefGroup's existing empty-state mechanism if ever absent.
 * - Remarks: no `remarks` column exists anywhere in installation_report
 *   (confirmed against CANONICAL_SCHEMA.sql before writing this), and
 *   this MWO explicitly forbids schema changes -- rather than silently
 *   omitting a section this MWO's own "Show:" list names, it renders the
 *   same disclosed-unavailable pattern Engineering AI already uses
 *   elsewhere in this codebase for a plausible-but-unimplemented concept
 *   (never a fabricated remarks string).
 *
 * Data discipline (never fabricate): identical to every other Open
 * Design view in this codebase -- every field shows real, transcribed
 * report data or an honest "—" (null), never an invented value.
 */

const _ENGINEER_TITLE_PATTERN = /eng/i;

export default function InstallationOpenDesignView({ installation, onOpenPump, onOpenDrawing, onOpenLifecycle }) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"

  // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- siteActivities
  // is date-grouped ([{ date, activities }]), never a flat string list (3
  // of 5 golden-sample reports print multiple dated field-activity
  // sessions); rendered as one RefGroup per date so chronology stays
  // visible, instead of collapsing every date's activities together.
  const siteActivityGroups = installation.siteActivities.map((group, gi) => ({
    key: group.date ?? `activity-group-${gi}`,
    date: group.date,
    items: group.activities.map((activity, ai) => ({ key: `activity-${gi}-${ai}`, name: activity })),
  }));

  const bomColumns = computeBomColumns(installation.billOfMaterial);
  const bomRowKey = resolveBomRowKey(installation.billOfMaterial);

  const postInstallationReadingItems = (installation.postInstallationReadings ?? []).map((reading, i) => {
    const parts = [];
    if (reading.de !== undefined && reading.de !== null) parts.push(`DE: ${reading.de}${reading.unit ?? ""}`);
    if (reading.nde !== undefined && reading.nde !== null) parts.push(`NDE: ${reading.nde}${reading.unit ?? ""}`);
    if (parts.length === 0 && reading.value !== undefined && reading.value !== null) {
      parts.push(`${reading.value}${reading.unit ?? ""}`);
    }
    const metaParts = [];
    if (reading.location) metaParts.push(reading.location);
    if (reading.dateTime) metaParts.push(reading.dateTime);
    if (reading.condition) metaParts.push(reading.condition);

    return {
      key: reading.measurement ? `${reading.measurement}-${i}` : `reading-${i}`,
      name: reading.measurement ?? "—",
      flag: "ok",
      flagLabel: parts.join(" · ") || "—",
      meta: metaParts.length > 0 ? metaParts.join(" · ") : undefined,
    };
  });

  const engineerItems = installation.signatures
    .filter((signatory) => _ENGINEER_TITLE_PATTERN.test(signatory.title ?? ""))
    .map((signatory) => ({
      key: signatory.id,
      name: signatory.name ?? "—",
      meta: signatory.title,
    }));

  const attachmentItems = installation.sourceDocumentName
    ? [{ key: installation.sourceDocumentName, name: installation.sourceDocumentName }]
    : [];

  // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- a
  // dual-position (DE/NDE) seal's observation entries carry checkedDE/
  // checkedNDE instead of a single checked boolean (1 of 5 golden-sample
  // reports has this shape); both states are always shown explicitly,
  // never collapsed into one combined checked value -- collapsing DE=true/
  // NDE=false into a single checked=true would be real engineering
  // information loss. Single-position entries (checked only) render
  // exactly as before -- byte-for-byte unchanged for every existing report.
  function observationItems(list) {
    return list.map((entry) => {
      const isDualPosition = "checkedDE" in entry || "checkedNDE" in entry;
      if (isDualPosition) {
        const de = entry.checkedDE ? "Checked" : "Not Checked";
        const nde = entry.checkedNDE ? "Checked" : "Not Checked";
        return {
          key: entry.item,
          name: entry.item,
          flag: entry.checkedDE || entry.checkedNDE ? "ok" : "pending",
          flagLabel: `DE: ${de} · NDE: ${nde}`,
        };
      }
      return {
        key: entry.item,
        name: entry.item,
        flag: entry.checked ? "ok" : "pending",
        flagLabel: entry.checked ? "Checked" : "Not Checked",
      };
    });
  }

  return (
    <div className="ltsa-open-design" data-testid="installation-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            {installation.plantEquipNo ? (
              <button
                type="button"
                className="crumb-link"
                onClick={() => onOpenPump?.(installation.plantEquipNo)}
                data-od-id="crumb-pump-link"
              >
                {installation.plantEquipNo}
              </button>
            ) : (
              <span>Unknown Equipment</span>
            )}
            <span className="sep">›</span><span>Installation Report</span>
            <span className="sep">›</span><b>{installation.reportNo}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>Mechanical Seal Installation Report</h1>
            <div className="identity-status">
              <span className="running-line">
                <span className="dot-sm" />
                {installation.reportNo} · {installation.date}
              </span>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="Report No." value={installation.reportNo} valueClassName="mono" />
              <InfoRow label="Customer" value={installation.customer} />
              <InfoRow label="Plant" value={installation.plant} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Plant Equip. No." value={installation.plantEquipNo ?? "—"} />
              <InfoRow label="Seal Type" value={installation.sealType ?? "—"} />
              <InfoRow label="Drawing No." value={installation.drawingNo ?? "—"} />
            </div>
          </section>

          {/* MWO-LTSA-068 -- Engineering Document Viewer overview. Six
              informational Sections, InfoRow/RefGroup only (no buttons --
              Open Pump/Open Drawing/Open Lifecycle live in the Action Bar
              only, avoiding a second, redundant set of navigation
              triggers). */}
          <Section id="installation-pump-section" title="Pump">
            <div style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Plant Equip. No." value={installation.plantEquipNo ?? "—"} />
              <InfoRow label="Pump Type" value={installation.pumpType ?? "—"} />
              <InfoRow label="Model/Type" value={installation.modelType ?? "—"} />
              <InfoRow label="Rotation" value={installation.rotation ?? "—"} />
              <InfoRow label="Shaft Speed" value={installation.shaftSpeed ?? "—"} />
            </div>
          </Section>

          <Section id="installation-drawing-section" title="Drawing">
            <div style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Drawing No." value={installation.drawingNo ?? "—"} />
            </div>
          </Section>

          <Section id="installation-seal-section" title="Seal">
            <div style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Seal Manufacture" value={installation.sealManufacture ?? "—"} />
              <InfoRow label="Seal Type" value={installation.sealType ?? "—"} />
              <InfoRow label="Seal Arrangement" value={installation.sealArrangement ?? "—"} />
              <InfoRow label="Seal Size" value={installation.sealSize ?? "—"} />
              <InfoRow label="Seal Code" value={installation.sealCode ?? "—"} />
            </div>
          </Section>

          <Section id="installation-engineer-section" title="Engineer">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Engineers" items={engineerItems} emptyReason="No engineer-titled signatory on this report" />
            </div>
          </Section>

          <Section id="installation-attachments-section" title="Attachments">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Source Documents" items={attachmentItems} emptyReason="No source document on file" />
            </div>
          </Section>

          <Section id="installation-remarks-section" title="Remarks">
            <p className="confidence-label ref-group-empty" style={{ marginTop: "var(--space-3)" }}>
              No remarks field exists in this report.
            </p>
          </Section>

          <Section id="report-information-section" title="Report Information">
            <div style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Report No." value={installation.reportNo ?? "—"} />
              <InfoRow label="TSO No." value={installation.tsoNo ?? "—"} />
              <InfoRow label="Date" value={installation.date ?? "—"} />
              <InfoRow label="Customer" value={installation.customer ?? "—"} />
              <InfoRow label="Address" value={installation.address ?? "—"} />
              <InfoRow label="Plant" value={installation.plant ?? "—"} />
              <InfoRow label="Unit" value={installation.unit ?? "—"} />
              <InfoRow label="PO No." value={installation.poNo ?? "—"} />
              <InfoRow label="Packing List No." value={installation.packingListNo ?? "—"} />
              <InfoRow label="Location" value={installation.location ?? "—"} />
            </div>
          </Section>

          <Section id="general-data-section" title="General Data">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <InfoRow label="Equipment Mfr." value={installation.equipmentMfr ?? "—"} />
                <InfoRow label="Model/Type" value={installation.modelType ?? "—"} />
                <InfoRow label="Size" value={installation.size ?? "—"} />
                <InfoRow label="Configuration" value={installation.configuration ?? "—"} />
                <InfoRow label="Serial No." value={installation.serialNo ?? "—"} />
                <InfoRow label="Plant Equip. No." value={installation.plantEquipNo ?? "—"} />
                <InfoRow label="Pump Type" value={installation.pumpType ?? "—"} />
                <InfoRow label="Shaft Speed" value={installation.shaftSpeed ?? "—"} />
                <InfoRow label="Rotation" value={installation.rotation ?? "—"} />
              </div>
              <div>
                <InfoRow label="Seal Manufacture" value={installation.sealManufacture ?? "—"} />
                <InfoRow label="Seal Type" value={installation.sealType ?? "—"} />
                <InfoRow label="Seal Arrangement" value={installation.sealArrangement ?? "—"} />
                <InfoRow label="Seal Size" value={installation.sealSize ?? "—"} />
                <InfoRow label="Material Code" value={installation.materialCode ?? "—"} />
                <InfoRow label="Drawing No." value={installation.drawingNo ?? "—"} />
                <InfoRow label="Seal Location" value={installation.sealLocation ?? "—"} />
              </div>
            </div>
          </Section>

          <Section id="service-operation-conditions-section" title="Service / Operation Conditions">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <InfoRow label="Liquid" value={installation.liquid ?? "—"} />
                <InfoRow label="Temperature Range" value={installation.temperatureRange ?? "—"} />
                <InfoRow label="Specific Gravity" value={installation.specificGravity ?? "—"} />
                <InfoRow label="Viscosity" value={installation.viscosity ?? "—"} />
                <InfoRow label="Flash Point" value={installation.flashPoint ?? "—"} />
                <InfoRow label="Boiling Point" value={installation.boilingPoint ?? "—"} />
                <InfoRow label="Freeze Point" value={installation.freezePoint ?? "—"} />
                <InfoRow label="Vapor Press." value={installation.vaporPress ?? "—"} />
                <InfoRow label="Discharge Press." value={installation.dischargePress ?? "—"} />
                <InfoRow label="Suction Press." value={installation.suctionPress ?? "—"} />
                <InfoRow label="Differential Press." value={installation.differentialPress ?? "—"} />
              </div>
              <div>
                <InfoRow label="Stuffing Box Press." value={installation.stuffingBoxPress ?? "—"} />
                <InfoRow label="Seal Press." value={installation.sealPress ?? "—"} />
                <InfoRow label="Corrosion/Erosion by" value={installation.corrosionErosionBy ?? "—"} />
                <InfoRow label="API Plan" value={installation.apiPlan ?? "—"} />
                <InfoRow label="Flush Liquid" value={installation.flushLiquid ?? "—"} />
                <InfoRow label="Flush Pressure" value={installation.flushPressure ?? "—"} />
                <InfoRow label="Flush Temp. (°C)" value={installation.flushTemp ?? "—"} />
                <InfoRow label="Flush Flowrate" value={installation.flushFlowrate ?? "—"} />
                <InfoRow label="Buffer/Barrier Press." value={installation.bufferBarrierPress ?? "—"} />
                <InfoRow label="Buffer/Barrier Fluid" value={installation.bufferBarrierFluid ?? "—"} />
                <InfoRow label="Quench Fluid" value={installation.quenchFluid ?? "—"} />
              </div>
            </div>
          </Section>

          <Section id="seal-chamber-shaft-inspection-section" title="Seal Chamber & Shaft Inspection">
            <div style={{ marginTop: "var(--space-3)" }}>
              {installation.sealChamberShaftInspection.map((row) => (
                <InfoRow
                  key={row.item}
                  label={row.item}
                  value={`${row.value ?? "—"} (${row.standard})`}
                />
              ))}
            </div>
          </Section>

          <Section id="note-section" title="Note">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <InfoRow label="Basic Seal Condition" value={installation.basicSealCondition ?? "—"} />
                <InfoRow label="Gland Condition" value={installation.glandCondition ?? "—"} />
                <InfoRow label="Sleeve Condition" value={installation.sleeveCondition ?? "—"} />
                <InfoRow label="Shaft Condition" value={installation.shaftCondition ?? "—"} />
              </div>
              <div>
                <InfoRow label="Bearing Condition" value={installation.bearingCondition ?? "—"} />
                <InfoRow label="Gasket Condition" value={installation.gasketCondition ?? "—"} />
                <InfoRow label="Radial Bearing No." value={installation.radialBearingNo ?? "—"} />
                <InfoRow label="Thrust Bearing No." value={installation.thrustBearingNo ?? "—"} />
              </div>
            </div>
          </Section>

          <Section id="summary-section" title="Summary">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)" }}>{installation.summaryIntro}</p>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{installation.siteActivityIntro}</p>
            {siteActivityGroups.map((group) => (
              <div key={group.key} style={{ marginTop: "var(--space-2)" }}>
                <RefGroup title={group.date ?? "Site Activity"} items={group.items} />
              </div>
            ))}
          </Section>

          {/* MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 --
              2 of 5 golden-sample reports (211-P-2A DE, 212-P-13AR) print a
              dated, DE/NDE-split post-installation measurement table
              directly on the same signed document. installation.
              postInstallationReadings is null (not []) for the 3 of 5
              reports with no such section -- omitted entirely here, the
              same "no defined field -> omit the whole slot" discipline this
              file's own header comment already establishes for Remarks/
              Recent Activities, rather than a fake-empty section. */}
          {installation.postInstallationReadings && (
            <Section id="post-installation-readings-section" title="Post-Installation Readings">
              <div style={{ marginTop: "var(--space-3)" }}>
                <RefGroup
                  title="Readings"
                  items={postInstallationReadingItems}
                  emptyReason="No post-installation readings on this report"
                />
              </div>
            </Section>
          )}

          <Section id="bill-of-material-section" title="Bill of Material">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)", marginBottom: "var(--space-2)" }}>
              {installation.bomCaption}
            </p>
            <Table rowKey={bomRowKey} data={installation.billOfMaterial} columns={bomColumns} />
          </Section>

          {/* Mechanical Seal Drawing deliberately keeps raw markup, same
              reason as every other workspace's own documented Documents
              exception -- its eyebrow sits inside .section-head alongside
              a button, deviating from Section's generic shape. */}
          <section className="assessment-section" data-od-id="mechanical-seal-drawing-section">
            <div className="section-head">
              <span className="eyebrow">Mechanical Seal Drawing</span>
              <button
                type="button"
                className="btn-link"
                onClick={() => { onOpenDrawing?.(installation.drawingNo); setDrawer("drawing"); }}
                data-od-id="open-drawing-link"
              >
                Buka Drawing →
              </button>
            </div>
            <div style={{ marginTop: "var(--space-2)" }}>
              <InfoRow label="Drawing No." value={installation.drawingNo ?? "—"} />
            </div>
          </section>

          <Section id="gland-observation-section" title="Gland Observation">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)" }}>{installation.glandObservationNote}</p>
            <div style={{ marginTop: "var(--space-2)" }}>
              <RefGroup title="Observation Items" items={observationItems(installation.glandObservation)} />
            </div>
          </Section>

          <Section id="sleeve-observation-section" title="Sleeve Observation">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)" }}>{installation.sleeveObservationNote}</p>
            <div style={{ marginTop: "var(--space-2)" }}>
              <RefGroup title="Observation Items" items={observationItems(installation.sleeveObservation)} />
            </div>
          </Section>

          <Section id="retainer-disc-observation-section" title="Retainer / Disc Observation">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)" }}>{installation.retainerDiscObservationNote}</p>
            <div style={{ marginTop: "var(--space-2)" }}>
              <RefGroup title="Observation Items" items={observationItems(installation.retainerDiscObservation)} />
            </div>
          </Section>

          <Section id="cartridge-drive-collar-observation-section" title="Cartridge Drive Collar Observation">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)" }}>{installation.cartridgeDriveCollarObservationNote}</p>
            <div style={{ marginTop: "var(--space-2)" }}>
              <RefGroup title="Observation Items" items={observationItems(installation.cartridgeDriveCollarObservation)} />
            </div>
          </Section>

          {/* No heading is printed above the report's own sign-off block
              -- "Signatures" is a minimal structural caption only, see
              this file's own header comment. */}
          <Section id="signatures-section" title="Signatures">
            <Table
              rowKey="id"
              data={installation.signatures}
              columns={[
                { key: "company", header: "Company" },
                { key: "name", header: "Name", render: (value) => value ?? "—" },
                { key: "title", header: "Title" },
                { key: "date", header: "Date" },
              ]}
            />
          </Section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="equipment-section" title="Equipment">
            <InfoRow label="Plant Equip. No." value={installation.plantEquipNo ?? "—"} />
            <InfoRow label="Model/Type" value={installation.modelType ?? "—"} />
          </RailSection>

          <RailSection id="seal-section" title="Seal">
            <InfoRow label="Seal Manufacture" value={installation.sealManufacture ?? "—"} />
            <InfoRow label="Seal Type" value={installation.sealType ?? "—"} />
            <InfoRow label="Seal Size" value={installation.sealSize ?? "—"} />
          </RailSection>

          <RailSection id="report-date-section" title="Report Date">
            <InfoRow label="Date" value={installation.date ?? "—"} />
            <InfoRow label="Report No." value={installation.reportNo ?? "—"} />
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${installation.reportNo} · ${installation.plantEquipNo}`}
        metaPrimary={installation.customer}
        metaLabel="Date"
        metaValue={installation.date}
      >
        {installation.plantEquipNo && (
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(installation.plantEquipNo)} data-od-id="action-bar-open-pump">
            Open Pump →
          </button>
        )}
        {installation.plantEquipNo && (
          <button type="button" className="btn-link" onClick={() => onOpenLifecycle?.(installation.plantEquipNo)} data-od-id="action-bar-open-lifecycle">
            Open Lifecycle →
          </button>
        )}
        {installation.drawingNo && (
          <button
            type="button"
            className="btn-primary"
            onClick={() => onOpenDrawing?.(installation.drawingNo)}
            data-od-id="action-bar-open-drawing"
          >
            Open Drawing
          </button>
        )}
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="Mechanical Seal Drawing">
        <div className="drawing-thumb" />
        <p>Static preview placeholder — no drawing file/rendering backend exists yet.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}
