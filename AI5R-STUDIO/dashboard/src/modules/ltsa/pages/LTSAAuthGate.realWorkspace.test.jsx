import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LTSAAuthGate from "./LTSAAuthGate";

// LTSA_PERTAMINA_ENGINEER_REACT_130_FIX_R4 -- the other LTSAAuthGate suites
// stub LTSAWorkspace, which hid the production crash: for every role without
// dashboard access, LTSAAuthGate landed on a key with no PAGES entry and the
// REAL LTSAWorkspace rendered an undefined component (React #130, blank
// /ltsa). This suite keeps LTSAAuthGate -> LTSAWorkspace -> ActivePage real
// and mocks only the network edge (authClient + the page's data calls).

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

vi.mock("../../../api/ai5rClient", async (importOriginal) => ({
  ...(await importOriginal()),
  getPumps: vi.fn().mockResolvedValue([]),
  getPump: vi.fn().mockResolvedValue({ tag_number: null, area: null }),
  getPumpLifecycle: vi.fn().mockResolvedValue([]),
  getSeals: vi.fn().mockResolvedValue([]),
  getSealCompatibility: vi.fn().mockResolvedValue([]),
  getCMReports: vi.fn().mockResolvedValue([]),
  postEngineeringAI: vi.fn().mockResolvedValue({}),
}));

// Verbatim CORE-SERVICES/API/auth_service.py ROLE_PERMISSIONS for the three
// roles that previously crashed, as GET /api/auth/me serves them.
const BACKEND_PERMISSIONS = {
  PERTAMINA_ENGINEER: [
    "condition.read", "drawing.read", "engineering_ai.ask", "inventory.read",
    "maintenance.read", "pump.read", "seal.read",
  ],
  PERTAMINA_VIEWER: ["inventory.read", "maintenance.read", "pump.read", "seal.read"],
  JOHN_CRANE_ENGINEER: [
    "condition.read", "drawing.read", "engineering_ai.ask", "internal_component.read",
    "inventory.read", "maintenance.read", "maintenance.technical_review", "pump.read", "seal.read",
  ],
};

function session(role, mustChange) {
  return {
    user: { id: "u-bagus", email: null, username: "bagus", name: "Bagus A.D" },
    organization: { id: "org-pertamina", code: "PERTAMINA", displayName: "PERTAMINA" },
    role,
    permissions: BACKEND_PERMISSIONS[role],
    data_scope_type: "ALL",
    data_scope_value: null,
    must_change_password: mustChange,
    token: mustChange ? "token.first-login" : "token.fresh",
  };
}

let consoleError;

function expectNoInvalidElementType() {
  const messages = consoleError.mock.calls.map((args) => args.map(String).join(" "));
  expect(messages.filter((message) => /Element type is invalid|Minified React error #130/.test(message))).toEqual([]);
}

beforeEach(() => {
  window.history.pushState({}, "", "/ltsa");
  consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  consoleError.mockRestore();
  vi.clearAllMocks();
});

describe("LTSAAuthGate -> real LTSAWorkspace landing (LTSA_PERTAMINA_ENGINEER_REACT_130_FIX_R4)", () => {
  it.each(Object.keys(BACKEND_PERMISSIONS))(
    "%s: forced first-login password change lands on the real Pump workspace, not a blank page",
    async (role) => {
      mockClient.getSession.mockResolvedValue(null);
      mockClient.login.mockResolvedValue(session(role, true));
      mockClient.changePassword.mockResolvedValue(session(role, false));

      render(<LTSAAuthGate />);
      await screen.findByRole("heading", { name: "Sign in" });
      fireEvent.change(screen.getByLabelText("Username or Email"), { target: { value: "bagus" } });
      fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Temp-Passw0rd-2026" } });
      fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

      await screen.findByTestId("forced-change-password");
      fireEvent.change(screen.getByLabelText("Current / Temporary Password"), { target: { value: "Temp-Passw0rd-2026" } });
      fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "Chosen-Passw0rd-2026" } });
      fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "Chosen-Passw0rd-2026" } });
      fireEvent.click(screen.getByTestId("change-password-submit"));

      expect(await screen.findByText("Pump Workspace")).toBeInTheDocument();
      expect(screen.queryByTestId("forced-change-password")).toBeNull();
      expect(mockClient.changePassword).toHaveBeenCalledWith("Temp-Passw0rd-2026", "Chosen-Passw0rd-2026");
      expect(window.location.pathname).toBe("/ltsa/pump");
      expectNoInvalidElementType();
    }
  );

  it("PERTAMINA_ENGINEER: reload of /ltsa with an existing session (GET /api/auth/me) renders the real Pump workspace", async () => {
    mockClient.getSession.mockResolvedValue(session("PERTAMINA_ENGINEER", false));

    render(<LTSAAuthGate />);

    expect(await screen.findByText("Pump Workspace")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/ltsa/pump");
    expectNoInvalidElementType();
  });
});
