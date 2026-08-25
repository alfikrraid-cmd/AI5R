import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AdminUsersView from "./AdminUsersView";
import {
  createAdminUser,
  getAdminUsers,
  resetAdminUserPassword,
  updateAdminUserRole,
  updateAdminUserStatus,
} from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getAdminUsers: vi.fn(),
  createAdminUser: vi.fn(),
  updateAdminUserStatus: vi.fn(),
  updateAdminUserRole: vi.fn(),
  resetAdminUserPassword: vi.fn(),
}));

const SAMPLE_USERS = [
  {
    id: "u-1", username: "tapeng", email: "tap-eng@tap.internal", status: "ACTIVE",
    created_at: "2026-01-01T00:00:00", updated_at: "2026-01-02T00:00:00",
    organization_id: "org-tap", organization_code: "TAP",
    role: "TAP_ENGINEER", membership_status: "ACTIVE",
  },
  {
    id: "u-2", username: "superuser", email: null, status: "ACTIVE",
    created_at: "2026-01-01T00:00:00", updated_at: "2026-01-01T00:00:00",
    organization_id: "org-tap", organization_code: "TAP",
    role: "SUPERUSER", membership_status: "ACTIVE",
  },
];

const TAP_ADMIN_SESSION = {
  role: "TAP_ADMIN",
  organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
};

const SUPERUSER_SESSION = {
  role: "SUPERUSER",
  organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
};

beforeEach(() => {
  vi.clearAllMocks();
  getAdminUsers.mockResolvedValue(SAMPLE_USERS);
  updateAdminUserStatus.mockResolvedValue({});
  updateAdminUserRole.mockResolvedValue({});
  resetAdminUserPassword.mockResolvedValue({});
  createAdminUser.mockResolvedValue({});
  vi.spyOn(window, "prompt").mockReturnValue("a-new-password");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AdminUsersView authorization gate", () => {
  it("renders a not-authorized state and never calls the API when canManageUsers is false", () => {
    render(<AdminUsersView canManageUsers={false} />);
    expect(screen.getByTestId("admin-users-denied")).toBeTruthy();
    expect(getAdminUsers).not.toHaveBeenCalled();
  });
});

describe("AdminUsersView list", () => {
  it("renders every user's username, email, role, organization, and status", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());

    expect(screen.getByText("superuser")).toBeTruthy();
    expect(screen.getAllByText("TAP").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ACTIVE").length).toBeGreaterThan(0);
  });

  it("shows username and N/A for a null email", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("superuser")).toBeTruthy());

    expect(screen.getByText("tapeng")).toBeTruthy();
    expect(screen.getByText("N/A")).toBeTruthy();
  });
  it("never renders a password or password_hash field anywhere", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());
    expect(screen.queryByText(/password_hash/i)).toBeNull();
  });

  it("shows created_at/updated_at (Record Attribution) but not a full audit timeline", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());
    expect(screen.getAllByText("2026-01-01T00:00:00").length).toBeGreaterThan(0);
  });
});

