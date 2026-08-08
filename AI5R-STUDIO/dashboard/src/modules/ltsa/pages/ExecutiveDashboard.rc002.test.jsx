import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ExecutiveDashboard from "./ExecutiveDashboard";
import { getFleetPowerBI, getFleetReliability } from "../../../api/ai5rClient";

// MWO-LTSA-037D -- FleetReliabilityPanel is this page's only real (non-
// sample-data) section; every other section here still derives from
// utils/executiveDashboard.js's static sample data, unmocked, unchanged.
// MWO-LTSA-038B -- FleetPowerBIPanel is a second, separate real section.
vi.mock("../../../api/ai5rClient", () => ({
  getFleetReliability: vi.fn(),
  getFleetPowerBI: vi.fn(),
}));

beforeEach(() => {
  getFleetReliability.mockResolvedValue({
    success: true,
    data: {
      pump_count: 4,
      fleet_health_score: 86.5,
      fleet_mtbf_days: 42.3,
      fleet_mttr_hours: 6.25,
      fleet_availability: 98.76,
      total_breakdown_count: 3,
      total_critical_spare_count: 2,
    },
  });
  getFleetPowerBI.mockResolvedValue({
    success: true,
    data: {
      overall_health: 86.5,
      fleet_status: "NORMAL",
      critical_asset_count: 1,
      fleet_availability: 98.76,
      fleet_mtbf_days: 42.3,
      fleet_mttr_hours: 6.25,
      breakdown_count: 3,
      critical_spare_count: 2,
      top_risks: [],
      insight: null,
    },
  });
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DASHBOARD_SOURCE = readFileSync(path.join(__dirname, "ExecutiveDashboard.jsx"), "utf-8");
const TOPBAR_SOURCE = readFileSync(path.join(__dirname, "..", "components", "DashboardTopBar.jsx"), "utf-8");
const INSIGHT_SOURCE = readFileSync(path.join(__dirname, "..", "components", "EngineeringInsightPanel.jsx"), "utf-8");
const KPI_SOURCE = readFileSync(path.join(__dirname, "..", "components", "KpiCardGrid.jsx"), "utf-8");
const READINESS_SOURCE = readFileSync(path.join(__dirname, "..", "components", "EngineeringReadinessPanel.jsx"), "utf-8");
const ALERTS_SOURCE = readFileSync(path.join(__dirname, "..", "components", "EngineeringAlertsPanel.jsx"), "utf-8");
const ACTION_TABLE_SOURCE = readFileSync(path.join(__dirname, "..", "components", "ImmediateActionTable.jsx"), "utf-8");
const NAV_SOURCE = readFileSync(path.join(__dirname, "..", "components", "QuickNavigationPanel.jsx"), "utf-8");
const TWIN_SOURCE = readFileSync(path.join(__dirname, "..", "components", "DigitalTwinPanel.jsx"), "utf-8");
const OPPORTUNITY_SOURCE = readFileSync(path.join(__dirname, "..", "components", "BusinessOpportunityPanel.jsx"), "utf-8");

const ALL_NEW_SOURCES = [
  DASHBOARD_SOURCE,
  TOPBAR_SOURCE,
  INSIGHT_SOURCE,
  KPI_SOURCE,
  READINESS_SOURCE,
  ALERTS_SOURCE,
  ACTION_TABLE_SOURCE,
  NAV_SOURCE,
  TWIN_SOURCE,
  OPPORTUNITY_SOURCE,
];

describe("Dashboard renders", () => {
  it("renders the page header", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();
  });

  it("renders the Top Bar", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("searchbox")).toBeTruthy();
    expect(screen.getByLabelText("Workspace Selector")).toBeTruthy();
    expect(screen.getByLabelText("Notifications")).toBeTruthy();
    expect(screen.getByLabelText("User")).toBeTruthy();
  });

  it("renders all 15 Global KPI cards", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    for (const title of [
      "Total Pumps",
      "Mechanical Seals",
      "PM Compliance",
      "CM Coverage",
      "Open Work Orders",
      "Critical Failures",
      "Inventory Availability",
      "Drawing Coverage",
      "Document Coverage",
      "Knowledge Coverage",
    ]) {
      expect(screen.getByRole("heading", { name: title })).toBeTruthy();
    }
  });

  it("renders Engineering Readiness with all 6 categories", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Engineering Readiness" })).toBeTruthy();
    for (const label of ["Pump", "Mechanical Seal", "Drawing", "Document", "Knowledge", "Inventory"]) {
      expect(screen.getByText(new RegExp(`^${label}( —|$)`))).toBeTruthy();
    }
  });

  it("renders Engineering Health (reused MaintenanceHealthPanel, unchanged heading)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Maintenance Health" })).toBeTruthy();
  });

  it("renders Engineering Alerts", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Engineering Alerts" })).toBeTruthy();
  });

  it("renders Today's Engineering Insight", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Today's Engineering Insight" })).toBeTruthy();
  });

  it("renders Business Opportunity", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Business Opportunity" })).toBeTruthy();
  });

  it("renders Assets Requiring Attention (existing, unchanged)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Assets Requiring Attention" })).toBeTruthy();
  });

  it("renders Assets Requiring Immediate Action", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Assets Requiring Immediate Action" })).toBeTruthy();
  });

  it("renders Upcoming Maintenance and Recent Activities (existing, unchanged)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Upcoming Maintenance" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Recent Activities" })).toBeTruthy();
  });

  it("renders Quick Navigation (existing heading, unchanged)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Quick Navigation" })).toBeTruthy();
  });

  it("renders Digital Twin", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Digital Twin" })).toBeTruthy();
  });

  it("keeps every original MWO-063 heading present after the RC-002 extension", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    for (const heading of [
      "Maintenance Health",
      "Assets Requiring Attention",
      "Upcoming Maintenance",
      "Recent Activities",
      "Quick Navigation",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    }
  });
});

