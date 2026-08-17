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

async function login(email, password = "demo123") {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

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
    expect(window.localStorage.getItem("ai5r.ltsa.session")).toBeNull();
  });
});
