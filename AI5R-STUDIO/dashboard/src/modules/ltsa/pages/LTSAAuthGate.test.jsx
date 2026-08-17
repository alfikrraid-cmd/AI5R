import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LTSAAuthGate from "./LTSAAuthGate";

// LTSAWorkspace itself is already covered end-to-end by LTSAWorkspace.test.jsx
// (which mocks the full ai5rClient surface). This suite is scoped to the new
// AUTHENTICATED LTSA SHELL layer only -- login/logout, identity display, and
// that tab visibility is capability-driven -- so LTSAWorkspace is stubbed to
// just surface the props it actually received.
vi.mock("./LTSAWorkspace", () => ({
  default: ({ capabilities }) => (
    <div data-testid="ltsa-workspace-stub">{capabilities.allowedKeys.join(",")}</div>
  ),
}));

// MWO-LTSA-AUTH-002 -- authClient.js now talks to the real AUTH-001
// backend (POST /api/auth/login, GET /api/auth/me); production code no
// longer contains demo identities (Rule 2). This suite supplies its own
// fixtures via the exact same login/getSession/logout contract instead,
// per Rule 2's own "tests may use fixtures/mocks" carve-out -- the real
// module is replaced wholesale for this file, not partially monkey-patched.
const FIXTURES = {
  "admin@tap.co.id": {
    user: { id: "u-tap-admin", email: "admin@tap.co.id", name: "Andra Wicaksono" },
    organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
    role: "TAP_ADMIN",
    permissions: [
      "pump.read", "seal.read", "inventory.read", "maintenance.read", "maintenance.write",
      "condition.read", "drawing.read", "engineering_ai.ask", "import.read", "import.execute",
      "master.edit", "internal_inventory.read", "internal_component.read", "admin.users",
    ],
    token: "fixture.tap-admin",
  },
  "engineer@tap.co.id": {
    user: { id: "u-tap-engineer", email: "engineer@tap.co.id", name: "Rizal Pratama" },
    organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
    role: "TAP_ENGINEER",
    permissions: [
      "pump.read", "seal.read", "inventory.read", "maintenance.read", "maintenance.write",
      "condition.read", "drawing.read", "engineering_ai.ask", "import.read", "import.execute",
      "internal_inventory.read", "internal_component.read",
    ],
    token: "fixture.tap-engineer",
  },
  "budi.santoso@pertamina.com": {
    user: { id: "u-pertamina-engineer", email: "budi.santoso@pertamina.com", name: "Budi Santoso" },
    organization: { id: "org-pertamina-ru2", code: "PERTAMINA_RU_II", displayName: "Pertamina RU II" },
    role: "PERTAMINA_ENGINEER",
    permissions: ["pump.read", "seal.read", "inventory.read", "maintenance.read", "condition.read", "drawing.read", "engineering_ai.ask"],
    token: "fixture.pertamina-engineer",
  },
  "viewer@pertamina.com": {
    user: { id: "u-pertamina-viewer", email: "viewer@pertamina.com", name: "Siti Rahayu" },
    organization: { id: "org-pertamina-ru2", code: "PERTAMINA_RU_II", displayName: "Pertamina RU II" },
    role: "PERTAMINA_VIEWER",
    permissions: ["pump.read", "seal.read", "inventory.read", "maintenance.read"],
    token: "fixture.pertamina-viewer",
  },
};

// inactive@tap.co.id: the backend collapses unknown-user/wrong-password/
// disabled-user into ONE generic invalid_credentials 401 (anti-enumeration
// -- authClient.js's own real login() never distinguishes them). LoginView's
// "inactive" state has no real backend trigger anymore, but Rule 3 requires
// it stay visually reachable, so this fixture-only login exercises it
// directly rather than through authClient's real (now-collapsed) code path.
let mockLoginImpl;

vi.mock("../auth/authClient", () => ({
  login: (...args) => mockLoginImpl(...args),
  getSession: async () => null,
  logout: vi.fn(),
}));

beforeEach(() => {
  window.localStorage.clear();
  mockLoginImpl = async ({ email, password }) => {
    if (email === "inactive@tap.co.id") {
      const error = new Error("inactive_account");
      error.code = "inactive_account";
      throw error;
    }
    const fixture = FIXTURES[email];
    if (!fixture || password !== "demo123") {
      const error = new Error("invalid_credentials");
      error.code = "invalid_credentials";
      throw error;
    }
    return fixture;
  };
});

afterEach(() => {
  window.localStorage.clear();
  vi.clearAllMocks();
});

async function login(email, password = "demo123") {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
}

describe("LTSAAuthGate", () => {
  it("shows the login screen when there is no session", async () => {
    render(<LTSAAuthGate />);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("TAP_ADMIN sees import.execute-gated navigation after login", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("admin@tap.co.id");

    const stub = await screen.findByTestId("ltsa-workspace-stub");
    expect(stub.textContent.split(",")).toEqual(
      expect.arrayContaining(["import", "pump", "seal", "dashboard"])
    );
    expect(await screen.findByText("Andra Wicaksono")).toBeInTheDocument();
    expect(screen.getByText("TAP")).toBeInTheDocument();
  });

  it("PERTAMINA_ENGINEER sees pump/seal/engineering AI but never import", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("budi.santoso@pertamina.com");

    const stub = await screen.findByTestId("ltsa-workspace-stub");
    const allowedKeys = stub.textContent.split(",");
    expect(allowedKeys).toEqual(expect.arrayContaining(["pump", "seal"]));
    expect(allowedKeys).not.toContain("import");
    expect(await screen.findByText("Budi Santoso")).toBeInTheDocument();
    expect(screen.getByText("Pertamina RU II")).toBeInTheDocument();
  });

  it("rejects invalid credentials and stays on the login screen", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("admin@tap.co.id", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent(/incorrect/i);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("rejects an inactive account with an honest status message, not a technical auth error", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("inactive@tap.co.id");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/inactive/i);
    expect(alert.textContent).not.toMatch(/jwt|token|401|500/i);
  });

  it("PERTAMINA_VIEWER signs in successfully with read access but no import", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("viewer@pertamina.com");

    const stub = await screen.findByTestId("ltsa-workspace-stub");
    const allowedKeys = stub.textContent.split(",");
    expect(allowedKeys).toEqual(expect.arrayContaining(["pump", "seal"]));
    expect(allowedKeys).not.toContain("import");
    expect(await screen.findByText("Siti Rahayu")).toBeInTheDocument();
  });

  it("logs out back to the login screen and clears the session", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("engineer@tap.co.id");
    await screen.findByTestId("ltsa-workspace-stub");

    fireEvent.click(screen.getByRole("button", { name: /rizal pratama/i }));
    fireEvent.click(screen.getByRole("button", { name: /log out/i }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
