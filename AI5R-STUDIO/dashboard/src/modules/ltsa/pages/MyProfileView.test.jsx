import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MyProfileView from "./MyProfileView";

const BASE_SESSION = {
  user: {
    id: "usr-1",
    name: "Yohanes Firdaus",
    username: "yohanes.firdaus",
    email: "yohanes.firdaus@pertamina.com",
  },
  organization: {
    id: "org-pertamina",
    code: "PERTAMINA",
    name: "PT Pertamina (Persero)",
    displayName: "PERTAMINA",
  },
  role: "PERTAMINA_ENGINEER",
  permissions: ["pump.read", "seal.read"],
  data_scope_type: "ALL",
  data_scope_value: null,
};

describe("MyProfileView", () => {
  it("renders user identity and explicit ALL area access correctly", () => {
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} />);

    expect(screen.getByTestId("profile-full-name")).toHaveTextContent("Yohanes Firdaus");
    expect(screen.getByTestId("profile-username")).toHaveTextContent("yohanes.firdaus");
    expect(screen.getByTestId("profile-organization")).toHaveTextContent("PT Pertamina (Persero)");
    expect(screen.getByTestId("profile-role")).toHaveTextContent("Pertamina Engineer");
    expect(screen.getByTestId("profile-area-access")).toHaveTextContent("All Areas");
    expect(screen.getByTestId("profile-email-display")).toHaveTextContent("yohanes.firdaus@pertamina.com");
    expect(screen.queryByTestId("profile-email-action-required")).not.toBeInTheDocument();
    expect(screen.getByTestId("profile-edit-email-btn")).toHaveTextContent("Edit Email");
  });

  it("renders specific AREA scope correctly", () => {
    const session = {
      ...BASE_SESSION,
      data_scope_type: "AREA",
      data_scope_value: "KILANG-02",
    };
    render(<MyProfileView session={session} onNavigateWorkspace={vi.fn()} />);

    expect(screen.getByTestId("profile-area-access")).toHaveTextContent("KILANG-02");
  });

  it("renders null/empty scope as 'No Area Access / Not Assigned' (never 'All Areas')", () => {
    const session = {
      ...BASE_SESSION,
      data_scope_type: null,
      data_scope_value: null,
    };
    render(<MyProfileView session={session} onNavigateWorkspace={vi.fn()} />);

    expect(screen.getByTestId("profile-area-access")).toHaveTextContent("No Area Access / Not Assigned");
  });

  it("shows action required badge when email is not registered", () => {
    const unverifiedSession = {
      ...BASE_SESSION,
      user: {
        ...BASE_SESSION.user,
        email: null,
      },
    };
    render(<MyProfileView session={unverifiedSession} onNavigateWorkspace={vi.fn()} />);

    expect(screen.getByTestId("profile-email-display")).toHaveTextContent("(not registered)");
    expect(screen.getByTestId("profile-email-action-required")).toBeInTheDocument();
    expect(screen.getByTestId("profile-edit-email-btn")).toHaveTextContent("Register Email");
  });

  it("enables Change Password and opens the change-password form", () => {
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} onChangePassword={vi.fn()} />);

    const changePwdBtn = screen.getByTestId("profile-change-password-btn");
    expect(changePwdBtn).toBeEnabled();
    expect(screen.queryByTestId("change-password-form")).toBeNull();

    fireEvent.click(changePwdBtn);
    expect(screen.getByTestId("change-password-form")).toBeInTheDocument();
    expect(screen.getByLabelText("Current Password")).toHaveProperty("type", "password");
    expect(screen.getByLabelText("New Password")).toHaveProperty("type", "password");
    expect(screen.getByLabelText("Confirm New Password")).toHaveProperty("type", "password");
  });

  it("changes the password through onChangePassword and reports success", async () => {
    const onChangePassword = vi.fn().mockResolvedValue({});
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} onChangePassword={onChangePassword} />);

    fireEvent.click(screen.getByTestId("profile-change-password-btn"));
    fireEvent.change(screen.getByLabelText("Current Password"), { target: { value: "Old-Passw0rd-2026" } });
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "New-Passw0rd-2026" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "New-Passw0rd-2026" } });
    fireEvent.click(screen.getByTestId("change-password-submit"));

    await waitFor(() => expect(onChangePassword).toHaveBeenCalledWith("Old-Passw0rd-2026", "New-Passw0rd-2026"));
    expect(await screen.findByTestId("profile-password-success")).toHaveTextContent("Password changed");
    expect(screen.queryByTestId("change-password-form")).toBeNull();
  });

  it("keeps the form open with a safe message when the current password is wrong", async () => {
    const error = new Error("incorrect_current_password");
    error.code = "incorrect_current_password";
    const onChangePassword = vi.fn().mockRejectedValue(error);
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} onChangePassword={onChangePassword} />);

    fireEvent.click(screen.getByTestId("profile-change-password-btn"));
    fireEvent.change(screen.getByLabelText("Current Password"), { target: { value: "Wrong-Passw0rd-2026" } });
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "New-Passw0rd-2026" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "New-Passw0rd-2026" } });
    fireEvent.click(screen.getByTestId("change-password-submit"));

    expect(await screen.findByTestId("change-password-error")).toHaveTextContent("Current password is incorrect.");
    expect(screen.getByTestId("change-password-form")).toBeInTheDocument();
    expect(screen.queryByTestId("profile-password-success")).toBeNull();
  });

  it("navigates back to workspace when back button is clicked", () => {
    const handleNavigate = vi.fn();
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={handleNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: /back to ltsa workspace/i }));
    expect(handleNavigate).toHaveBeenCalledTimes(1);
  });

  it("allows editing email and handles cancel", () => {
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByTestId("profile-edit-email-btn"));
    const input = screen.getByTestId("profile-email-input");
    expect(input).toBeInTheDocument();
    expect(input.value).toBe("yohanes.firdaus@pertamina.com");

    fireEvent.change(input, { target: { value: "new.email@pertamina.com" } });
    expect(input.value).toBe("new.email@pertamina.com");

    fireEvent.click(screen.getByTestId("profile-cancel-email-btn"));
    expect(screen.queryByTestId("profile-email-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("profile-email-display")).toHaveTextContent("yohanes.firdaus@pertamina.com");
  });

  it("updates email successfully on form submission", async () => {
    const handleUpdate = vi.fn().mockResolvedValue({
      ...BASE_SESSION,
      user: { ...BASE_SESSION.user, email: "updated@pertamina.com" },
    });

    render(<MyProfileView session={BASE_SESSION} onUpdateEmail={handleUpdate} onNavigateWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByTestId("profile-edit-email-btn"));
    const input = screen.getByTestId("profile-email-input");
    fireEvent.change(input, { target: { value: " updated@pertamina.com " } });
    fireEvent.click(screen.getByTestId("profile-save-email-btn"));

    await waitFor(() => {
      expect(handleUpdate).toHaveBeenCalledWith("updated@pertamina.com");
    });

    expect(await screen.findByTestId("profile-email-success")).toHaveTextContent(
      "Email updated successfully. Password reset is now available."
    );
  });

  it("handles 409 conflict when email is already in use", async () => {
    const error = new Error("email_already_in_use");
    error.code = "email_already_in_use";
    const handleUpdate = vi.fn().mockRejectedValue(error);

    render(<MyProfileView session={BASE_SESSION} onUpdateEmail={handleUpdate} onNavigateWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByTestId("profile-edit-email-btn"));
    const input = screen.getByTestId("profile-email-input");
    fireEvent.change(input, { target: { value: "duplicate@pertamina.com" } });
    fireEvent.click(screen.getByTestId("profile-save-email-btn"));

    expect(await screen.findByTestId("profile-email-error")).toHaveTextContent(
      "This email address is already in use by another account."
    );
  });

  it("handles 422 format error when email is invalid", async () => {
    const error = new Error("invalid_email");
    error.code = "invalid_email";
    const handleUpdate = vi.fn().mockRejectedValue(error);

    render(<MyProfileView session={BASE_SESSION} onUpdateEmail={handleUpdate} onNavigateWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByTestId("profile-edit-email-btn"));
    const input = screen.getByTestId("profile-email-input");
    fireEvent.change(input, { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByTestId("profile-save-email-btn"));

    expect(await screen.findByTestId("profile-email-error")).toHaveTextContent(
      "Please enter a valid email address."
    );
  });
});

