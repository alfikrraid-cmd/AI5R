import { useState } from "react";
import { PASSWORD_POLICY_HINT, passwordPolicyError } from "../auth/passwordPolicy";
import "./ChangePasswordForm.css";

// LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- one form for both the forced
// first-login screen and My Profile. onSubmit(currentPassword, newPassword)
// is AuthContext.changePassword; client-side checks run first so a mismatch
// or policy problem never sends a request.
const ERROR_MESSAGES = {
  incorrect_current_password: "Current password is incorrect.",
  rate_limited: "Too many incorrect attempts. Please wait 15 minutes and try again.",
  password_changed_elsewhere: "Your password was changed in another session. Please sign in again.",
  unauthorized: "Your session has expired. Please sign in again.",
};

export default function ChangePasswordForm({
  onSubmit,
  onSuccess,
  onCancel,
  username,
  email,
  currentLabel = "Current Password",
  submitLabel = "Change Password",
  idPrefix = "change-password",
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function clientError() {
    if (!currentPassword) return `Please enter your ${currentLabel.toLowerCase()}.`;
    const policy = passwordPolicyError(newPassword, { username, email });
    if (policy) return policy;
    if (newPassword !== confirmPassword) return "New passwords do not match.";
    if (newPassword === currentPassword) return "New password must be different from the current password.";
    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;
    const problem = clientError();
    if (problem) {
      setError(problem);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      onSuccess?.();
    } catch (err) {
      if (err?.code === "password_policy") {
        setError(err.detail || "Password does not meet the password requirements.");
      } else {
        setError(ERROR_MESSAGES[err?.code] || "Unable to change password right now. Please try again shortly.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputType = showPasswords ? "text" : "password";

  return (
    <form className="change-password-form" onSubmit={handleSubmit} noValidate data-testid="change-password-form">
      {error ? (
        <div className="change-password-error" role="alert" data-testid="change-password-error">
          {error}
        </div>
      ) : null}

      <div className="change-password-field">
        <label htmlFor={`${idPrefix}-current`}>{currentLabel}</label>
        <input
          id={`${idPrefix}-current`}
          type={inputType}
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          disabled={isSubmitting}
        />
      </div>

      <div className="change-password-field">
        <label htmlFor={`${idPrefix}-new`}>New Password</label>
        <input
          id={`${idPrefix}-new`}
          type={inputType}
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          disabled={isSubmitting}
          aria-describedby={`${idPrefix}-hint`}
        />
        <span className="change-password-hint" id={`${idPrefix}-hint`}>
          {PASSWORD_POLICY_HINT}
        </span>
      </div>

      <div className="change-password-field">
        <label htmlFor={`${idPrefix}-confirm`}>Confirm New Password</label>
        <input
          id={`${idPrefix}-confirm`}
          type={inputType}
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          disabled={isSubmitting}
        />
      </div>

      <label className="change-password-toggle">
        <input
          type="checkbox"
          checked={showPasswords}
          onChange={(event) => setShowPasswords(event.target.checked)}
        />
        Show passwords
      </label>

      <div className="change-password-actions">
        <button type="submit" className="btn-primary" disabled={isSubmitting} data-testid="change-password-submit">
          {isSubmitting ? "Saving…" : submitLabel}
        </button>
        {onCancel ? (
          <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
}