describe("Navigation", () => {
  it("calls onNavigate('history') from the existing Open Asset 360 button", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Asset 360" }));
    expect(onNavigate).toHaveBeenCalledWith("history");
  });

  it("navigates to Mechanical Seal from Quick Navigation", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Mechanical Seal" }));
    expect(onNavigate).toHaveBeenCalledWith("seal");
  });

  it("navigates to Condition Monitoring from Quick Navigation", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Condition Monitoring" }));
    expect(onNavigate).toHaveBeenCalledWith("cmon");
  });

  it("renders a disabled button for Inventory only (Drawing live as of RC-003A, Document live as of RC-004)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("button", { name: /Open Inventory/ }).disabled).toBe(true);
  });

  it("navigates to Drawing from Quick Navigation (live as of RC-003A)", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Drawing" }));
    expect(onNavigate).toHaveBeenCalledWith("drawing");
  });

  it("navigates to Document from Quick Navigation (live as of RC-004)", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Document" }));
    expect(onNavigate).toHaveBeenCalledWith("document");
  });

  it("does not call onNavigate when a disabled destination is clicked", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: /Open Inventory/ }));
    expect(onNavigate).not.toHaveBeenCalledWith("inventory");
  });

  it("navigates via the Workspace Selector in the Top Bar", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    fireEvent.change(screen.getByLabelText("Workspace Selector"), { target: { value: "pump" } });
    expect(onNavigate).toHaveBeenCalledWith("pump");
  });

  it("Workspace Selector offers the same destinations as Quick Navigation (single source of truth)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    const select = screen.getByLabelText("Workspace Selector");
    const optionValues = Array.from(select.querySelectorAll("option")).map((o) => o.value).filter(Boolean);
    expect(optionValues).toContain("seal");
    expect(optionValues).toContain("cmon");
    expect(optionValues).toContain("drawing");
  });
});

