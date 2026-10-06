import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ForgotPasswordView from "./ForgotPasswordView";
import "@testing-library/jest-dom";

describe("ForgotPasswordView", () => {
  it("renders form and submits entered identifier", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ message: "sent" });
    const onBackToLogin = vi.fn();

    render(<ForgotPasswordView onSubmit={onSubmit} onBackToLogin={onBackToLogin} />);

    expect(screen.getByRole("heading", { name: "Forgot password?" })).toBeInTheDocument();
    const input = screen.getByLabelText("Username or Email");
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "engineer@tap.com" } });
    const submitBtn = screen.getByRole("button", { name: "Send Reset Link" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("engineer@tap.com");
    });

    // Confirmation message displayed
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Check your inbox" })).toBeInTheDocument();
    });
    expect(screen.getByText(/15 minutes/)).toBeInTheDocument();

    // Click back to sign in
    const backBtn = screen.getByRole("button", { name: "Back to Sign In" });
    fireEvent.click(backBtn);
    expect(onBackToLogin).toHaveBeenCalledTimes(1);
  });

  it("handles rate limiting error gracefully", async () => {
    const rateLimitErr = new Error("rate_limited");
    rateLimitErr.code = "rate_limited";
    const onSubmit = vi.fn().mockRejectedValue(rateLimitErr);

    render(<ForgotPasswordView onSubmit={onSubmit} onBackToLogin={vi.fn()} />);

    const input = screen.getByLabelText("Username or Email");
    fireEvent.change(input, { target: { value: "spam@tap.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send Reset Link" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Too many password reset requests");
    });
  });

  it("handles server unavailable error gracefully", async () => {
    const serverErr = new Error("server_unavailable");
    serverErr.code = "server_unavailable";
    const onSubmit = vi.fn().mockRejectedValue(serverErr);

    render(<ForgotPasswordView onSubmit={onSubmit} onBackToLogin={vi.fn()} />);

    const input = screen.getByLabelText("Username or Email");
    fireEvent.change(input, { target: { value: "any@tap.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send Reset Link" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Unable to process request right now");
    });
  });

  it("clicking Back to Sign In from initial form triggers callback", () => {
    const onBackToLogin = vi.fn();
    render(<ForgotPasswordView onSubmit={vi.fn()} onBackToLogin={onBackToLogin} />);

    const backBtn = screen.getByRole("button", { name: "Back to Sign In" });
    fireEvent.click(backBtn);
    expect(onBackToLogin).toHaveBeenCalledTimes(1);
  });
});
