import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LTSAAuthGate from "./LTSAAuthGate";

// LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- the forced first-login screen is
// rendered by LTSAAuthGate before AuthenticatedLTSA, so none of the
// authenticated shells below may render while must_change_password is true.
vi.mock("./LTSAWorkspace", () => ({ default: () => <div data-testid="ltsa-workspace-stub" /> }));
vi.mock("./AdminUsersView", () => ({ default: () => <div data-testid="admin-users-view-stub" /> }));
vi.mock("./MyProfileView", () => ({ default: () => <div data-testid="my-profile-view-stub" /> }));

const mockClient = {
  getSession: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
};

vi.mock("../auth/authClient", () => ({
  getSession: (...args) => mockClient.getSession(...args),
  login: (...args) => mockClient.login(...args),
  logout: (...args) => mockClient.logout(...args),
  changePassword: (...args) => mockClient.changePassword(...args),
}));

function session(mustChange) {
  return {
    user: { id: "u-new", email: "new.user@tap.internal", username: "new.user", name: "New User" },
    organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
    role: "TAP_ENGINEER",
    permissions: ["pump.read", "maintenance.read", "internal_inventory.read", "dashboard.read"],
    must_change_password: mustChange,
    token: mustChange ? "token.first-login" : "token.fresh",
  };
}

const AUTHENTICATED_SHELLS = ["ltsa-workspace-stub", "admin-users-view-stub", "my-profile-view-stub"];

function expectNoAuthenticatedShell() {
  for (const testId of AUTHENTICATED_SHELLS) {
    expect(screen.queryByTestId(testId)).toBeNull();
  }
}

async function signIn() {
  await screen.findByRole("heading", { name: "Sign in" });
  fireEvent.change(screen.getByLabelText("Username or Email"), { target: { value: "new.user" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Temp-Passw0rd-2026" } });
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
}

function fillForm({ current = "Temp-Passw0rd-2026", next = "Chosen-Passw0rd-2026", confirm = next } = {}) {
  fireEvent.change(screen.getByLabelText("Current / Temporary Password"), { target: { value: current } });
  fireEvent.change(screen.getByLabelText("New Password"), { target: { value: next } });
  fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: confirm } });
  fireEvent.click(screen.getByTestId("change-password-submit"));
}

beforeEach(() => {
  window.history.pushState({}, "", "/ltsa");
  mockClient.getSession.mockResolvedValue(null);
  mockClient.login.mockResolvedValue(session(true));
  mockClient.changePassword.mockResolvedValue(session(false));
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("LTSAAuthGate forced first-login password change", () => {
  it("a normal user goes straight to the workspace", async () => {
    mockClient.login.mockResolvedValue(session(false));
    render(<LTSAAuthGate />);
    await signIn();
    expect(await screen.findByTestId("ltsa-workspace-stub")).toBeInTheDocument();
    expect(screen.queryByTestId("forced-change-password")).toBeNull();
  });

  it("a flagged user sees the forced change-password screen after sign-in", async () => {
    render(<LTSAAuthGate />);
    await signIn();
    expect(await screen.findByTestId("forced-change-password")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Change your password" })).toBeInTheDocument();
    expect(
      screen.getByText("For security, you must create a new password before continuing to LTSA.")
    ).toBeInTheDocument();
    expectNoAuthenticatedShell();
  });

  it("a reload with a flagged session still shows the forced screen", async () => {
    mockClient.getSession.mockResolvedValue(session(true));
    render(<LTSAAuthGate />);
    expect(await screen.findByTestId("forced-change-password")).toBeInTheDocument();
    expectNoAuthenticatedShell();
  });

  it.each(["/ltsa/profile", "/ltsa/admin/users", "/ltsa/pump/211-P-13A", "/ltsa/history"])(
    "deep link %s cannot bypass the forced screen",
    async (path) => {
      window.history.pushState({}, "", path);
      mockClient.getSession.mockResolvedValue(session(true));
      render(<LTSAAuthGate />);
      expect(await screen.findByTestId("forced-change-password")).toBeInTheDocument();
      expectNoAuthenticatedShell();
    }
  );

  it("a wrong current password shows a safe error and does not sign the user out", async () => {
    const error = new Error("incorrect_current_password");
    error.code = "incorrect_current_password";
    mockClient.changePassword.mockRejectedValue(error);
    render(<LTSAAuthGate />);
    await signIn();
    await screen.findByTestId("forced-change-password");

    fillForm({ current: "Wrong-Passw0rd-2026" });

    expect(await screen.findByTestId("change-password-error")).toHaveTextContent("Current password is incorrect.");
    expect(screen.getByTestId("forced-change-password")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
    expect(mockClient.logout).not.toHaveBeenCalled();
    expectNoAuthenticatedShell();
  });

  it("a confirmation mismatch is blocked before any request", async () => {
    render(<LTSAAuthGate />);
    await signIn();
    await screen.findByTestId("forced-change-password");

    fillForm({ confirm: "Different-Passw0rd-2026" });

    expect(screen.getByTestId("change-password-error")).toHaveTextContent("New passwords do not match.");
    expect(mockClient.changePassword).not.toHaveBeenCalled();
  });

  it("a policy violation is blocked before any request", async () => {
    render(<LTSAAuthGate />);
    await signIn();
    await screen.findByTestId("forced-change-password");

    fillForm({ next: "short", confirm: "short" });

    expect(screen.getByTestId("change-password-error")).toHaveTextContent("at least 12 characters");
    expect(mockClient.changePassword).not.toHaveBeenCalled();
  });

  it("a successful change stores the fresh session and opens the workspace", async () => {
    render(<LTSAAuthGate />);
    await signIn();
    await screen.findByTestId("forced-change-password");

    fillForm();

    await waitFor(() =>
      expect(mockClient.changePassword).toHaveBeenCalledWith("Temp-Passw0rd-2026", "Chosen-Passw0rd-2026")
    );
    expect(await screen.findByTestId("ltsa-workspace-stub")).toBeInTheDocument();
    expect(screen.queryByTestId("forced-change-password")).toBeNull();
  });

  it("Log out is the only way out of the forced screen", async () => {
    render(<LTSAAuthGate />);
    await signIn();
    await screen.findByTestId("forced-change-password");

    fireEvent.click(screen.getByRole("button", { name: "Log out" }));

    expect(mockClient.logout).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
