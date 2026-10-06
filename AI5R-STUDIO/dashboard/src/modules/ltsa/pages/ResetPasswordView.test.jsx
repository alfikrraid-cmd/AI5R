import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ResetPasswordView from "./ResetPasswordView";
import "@testing-library/jest-dom";

describe("ResetPasswordView", () => {
  it("renders invalid link notice when token is missing", () => {
    const onBackToLogin = vi.fn();
    render(<ResetPasswordView token="" onBackToLogin={onBackToLogin} onSubmit={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Invalid Reset Link" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("No reset token was provided");

    fireEvent.click(screen.getByRole("button", { name: "Back to Sign In" }));
    expect(onBackToLogin).toHaveBeenCalledTimes(1);
  });

  it("validates password matching before submitting", async () => {
    const onSubmit = vi.fn();
    render(<ResetPasswordView token="valid-token-123" onBackToLogin={vi.fn()} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "SecretPass123" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "DifferentPass456" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset Password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match");
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("validates minimum password length", async () => {
    const onSubmit = vi.fn();
    render(<ResetPasswordView token="valid-token-123" onBackToLogin={vi.fn()} onSubmit={onSubmit} />);

    // Global password policy (LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A): 12-128.
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "elevenchars" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "elevenchars" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset Password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Password must be at least 12 characters");
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows the backend policy message when the server rejects the password", async () => {
    const error = new Error("invalid_password");
    error.code = "invalid_password";
    error.detail = "Password must not be the same as the username";
    const onSubmit = vi.fn().mockRejectedValue(error);
    render(<ResetPasswordView token="valid-token-123" onBackToLogin={vi.fn()} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "tap.engineer.x" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "tap.engineer.x" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset Password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Password must not be the same as the username");
    });
  });

  it("successfully resets password and navigates back to sign in", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ message: "success" });
    const onBackToLogin = vi.fn();

    render(<ResetPasswordView token="valid-token-123" onBackToLogin={onBackToLogin} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "NewSecurePassword2026!" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "NewSecurePassword2026!" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset Password" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("valid-token-123", "NewSecurePassword2026!");
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Password Reset" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    expect(onBackToLogin).toHaveBeenCalledTimes(1);
  });

  it("handles invalid or expired token error from API", async () => {
    const tokenErr = new Error("invalid_token");
    tokenErr.code = "invalid_token";
    const onSubmit = vi.fn().mockRejectedValue(tokenErr);

    render(<ResetPasswordView token="expired-token" onBackToLogin={vi.fn()} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "ValidPassword123" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "ValidPassword123" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset Password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("This password reset link is invalid or has expired");
    });
  });
});
