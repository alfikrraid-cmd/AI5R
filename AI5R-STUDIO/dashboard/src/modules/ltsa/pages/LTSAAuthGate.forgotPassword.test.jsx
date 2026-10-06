import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LTSAAuthGate from "./LTSAAuthGate";
import "@testing-library/jest-dom";

vi.mock("../auth/AuthContext", () => ({
  AuthProvider: ({ children }) => children,
  useAuth: vi.fn(() => ({
    status: "unauthenticated",
    error: null,
    login: vi.fn().mockResolvedValue({}),
    logout: vi.fn(),
  })),
}));

vi.mock("../auth/authClient", () => ({
  requestPasswordReset: vi.fn().mockResolvedValue({ message: "sent" }),
  confirmPasswordReset: vi.fn().mockResolvedValue({ message: "success" }),
}));

describe("LTSAAuthGate Forgot Password / Reset Password Routing", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/ltsa");
  });

  it("renders LoginView by default and switches to ForgotPasswordView when clicking Forgot password", async () => {
    render(<LTSAAuthGate />);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    const forgotBtn = screen.getByRole("button", { name: "Forgot password?" });
    expect(forgotBtn).toBeInTheDocument();

    fireEvent.click(forgotBtn);

    // Switches to ForgotPasswordView
    expect(screen.getByRole("heading", { name: "Forgot password?" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username or Email")).toBeInTheDocument();

    // Clicking Back to Sign In switches back to LoginView
    const backBtn = screen.getByRole("button", { name: "Back to Sign In" });
    fireEvent.click(backBtn);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("renders ResetPasswordView when navigating to /reset-password?token=xyz", async () => {
    window.history.pushState({}, "", "/reset-password?token=test-reset-token-123");
    render(<LTSAAuthGate />);

    expect(screen.getByRole("heading", { name: "Set new password" })).toBeInTheDocument();
    expect(screen.getByLabelText("New Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm New Password")).toBeInTheDocument();

    // Clicking Back to Sign In returns to /ltsa LoginView
    const backBtn = screen.getByRole("button", { name: "Back to Sign In" });
    fireEvent.click(backBtn);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("renders ResetPasswordView when navigating to /ltsa/reset-password?token=xyz", async () => {
    window.history.pushState({}, "", "/ltsa/reset-password?token=ltsa-token-456");
    render(<LTSAAuthGate />);

    expect(screen.getByRole("heading", { name: "Set new password" })).toBeInTheDocument();
  });
});