describe("MyProfileView layout", () => {
  it("renders the page header inside the centered profile container", () => {
    const { container } = render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} />);

    const root = container.querySelector(".ltsa-open-design > .ltsa-profile-container");
    expect(root).not.toBeNull();
    expect(screen.getByRole("heading", { level: 1, name: "My Profile" })).toBeInTheDocument();
    expect(
      screen.getByText("Manage your LTSA identity, organization, and account security.")
    ).toBeInTheDocument();
  });

  it("renders two labelled cards: Profile Information and Security & Credentials", () => {
    const { container } = render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} />);

    expect(container.querySelectorAll(".profile-card")).toHaveLength(2);
    expect(screen.getByRole("region", { name: "Profile Information" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Security & Credentials" })).toBeInTheDocument();
  });

  it("keeps every label and value in separate elements within the field grid", () => {
    const { container } = render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} />);

    const grid = container.querySelector(".profile-field-grid");
    expect(grid).not.toBeNull();
    const labels = [...grid.querySelectorAll(".profile-field-label")].map((el) => el.textContent);
    expect(labels).toEqual(["Full Name", "Username", "Organization", "Role", "Area Access", "Registered Email"]);
    for (const testId of ["profile-full-name", "profile-username", "profile-organization"]) {
      const value = screen.getByTestId(testId);
      expect(value).toHaveClass("profile-field-value");
      expect(value.closest(".profile-field").querySelector(".profile-field-label")).not.toBe(value);
    }
  });

  it("renders role and area access as badges and the email row across the full grid width", () => {
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} />);

    expect(screen.getByTestId("profile-role")).toHaveClass("profile-badge");
    expect(screen.getByTestId("profile-area-access")).toHaveClass("profile-badge");
    expect(screen.getByTestId("profile-email-display").closest(".profile-field")).toHaveClass("profile-field-full");
  });

  it("keeps a SUPERUSER with no recorded scope as 'No Area Access / Not Assigned' (resolver contract unchanged)", () => {
    const session = { ...BASE_SESSION, role: "SUPERUSER", data_scope_type: null, data_scope_value: null };
    render(<MyProfileView session={session} onNavigateWorkspace={vi.fn()} />);

    expect(screen.getByTestId("profile-role")).toHaveTextContent("Superuser");
    expect(screen.getByTestId("profile-area-access")).toHaveTextContent("No Area Access / Not Assigned");
  });

  it("shows the Change Password action with its hint underneath, and a masked password", () => {
    render(<MyProfileView session={BASE_SESSION} onNavigateWorkspace={vi.fn()} onChangePassword={vi.fn()} />);

    const button = screen.getByTestId("profile-change-password-btn");
    expect(button).toBeEnabled();
    expect(button).toHaveClass("btn-secondary");
    const action = button.closest(".profile-security-action");
    expect(action.querySelector(".profile-security-hint")).toHaveTextContent("Other signed-in sessions end after a change");
    expect(screen.getByTestId("profile-password-display")).toHaveTextContent("••••••••••••");
  });
});
