import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PM from "./PM";
import { getPMSchedules, getPump, getCMReports, getPMOccurrences, getPMCMEvidence, createPMSchedule, getPumps } from "../../../api/ai5rClient";

// MWO-LTSA-053 -- getCMReports added: PM.jsx now fetches Related CM
// Reports (mirroring Pump.jsx/Seal.jsx's own Related Engineering pattern)
// alongside getPMSchedules, so every test that renders <PM /> now
// triggers this call too.
//
// MWO-LTSA-PM-CM-REVIEW-UI-001 -- getPMOccurrences added: PM.jsx now also
// fetches the real PM Occurrence list on mount (the disclosed gap from
// MWO-LTSA-PM-CM-INTAKE-001's own completion report). Occurrence-specific
// review/evidence flows are covered by PM.occurrence.test.jsx and
// PM.review.test.jsx, same convention as PM.test.jsx's own header note.
// MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- getPMCMEvidence added: the
// new navContext.occurrenceSelectId test renders PMOccurrenceDetailPanel
// directly (no prior test in this file did), which always mounts the
// shared EvidenceAttachments widget -- same mock every other file that
// renders that panel already carries (PM.review.test.jsx,
// ConditionMonitoring.test.jsx).
vi.mock("../../../api/ai5rClient", () => ({
  getPMSchedules: vi.fn(),
  getPump: vi.fn(),
  getCMReports: vi.fn(),
  getPMOccurrences: vi.fn(),
  getPMCMEvidence: vi.fn(),
  createPMSchedule: vi.fn(),
  getPumps: vi.fn(),
}));

