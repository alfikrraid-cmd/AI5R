import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import QuickNavigationPanel from "./QuickNavigationPanel";
import { AuthProvider } from "../auth/AuthContext";

describe("QuickNavigationPanel", () => {
  it("renders every quick navigation action", () => {
    render(<QuickNavigationPanel onNavigate={() => {}} />);

    // MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- retitled "Quick Actions"
    expect(screen.getByRole("heading", { name: "Quick Actions" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Pump Registry" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Work Orders" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Preventive Maintenance" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Corrective Maintenance" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Asset 360" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Reports" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Analytics" })).toBeTruthy();
  });

  it("calls onNavigate with the correct workspace key for each action", () => {
    const onNavigate = vi.fn();
    render(<QuickNavigationPanel onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Pump Registry" }));
    expect(onNavigate).toHaveBeenCalledWith("pump");

    fireEvent.click(screen.getByRole("button", { name: "Open Work Orders" }));
    expect(onNavigate).toHaveBeenCalledWith("workorder");

    fireEvent.click(screen.getByRole("button", { name: "Open Preventive Maintenance" }));
    expect(onNavigate).toHaveBeenCalledWith("pm");

    fireEvent.click(screen.getByRole("button", { name: "Open Corrective Maintenance" }));
    expect(onNavigate).toHaveBeenCalledWith("cm");

    fireEvent.click(screen.getByRole("button", { name: "Open Asset 360" }));
    expect(onNavigate).toHaveBeenCalledWith("history");

    fireEvent.click(screen.getByRole("button", { name: "Open Reports" }));
    expect(onNavigate).toHaveBeenCalledWith("reports");

    fireEvent.click(screen.getByRole("button", { name: "Open Analytics" }));
    expect(onNavigate).toHaveBeenCalledWith("analytics");
  });
});

// LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- destinations follow the
// signed-in session's capabilities (the same visibleTabKeys source as the
// sidebar).
describe("QuickNavigationPanel capability filtering", () => {
  function renderWithSession(session) {
    const client = { getSession: async () => session, login: vi.fn(), logout: vi.fn() };
    return render(
      <AuthProvider client={client}>
        <QuickNavigationPanel onNavigate={() => {}} />
      </AuthProvider>
    );
  }

  it("a PERTAMINA_ENGINEER is not offered Analytics but keeps its permitted destinations", async () => {
    renderWithSession({
      role: "PERTAMINA_ENGINEER",
      permissions: ["pump.read", "seal.read", "inventory.read", "maintenance.read", "condition.read",
        "drawing.read", "engineering_ai.ask", "dashboard.read"],
    });
    expect(await screen.findByRole("button", { name: "Open Pump Registry" })).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Open Analytics" })).toBeNull());
    expect(screen.getByRole("button", { name: "Open Reports" })).toBeTruthy();
  });

  it("a PERTAMINA_VIEWER is not offered Drawing or Document (no drawing.read)", async () => {
    renderWithSession({ role: "PERTAMINA_VIEWER", permissions: ["pump.read", "seal.read", "inventory.read", "maintenance.read"] });
    expect(await screen.findByRole("button", { name: "Open Pump Registry" })).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Open Drawing" })).toBeNull());
    expect(screen.queryByRole("button", { name: "Open Document" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Open Condition Monitoring" })).toBeNull();
  });
});