describe("AdminUsersView actions", () => {
  it("does not show an API-unavailable state when TAP_ADMIN sees unmanageable rows", async () => {
    render(<AdminUsersView canManageUsers={true} session={TAP_ADMIN_SESSION} />);
    await waitFor(() => expect(screen.getByText("tapeng")).toBeTruthy());

    expect(screen.queryByText(/Admin Users API unavailable/i)).toBeNull();
    expect(screen.getAllByText("Read-only").length).toBe(1);
  });

  it("auto-resolves TAP_ADMIN organization and removes the raw Organization ID input", async () => {
    render(<AdminUsersView canManageUsers={true} session={TAP_ADMIN_SESSION} />);
    await waitFor(() => expect(screen.getByText("tapeng")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));

    expect(screen.getByTestId("admin-users-organization-display").textContent).toContain("Organization: TAP");
    expect(screen.queryByLabelText("Organization ID")).toBeNull();
  });

  it("limits TAP_ADMIN create role choices to authorized roles", async () => {
    render(<AdminUsersView canManageUsers={true} session={TAP_ADMIN_SESSION} />);
    await waitFor(() => expect(screen.getByText("tapeng")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));
    const options = Array.from(screen.getByLabelText("Role").querySelectorAll("option")).map((option) => option.value);

    expect(options).toEqual(["TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"]);
    expect(options).not.toContain("SUPERUSER");
    expect(options).not.toContain("TAP_ADMIN");
  });

  it("TAP_ADMIN creates username-only users with the current organization id", async () => {
    render(<AdminUsersView canManageUsers={true} session={TAP_ADMIN_SESSION} />);
    await waitFor(() => expect(screen.getByText("tapeng")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "ravi" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "temp-pw" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() =>
      expect(createAdminUser).toHaveBeenCalledWith({
        username: "ravi", email: null, password: "temp-pw", organizationId: "org-tap", role: "TAP_ENGINEER",
      })
    );
  });

  it("keeps SUPERUSER role choices unchanged", async () => {
    render(<AdminUsersView canManageUsers={true} session={SUPERUSER_SESSION} />);
    await waitFor(() => expect(screen.getByText("tapeng")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));
    const options = Array.from(screen.getByLabelText("Role").querySelectorAll("option")).map((option) => option.value);

    expect(options).toEqual(["SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"]);
  });
  it("disabling an active user calls updateAdminUserStatus with DISABLED", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());

    const disableButtons = screen.getAllByText("Disable");
    fireEvent.click(disableButtons[0]);

    await waitFor(() => expect(updateAdminUserStatus).toHaveBeenCalledWith("u-1", "DISABLED"));
  });

  it("a 409 last-superuser error from the backend is surfaced verbatim, not swallowed", async () => {
    updateAdminUserStatus.mockRejectedValueOnce(new Error("cannot disable: this is the last active SUPERUSER account"));
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("superuser")).toBeTruthy());

    const disableButtons = screen.getAllByText("Disable");
    fireEvent.click(disableButtons[1]);

    await waitFor(() =>
      expect(screen.getByTestId("admin-users-action-error").textContent).toMatch(/last active SUPERUSER/)
    );
  });

  it("a 403 delegation-denied error from the backend is surfaced verbatim", async () => {
    updateAdminUserRole.mockRejectedValueOnce(new Error("TAP_ADMIN is not authorized to manage SUPERUSER accounts"));
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());

    fireEvent.change(screen.getByLabelText("Change role for tapeng"), { target: { value: "SUPERUSER" } });

    await waitFor(() =>
      expect(screen.getByTestId("admin-users-action-error").textContent).toMatch(/not authorized to manage SUPERUSER/)
    );
  });

  it("password reset prompts for a new password and never displays it in the DOM afterwards", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());

    fireEvent.click(screen.getAllByText("Reset Password")[0]);

    await waitFor(() => expect(resetAdminUserPassword).toHaveBeenCalledWith("u-1", "a-new-password"));
    expect(screen.queryByText("a-new-password")).toBeNull();
  });

  // MWO-LTSA-ADMIN-USERS-WIRING-001 -- Phase 5: JOHN_CRANE organization gap.
  it("shows a visible warning when JOHN_CRANE_ENGINEER is selected, never silently assigning an organization", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));
    expect(screen.queryByTestId("admin-users-jc-org-warning")).toBeNull();

    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "JOHN_CRANE_ENGINEER" } });

    expect(screen.getByTestId("admin-users-jc-org-warning")).toBeTruthy();
    // Organization ID stays whatever the operator typed -- never auto-filled.
    expect(screen.getByLabelText("Organization ID").value).toBe("");
  });

  it("creating a user submits the form fields to createAdminUser", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tap-eng@tap.internal")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "ravi" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@tap.internal" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "temp-pw" } });
    fireEvent.change(screen.getByLabelText("Organization ID"), { target: { value: "org-tap" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() =>
      expect(createAdminUser).toHaveBeenCalledWith({
        username: "ravi", email: "new@tap.internal", password: "temp-pw", organizationId: "org-tap", role: "TAP_ENGINEER",
      })
    );
  });

  it("creating a username-only user submits null email", async () => {
    render(<AdminUsersView canManageUsers={true} />);
    await waitFor(() => expect(screen.getByText("tapeng")).toBeTruthy());

    fireEvent.click(screen.getByText("Create User"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "ravi" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "temp-pw" } });
    fireEvent.change(screen.getByLabelText("Organization ID"), { target: { value: "org-tap" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() =>
      expect(createAdminUser).toHaveBeenCalledWith({
        username: "ravi", email: null, password: "temp-pw", organizationId: "org-tap", role: "TAP_ENGINEER",
      })
    );
  });
});