function daysFromToday(offset) {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

const PM_SCHEDULES = [
  {
    pm_schedule_code: "PM-2001",
    asset_code: "211-P-1A",
    procedure: "Lubrication & Vibration Check",
    frequency: "MONTHLY",
    trigger_type: "CALENDAR",
    checklist: ["Check oil level", "Grease bearings"],
    last_performed: "2026-06-02",
    next_due: daysFromToday(3),
    assigned_to: "Sari Wulandari",
    estimated_duration_hours: 1.5,
    status: "ACTIVE",
  },
  {
    pm_schedule_code: "PM-2002",
    asset_code: "112-P-3",
    procedure: "Bearing Housing Inspection",
    frequency: "RUNTIME_BASED",
    trigger_type: "METER",
    checklist: ["Open bearing housing"],
    last_performed: "2025-11-18",
    next_due: daysFromToday(-5),
    assigned_to: "Bagus Setiawan",
    estimated_duration_hours: 6,
    status: "ACTIVE",
  },
  {
    pm_schedule_code: "PM-2004",
    asset_code: "150-P-9",
    procedure: "Wear-Plate Inspection",
    frequency: "MONTHLY",
    trigger_type: "CALENDAR",
    checklist: ["Inspect wear plate"],
    last_performed: "2026-06-15",
    next_due: daysFromToday(30),
    assigned_to: "Dedi Kurniawan",
    estimated_duration_hours: 3,
    status: "ACTIVE",
  },
  {
    pm_schedule_code: "PM-2007",
    asset_code: "211-P-1B",
    procedure: "Weekly Standby Auto-Start Test",
    frequency: "WEEKLY",
    trigger_type: "CALENDAR",
    checklist: ["Initiate auto-start sequence"],
    last_performed: "2026-06-20",
    next_due: daysFromToday(60),
    assigned_to: "Sari Wulandari",
    estimated_duration_hours: 0.5,
    status: "ON_HOLD",
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

// UI-D2B -- the registry now renders two representations of the same
// data simultaneously (desktop table + mobile card list, CSS-gated in
// PM.css; jsdom applies no CSS, so both are always in the DOM). Every
// PM-ID that used to be a single unambiguous match is now two -- scope
// existence/click queries to the always-present table (the desktop-
// primary representation). Async: the table doesn't exist until the
// initial getPMSchedules() fetch resolves, so this must use findByRole
// (auto-retrying), never getByRole.
function pmTable() {
  return screen.findByRole("table");
}

function loadPMSchedules(records = PM_SCHEDULES) {
  getPMSchedules.mockResolvedValue(records);
  getPump.mockResolvedValue({ tag_number: null, area: "Boiler House" });
  getCMReports.mockResolvedValue([]);
  getPMOccurrences.mockResolvedValue([]);
  getPumps.mockResolvedValue([{ tag_number: "533-P-1", name: "Standby Transfer Pump" }]);
}

describe("Preventive Maintenance workspace page", () => {
  it("renders the page header", async () => {
    loadPMSchedules();
    render(<PM />);

    expect(screen.getByRole("heading", { name: "PREVENTIVE MAINTENANCE" })).toBeTruthy();
    await within(await pmTable()).findByText("PM-2001");
  });

  it("renders a loading state before the API resolves", () => {
    getPMSchedules.mockReturnValue(new Promise(() => {}));
    getCMReports.mockResolvedValue([]);
    getPMOccurrences.mockResolvedValue([]);
    render(<PM />);

    expect(screen.getByText("Loading PM schedules...")).toBeTruthy();
  });

  it("renders list API errors without fallback mock data", async () => {
    getPMSchedules.mockRejectedValue(new Error("API unavailable"));
    getCMReports.mockResolvedValue([]);
    getPMOccurrences.mockResolvedValue([]);
    render(<PM />);

    expect(await screen.findByText("PM schedules could not be loaded.")).toBeTruthy();
    expect(screen.queryByText("PM-2001")).toBeNull();
  });

  it("renders every PM schedule from the canonical API in the list", async () => {
    loadPMSchedules();
    render(<PM />);

    for (const pm of PM_SCHEDULES) {
      expect(await within(await pmTable()).findByText(pm.pm_schedule_code)).toBeTruthy();
    }
    expect(getPMSchedules).toHaveBeenCalledOnce();
  });

  it("shows an empty state in the detail panel before any PM schedule is selected", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    expect(screen.getByText(/no pm schedule selected/i)).toBeTruthy();
  });

  it("shows the selected PM schedule's detail when a list row is clicked", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2004");

    fireEvent.click(within(await pmTable()).getByText("PM-2004"));

    expect(await screen.findByRole("heading", { name: "PM-2004" })).toBeTruthy();
  });

  it("filters the list by search text", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "wear-plate" } });

    expect(within(await pmTable()).getByText("PM-2004")).toBeTruthy();
    expect(screen.queryByText("PM-2001")).toBeNull();
  });

  // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- DUE_SOON is superseded by
  // the owner-approved PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED
  // lifecycle (pmMapping.js's own computeDisplayStatus); this test now
  // covers OVERDUE (robust: PM-2002's next_due is always 5 days in the
  // past, so always overdue regardless of the current month) and ON_HOLD
  // (a literal stored value, no date math -- always deterministic).
  // Month-boundary-sensitive PLANNED/ACTIVE classification has its own
  // dedicated, explicitly-dated coverage in
  // pmMapping.scheduleLifecycle.test.js and PM.scheduleLifecycle.test.jsx.
  it("computes OVERDUE display status from next_due, never stores it", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    fireEvent.change(screen.getByRole("combobox", { name: "Filter by status" }), { target: { value: "OVERDUE" } });
    expect(within(await pmTable()).getByText("PM-2002")).toBeTruthy();
    expect(screen.queryByText("PM-2001")).toBeNull();

    fireEvent.change(screen.getByRole("combobox", { name: "Filter by status" }), { target: { value: "ON_HOLD" } });
    expect(within(await pmTable()).getByText("PM-2007")).toBeTruthy();
    expect(screen.queryByText("PM-2004")).toBeNull();
  });

  it("shows an empty state in the list when no PM schedule matches the search", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-pm-xyz" } });

    expect(screen.getByText(/no pm schedules match/i)).toBeTruthy();
  });

  it("opens the Create PM Schedule modal when the header action is clicked", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    fireEvent.click(screen.getByRole("button", { name: "+ Create PM Schedule" }));

    expect(screen.getByRole("heading", { name: "Create PM Schedule" })).toBeTruthy();
  });

  it("creates a new PM schedule through the canonical API, closes it, and selects the new entry", async () => {
    loadPMSchedules();
    createPMSchedule.mockResolvedValue({ data: {
      pm_schedule_code: "PM-2008", asset_code: "533-P-1", procedure: "Standard Lubrication",
      frequency: "MONTHLY", trigger_type: "CALENDAR", status: "ACTIVE", checklist: [],
    } });
    render(<PM />);
    await within(await pmTable()).findByText("PM-2007");

    fireEvent.click(screen.getByRole("button", { name: "+ Create PM Schedule" }));
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Standard Lubrication" } });
    fireEvent.change(await screen.findByLabelText("Pump *"), { target: { value: "533-P-1" } });

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: "Create PM Schedule" })).toBeNull());
    expect(screen.getByRole("heading", { name: "PM-2008" })).toBeTruthy();
    // MWO-LTSA-053 -- the new entry is now auto-selected into
    // PMOpenDesignView, so "PM-2008" legitimately appears in both the
    // registry row and the ChromeBar/Hero of the open detail view -- same
    // "expected duplication" pattern Seal.test.jsx's own migration hit.
    expect(screen.getAllByText("PM-2008").length).toBeGreaterThan(0);
    expect(screen.getByRole("status").textContent).toContain("PM-2008 created.");
  });

  it("resolves area per PM schedule by reusing the existing Pump API", async () => {
    loadPMSchedules();
    getPump.mockImplementation((tag) =>
      Promise.resolve({ tag_number: tag, area: tag === "211-P-1A" ? "Boiler House" : null })
    );
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    // UI-D2B -- "Boiler House" also now appears as an <option> in the new
    // Area filter select (derived from the same real, resolved areas) --
    // scope to the table.
    expect(getPump).toHaveBeenCalledWith("211-P-1A");
    expect(within(await pmTable()).getByText("Boiler House")).toBeTruthy();
  });
});

