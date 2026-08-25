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

// MWO-LTSA-ADMIN-USERS-WIRING-001 -- AdminUsersView itself is already
// fully tested (AdminUsersView.test.jsx); this suite only proves the
// GATE (capability-driven visibility + direct-route security), the same
// "stub the child, test the shell" split this file already establishes
// for LTSAWorkspace above.
vi.mock("./AdminUsersView", () => ({
  default: ({ canManageUsers }) => (
    <div data-testid="admin-users-view-stub">{String(canManageUsers)}</div>
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
  // MWO-LTSA-AUTH-003A-FINAL roles.
  "su@tap.co.id": {
    user: { id: "u-superuser", email: "su@tap.co.id", name: "Sari Wulandari" },
    organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
    role: "SUPERUSER",
    permissions: [
      "pump.read", "seal.read", "inventory.read", "maintenance.read", "maintenance.write",
      "maintenance.technical_review", "maintenance.admin_review", "condition.read", "drawing.read",
      "engineering_ai.ask", "import.read", "import.execute", "master.edit", "internal_inventory.read",
      "internal_component.read", "installation.write", "installation.review",
      "admin.users", "admin.superuser", "audit.read_full",
    ],
    token: "fixture.superuser",
  },
  "jc@johncrane.internal": {
    user: { id: "u-jc-engineer", email: "jc@johncrane.internal", name: "Kenji Watanabe" },
    organization: { id: "org-tap", code: "TAP", displayName: "TAP" },
    role: "JOHN_CRANE_ENGINEER",
    permissions: [
      "pump.read", "seal.read", "inventory.read", "maintenance.read", "maintenance.technical_review",
      "condition.read", "drawing.read", "engineering_ai.ask", "internal_component.read",
    ],
    token: "fixture.jc-engineer",
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
  window.history.pushState({}, "", "/ltsa");
  window.localStorage.clear();
  mockLoginImpl = async ({ identifier, email, password }) => {
    email = identifier ?? email;
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
  fireEvent.change(screen.getByLabelText("Username or Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
}

describe("LTSAAuthGate", () => {
  it("shows the login screen when there is no session", async () => {
    render(<LTSAAuthGate />);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });


  it("renders the official AI5R logo in the header and links it back to LTSA workspace", async () => {
    window.history.pushState({}, "", "/ltsa/admin/users");
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("admin@tap.co.id");
    await screen.findByTestId("admin-users-view-stub");

    const logo = screen.getAllByRole("img", { name: "AI5R" }).find((node) => node.getAttribute("width") === "28");
    expect(logo).toHaveAttribute("src", "/favicon.svg");
    expect(logo).toHaveAttribute("height", "27");

    fireEvent.click(screen.getByRole("button", { name: "Open LTSA workspace" }));
    expect(window.location.pathname).toBe("/ltsa");
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

// MWO-LTSA-ADMIN-USERS-WIRING-001
describe("Admin Users navigation visibility (capability-driven, never role === \"...\")", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/ltsa");
  });

  async function loginAndOpenMenu(email, nameMatch) {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login(email);
    await screen.findByText(nameMatch);
    fireEvent.click(screen.getByRole("button", { name: new RegExp(nameMatch, "i") }));
  }

  it("SUPERUSER sees the Admin — Users menu item", async () => {
    await loginAndOpenMenu("su@tap.co.id", "Sari Wulandari");
    expect(screen.getByText("Admin — Users")).toBeInTheDocument();
  });

  it("TAP_ADMIN sees the Admin — Users menu item", async () => {
    await loginAndOpenMenu("admin@tap.co.id", "Andra Wicaksono");
    expect(screen.getByText("Admin — Users")).toBeInTheDocument();
  });

  it("TAP_ENGINEER does not see the Admin — Users menu item", async () => {
    await loginAndOpenMenu("engineer@tap.co.id", "Rizal Pratama");
    expect(screen.queryByText("Admin — Users")).not.toBeInTheDocument();
  });

  it("JOHN_CRANE_ENGINEER does not see the Admin — Users menu item", async () => {
    await loginAndOpenMenu("jc@johncrane.internal", "Kenji Watanabe");
    expect(screen.queryByText("Admin — Users")).not.toBeInTheDocument();
  });

  it("PERTAMINA_ENGINEER does not see the Admin — Users menu item", async () => {
    await loginAndOpenMenu("budi.santoso@pertamina.com", "Budi Santoso");
    expect(screen.queryByText("Admin — Users")).not.toBeInTheDocument();
  });

  it("PERTAMINA_VIEWER does not see the Admin — Users menu item", async () => {
    await loginAndOpenMenu("viewer@pertamina.com", "Siti Rahayu");
    expect(screen.queryByText("Admin — Users")).not.toBeInTheDocument();
  });
});

describe("Direct route: /ltsa/admin/users (Phase 3 -- hiding the nav item is not security)", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/ltsa");
  });

  it("clicking Admin — Users navigates to AdminUsersView with canManageUsers=true for TAP_ADMIN, and hides LTSAWorkspace", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("admin@tap.co.id");
    await screen.findByTestId("ltsa-workspace-stub");

    fireEvent.click(screen.getByRole("button", { name: /andra wicaksono/i }));
    fireEvent.click(screen.getByText("Admin — Users"));

    const stub = await screen.findByTestId("admin-users-view-stub");
    expect(stub.textContent).toBe("true");
    expect(screen.queryByTestId("ltsa-workspace-stub")).not.toBeInTheDocument();
    expect(window.location.pathname).toBe("/ltsa/admin/users");
  });

  it("a TAP_ENGINEER who manually navigates to the route reaches AdminUsersView only with canManageUsers=false -- the real gate stays in AdminUsersView/the backend, not a blocked render", async () => {
    window.history.pushState({}, "", "/ltsa/admin/users");
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("engineer@tap.co.id");

    const stub = await screen.findByTestId("admin-users-view-stub");
    expect(stub.textContent).toBe("false");
  });

  it("a JOHN_CRANE_ENGINEER who manually navigates to the route also gets canManageUsers=false", async () => {
    window.history.pushState({}, "", "/ltsa/admin/users");
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("jc@johncrane.internal");

    const stub = await screen.findByTestId("admin-users-view-stub");
    expect(stub.textContent).toBe("false");
  });

  it("a PERTAMINA_VIEWER who manually navigates to the route also gets canManageUsers=false", async () => {
    window.history.pushState({}, "", "/ltsa/admin/users");
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("viewer@pertamina.com");

    const stub = await screen.findByTestId("admin-users-view-stub");
    expect(stub.textContent).toBe("false");
  });

  it("Back to LTSA Workspace returns from the admin route to the normal capability-gated workspace", async () => {
    render(<LTSAAuthGate />);
    await screen.findByRole("heading", { name: "Sign in" });
    await login("admin@tap.co.id");
    await screen.findByTestId("ltsa-workspace-stub");

    fireEvent.click(screen.getByRole("button", { name: /andra wicaksono/i }));
    fireEvent.click(screen.getByText("Admin — Users"));
    await screen.findByTestId("admin-users-view-stub");

    fireEvent.click(screen.getByText("Back to LTSA Workspace"));

    expect(await screen.findByTestId("ltsa-workspace-stub")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-users-view-stub")).not.toBeInTheDocument();
    expect(window.location.pathname).toBe("/ltsa");
  });
});