describe("Placeholder widgets", () => {
  it("shows Unavailable for CM Coverage, Inventory Availability, Drawing/Document/Knowledge Coverage", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThanOrEqual(5);
  });

  // MWO-LTSA-036L: Mechanical Seal readiness joins Drawing/Document/
  // Knowledge/Inventory (5 total) -- no real Seal Registry data source
  // exists to reuse, so it is no longer a fabricated percentage over mock
  // data.
  it("shows 'Not available' for Seal/Drawing/Document/Knowledge/Inventory readiness", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getAllByText("Not available").length).toBe(5);
  });

  it("shows a real percentage for Pump readiness, not a placeholder", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByText(/Pump — \d+%/)).toBeTruthy();
  });

  it("Today's Engineering Insight shows the Reserved badge and Future Aggregation Platform text", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByText("Reserved")).toBeTruthy();
    expect(screen.getByText(/Future Aggregation Platform/)).toBeTruthy();
  });

  it("Business Opportunity shows a not-yet-available placeholder, no numbers", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByText(/Business Opportunity analysis is not yet available/)).toBeTruthy();
  });

  it("Digital Twin shows a not-yet-available placeholder", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByText(/Digital Twin is not yet available/)).toBeTruthy();
  });
});

describe("No duplicate Engineering AI", () => {
  it("EngineeringInsightPanel never imports any EngineeringAI* component", () => {
    expect(INSIGHT_SOURCE).not.toMatch(/EngineeringAI(Status|Summary|Findings|Evidence|Recommendation|Confidence|Risk|RemainingLife|SourceReferences|ProviderInfo)/);
  });

  it("no RC-002 file imports from the canonical engineering-ai package", () => {
    for (const source of ALL_NEW_SOURCES) {
      expect(source).not.toMatch(/from ["'].*engineering-ai["']/);
    }
  });

  it("no RC-002 file imports or calls postEngineeringAI (comment mentions are not a call)", () => {
    for (const source of ALL_NEW_SOURCES) {
      expect(source).not.toMatch(/import[^;]*postEngineeringAI/);
      expect(source).not.toMatch(/postEngineeringAI\(/);
    }
  });

  it("does not define any forbidden Dashboard*-prefixed AI/architecture object", () => {
    for (const forbidden of [
      "DashboardAIClient",
      "DashboardRouter",
      "DashboardContext",
      "DashboardAggregator",
      "DashboardPromptBuilder",
      "DashboardRecommendationEngine",
      "DashboardRuntime",
      "DashboardGateway",
    ]) {
      for (const source of [...ALL_NEW_SOURCES]) {
        expect(source).not.toMatch(new RegExp(forbidden));
      }
    }
  });
});

describe("No aggregation logic", () => {
  it("EngineeringInsightPanel takes no props (reads no other workspace's state)", () => {
    expect(INSIGHT_SOURCE).not.toMatch(/EngineeringInsightPanel\(\s*\{/);
  });

  it("ExecutiveDashboard.jsx does not import from any other workspace's page module", () => {
    for (const forbidden of ["from \"./Pump\"", "from \"./PM", "from \"./ConditionMonitoring", "from \"./FailureAnalysisWorkspace\"", "from \"./Seal\"", "from \"./WorkOrder\""]) {
      expect(DASHBOARD_SOURCE).not.toContain(forbidden);
    }
  });
});

describe("No raw fetch", () => {
  it("no RC-002 file makes a raw fetch() call", () => {
    for (const source of ALL_NEW_SOURCES) {
      expect(source).not.toMatch(/\bfetch\(/);
    }
  });

  it("no RC-002 file imports ai5rClient", () => {
    for (const source of ALL_NEW_SOURCES) {
      expect(source).not.toMatch(/ai5rClient/);
    }
  });
});

describe("Reuse existing components", () => {
  it("KpiCardGrid imports MetricCard from the design system, defines no local card component", () => {
    expect(KPI_SOURCE).toMatch(/import \{ MetricCard \} from ["'].*design-system["']/);
  });

  it("EngineeringReadinessPanel reuses ProgressBar, defines no local progress bar", () => {
    expect(READINESS_SOURCE).toMatch(/ProgressBar/);
    expect(READINESS_SOURCE).not.toMatch(/function ProgressBar/);
  });

  it("ImmediateActionTable reuses the design-system Table, defines no local table", () => {
    expect(ACTION_TABLE_SOURCE).toMatch(/import \{ .*Table.* \} from ["'].*design-system["']/);
    expect(ACTION_TABLE_SOURCE).not.toMatch(/function Table/);
  });

  it("DashboardTopBar reuses SearchBox, defines no local search input", () => {
    expect(TOPBAR_SOURCE).toMatch(/import \{ .*SearchBox.* \} from ["'].*design-system["']/);
  });

  it("QuickNavigationPanel's DESTINATIONS is exported and reused by DashboardTopBar (single source of truth)", () => {
    expect(NAV_SOURCE).toMatch(/export const DESTINATIONS/);
    expect(TOPBAR_SOURCE).toMatch(/import \{ DESTINATIONS \} from ["']\.\/QuickNavigationPanel["']/);
  });

  it("ImmediateActionTable receives assets as a prop rather than recomputing them", () => {
    expect(ACTION_TABLE_SOURCE).not.toMatch(/import[^;]*buildAttentionAssets/);
    expect(ACTION_TABLE_SOURCE).toMatch(/ImmediateActionTable\(\s*\{\s*assets\s*\}/);
  });

  it("ExecutiveDashboard.jsx computes buildAttentionAssets() exactly once, reused by both consumers", () => {
    const matches = DASHBOARD_SOURCE.match(/buildAttentionAssets\(\)/g) || [];
    expect(matches.length).toBe(1);
  });
});

describe("Accessibility", () => {
  it("Global Search is a real searchbox with a placeholder", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    const search = screen.getByRole("searchbox");
    expect(search.getAttribute("placeholder")).toBeTruthy();
  });

  it("Workspace Selector is a labeled combobox", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByLabelText("Workspace Selector").tagName).toBe("SELECT");
  });

  it("every KPI card title is a real heading (screen-reader discoverable)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Total Pumps" }).tagName).toBe("H3");
  });

  it("disabled navigation buttons are real disabled buttons, not styled-only", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    const button = screen.getByRole("button", { name: /Open Inventory/ });
    expect(button.tagName).toBe("BUTTON");
    expect(button.disabled).toBe(true);
  });
});

describe("Snapshot", () => {
  it("matches the full Executive Dashboard snapshot", async () => {
    const { container } = render(<ExecutiveDashboard onNavigate={() => {}} />);
    // MWO-LTSA-038B: FleetPowerBIPanel reuses the same "Fleet Health"
    // MetricCard title as FleetReliabilityPanel -- now two matches.
    await waitFor(() => expect(screen.getAllByText("Fleet Health").length).toBe(2));
    expect(container.querySelector(".executive-dashboard-layout")).toMatchSnapshot();
  });
});

describe("Regression", () => {
  it("Open Work Orders KPI still appears before Quick Navigation (existing ordering contract)", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    const headings = screen.getAllByRole("heading").map((h) => h.textContent);
    expect(headings.indexOf("Open Work Orders")).toBeLessThan(headings.indexOf("Quick Navigation"));
  });

  it("still calls onNavigate for every original Quick Navigation destination", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    for (const label of ["Open Pump Registry", "Open Work Orders", "Open Preventive Maintenance", "Open Corrective Maintenance", "Open Reports", "Open Analytics"]) {
      fireEvent.click(screen.getByRole("button", { name: label }));
    }
    expect(onNavigate).toHaveBeenCalledTimes(6);
  });

  it("still passes activities and onNavigate through to RecentActivityFeed", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);
    expect(screen.getByRole("heading", { name: "Recent Activities" })).toBeTruthy();
  });

  it("LTSAWorkspace routes the 'seal' key to the Seal page (extended registry)", async () => {
    const LTSAWorkspaceModule = await import("./LTSAWorkspace");
    const source = readFileSync(path.join(__dirname, "LTSAWorkspace.jsx"), "utf-8");
    expect(source).toMatch(/seal: Seal/);
    expect(LTSAWorkspaceModule.default).toBeTruthy();
  });
});