// MWO-LTSA-053 -- PM Workspace Enterprise Upgrade: PMOpenDesignView
// replaces PMDetailPanel, reusing the same LTSA Open Design Kit
// (components/open-design/) Pump.jsx/Seal.jsx already migrated to.
describe("PM Open Design (MWO-LTSA-053)", () => {
  it("renders the full Open Design Information Hierarchy for the selected PM schedule", async () => {
    // UI-D2B -- these sections are now spread across tabs (Overview/
    // Engineering AI/Documents/History) instead of one continuous
    // document; this proves each one is still reachable, tab by tab.
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2004");
    fireEvent.click(within(await pmTable()).getByText("PM-2004"));

    expect(await screen.findByRole("heading", { name: "PM-2004" })).toBeTruthy();
    // Overview tab (default)
    expect(screen.getByText("Schedule & Assignment")).toBeTruthy();
    expect(screen.getByText("LTSA Coverage")).toBeTruthy();
    expect(screen.getByText("Engineering Recommendation")).toBeTruthy();
    // Documents tab
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));
    expect(screen.getAllByText("Documents").length).toBeGreaterThan(0);
    expect(screen.getByText("Document Types")).toBeTruthy();
    // History tab
    fireEvent.click(screen.getByRole("tab", { name: "History" }));
    expect(screen.getByText("Related Engineering")).toBeTruthy();
    // Engineering AI tab
    fireEvent.click(screen.getByRole("tab", { name: "Engineering AI" }));
    expect(screen.getAllByText("Engineering AI").length).toBeGreaterThan(0);
  });

  it("renders the real checklist items inside Engineering Overview, never dropped", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));

    expect(await screen.findByText("Check oil level")).toBeTruthy();
    expect(screen.getByText("Grease bearings")).toBeTruthy();
  });

  it("shows LTSA Covered when the equipment resolves to a real pump (pm.area is non-null)", async () => {
    loadPMSchedules();
    getPump.mockResolvedValue({ tag_number: "211-P-1A", area: "Boiler House" });
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));

    expect((await screen.findAllByText("LTSA Covered")).length).toBeGreaterThan(0);
  });

  it("shows Coverage Unknown, not a fabricated coverage, when the equipment cannot be resolved to a real pump", async () => {
    loadPMSchedules();
    getPump.mockResolvedValue({ tag_number: null, area: null });
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));

    expect((await screen.findAllByText("Coverage Unknown")).length).toBeGreaterThan(0);
  });

  it("shows No recommendation available -- pm_schedule has no recommendation column yet, never fabricated", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));

    expect((await screen.findAllByText("No recommendation available.")).length).toBeGreaterThan(0);
  });

  it("shows Engineering AI as a disclosed placeholder -- no live call, no generated recommendation", async () => {
    // UI-D2B -- Engineering AI now lives under its own tab.
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));
    fireEvent.click(await screen.findByRole("tab", { name: "Engineering AI" }));

    expect(await screen.findByText("Engineering AI has not been integrated for PM Schedules yet.")).toBeTruthy();
  });

  // UI-D2B -- deleted: "navigates to Pump when the ChromeBar equipment
  // link is clicked". This asserted the old ChromeBar breadcrumb's
  // clickable equipment-tag button (bare tag text as a <button>, separate
  // from the Quick Actions "Buka Pump ->" button). The Open Design
  // identity header's <h1> tag (AssetIdentityHeader.jsx) has no click
  // handler and Chief's approved reference has no self-navigating crumb
  // on the identity header -- confirmed via grep that no button renders
  // this case today, same finding already made for Pump/Seal in UI-D1.2.
  // Per this mission's "do not fabricate/invent" and the established
  // precedent, no crumb button was reintroduced just to keep this test
  // green -- the same onNavigate("pump", {selectId}) behavior remains
  // fully covered by the Quick Actions "Buka Pump ->" button, which has
  // no dedicated test of its own here but is exercised identically to
  // Work Order/Pump/Seal's own equivalent buttons.

  it("navigates to Pump when the Quick Actions 'Buka Pump' button is clicked", async () => {
    // UI-D2B -- replaces the deleted ChromeBar-crumb test above with
    // coverage of the button that actually exists now (Overview tab's
    // Quick Actions card), preserving the same real onOpenPump/onNavigate
    // behavior rather than leaving it untested.
    const onNavigate = vi.fn();
    loadPMSchedules();
    render(<PM onNavigate={onNavigate} />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));

    fireEvent.click(await screen.findByText("Buka Pump →"));

    expect(onNavigate).toHaveBeenCalledWith("pump", { selectId: "211-P-1A" });
  });

  it("navigates to Drawing with the equipment tag as context when 'Buka Drawing' is clicked", async () => {
    // UI-D2B -- "Buka Drawing ->" now lives under the Documents tab.
    const onNavigate = vi.fn();
    loadPMSchedules();
    render(<PM onNavigate={onNavigate} />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));
    fireEvent.click(await screen.findByRole("tab", { name: "Documents" }));

    fireEvent.click(await screen.findByText("Buka Drawing →"));

    expect(onNavigate).toHaveBeenCalledWith("drawing", { assetTag: "211-P-1A" });
  });

  it("opens the Create PM Schedule modal from the sticky Action Bar too, reusing the same modal/handler as the header action", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));

    fireEvent.click(await screen.findByRole("button", { name: "Create PM Schedule" }));

    expect(screen.getByRole("heading", { name: "Create PM Schedule" })).toBeTruthy();
  });

  it("derives Related PM from schedules sharing the same equipment tag, excluding itself, from the already-fetched list -- no new fetch", async () => {
    // UI-D2B -- Related Engineering (including Related PM) now lives
    // under the History tab.
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");
    fireEvent.click(within(await pmTable()).getByText("PM-2001"));
    fireEvent.click(await screen.findByRole("tab", { name: "History" }));

    // PM-2001 and PM-2007 both target 211-P-1A/211-P-1B family tags in
    // this fixture only via equipmentTag match -- PM-2001 is 211-P-1A
    // itself, so Related PM must show entries for the *other* schedule(s)
    // sharing that exact tag, not PM-2001 itself.
    expect(screen.queryByText("Related PM")).toBeTruthy();
    expect(getPMSchedules).toHaveBeenCalledOnce();
  });

  it("fetches Related CM Reports via the existing getCMReports() endpoint -- no new API", async () => {
    loadPMSchedules();
    render(<PM />);
    await within(await pmTable()).findByText("PM-2001");

    expect(getCMReports).toHaveBeenCalledOnce();
  });

  it("preserves the navigation chain: selects the matching PM schedule when navContext.assetTag is provided (Drawing/Document -> PM)", async () => {
    loadPMSchedules();
    render(<PM navContext={{ assetTag: "150-P-9" }} />);

    expect(await screen.findByRole("heading", { name: "PM-2004" })).toBeTruthy();
  });

  it("still supports the existing navContext.selectId deep-link (Asset 360), unaffected by the assetTag addition", async () => {
    loadPMSchedules();
    render(<PM navContext={{ selectId: "PM-2004" }} />);

    expect(await screen.findByRole("heading", { name: "PM-2004" })).toBeTruthy();
  });

  // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- this scenario (a real pump,
  // deep-linked, with no matching PM Schedule) now shows the specific "No
  // active PM Schedule is available for this pump." message instead of
  // the generic "No PM schedule selected" -- see the "PM no-schedule flow"
  // describe block below for full coverage. No fabricated selection
  // either way.
  it("does not select any PM schedule when navContext.assetTag matches nothing, no fabricated selection", async () => {
    loadPMSchedules();
    render(<PM navContext={{ assetTag: "999-NO-MATCH" }} />);
    await within(await pmTable()).findByText("PM-2001");

    expect(screen.getByText(/no active pm schedule is available for this pump/i)).toBeTruthy();
  });

  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001
  it("navContext.occurrenceSelectId opens the exact PM occurrence detail directly, even with no matching PM Schedule (historical UNSCHEDULED::* data)", async () => {
    loadPMSchedules();
    getPMCMEvidence.mockResolvedValue([]);
    getPMOccurrences.mockResolvedValue([
      {
        pm_occurrence_code: "LTSA-PMO-7443977B09BE8764",
        pm_schedule_code: "UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx",
        asset_code: "220-P-4A",
        occurrence_date: "2026-06-24",
        status: "DONE",
        activities: [{ code: "1", description: "Flushing Line", side: null, done: true }],
        workflow_status: "DRAFT",
        source_workbook_name: "CM & PM Summary HOC JUNI.xlsx",
        source_sheet_name: " PM Mech Seal",
        source_row_number: 23,
      },
    ]);

    render(<PM navContext={{ occurrenceSelectId: "LTSA-PMO-7443977B09BE8764" }} />);

    expect(await screen.findByRole("heading", { name: "LTSA-PMO-7443977B09BE8764" })).toBeTruthy();
    // No pm_schedule row exists for this UNSCHEDULED::* code -- disclosed
    // honestly, never a fabricated schedule view.
    expect(screen.getByText(/no pm schedule for this occurrence/i)).toBeTruthy();
    // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- the raw UNSCHEDULED::*
    // placeholder is no longer presented under the "PM Schedule" label in
    // PMOccurrenceDetailPanel.jsx (it is provenance, not a real schedule
    // identity) -- superseded by an honest "no linked schedule" message.
    // Provenance itself is still preserved, unmodified, in the Source card.
    expect(screen.queryByText("UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx")).toBeNull();
    expect(screen.getByText(/no linked schedule/i)).toBeTruthy();
    expect(screen.getByText("CM & PM Summary HOC JUNI.xlsx")).toBeTruthy();
  });
});
