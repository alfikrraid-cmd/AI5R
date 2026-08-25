import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LoginView from "./LoginView";

import "@testing-library/jest-dom";

describe("LoginView username/email identifier", () => {
  it("renders Username or Email and submits it unchanged with the password", async () => {
    const onSubmit = vi.fn().mockResolvedValue({});
    render(<LoginView status="unauthenticated" error={null} onSubmit={onSubmit} />);

    const identifier = screen.getByLabelText("Username or Email");
    expect(identifier).toHaveAttribute("type", "text");

    fireEvent.change(identifier, { target: { value: "ravi" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("ravi", "secret"));
  });
  it("renders the official AI5R logo on the login screen", () => {
    const onSubmit = vi.fn().mockResolvedValue({});
    render(<LoginView status="unauthenticated" error={null} onSubmit={onSubmit} />);

    const logo = screen.getByRole("img", { name: "AI5R" });
    expect(logo).toHaveAttribute("src", "/favicon.svg");
    expect(logo).toHaveAttribute("width", "48");
    expect(logo).toHaveAttribute("height", "46");
  });
});
