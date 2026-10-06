import { useState } from "react";
import { confirmPasswordReset } from "../auth/authClient";
import "./LTSAOpenDesign.css";
import "./LoginView.css";
import "./ForgotPasswordView.css";
import "./ResetPasswordView.css";

export default function ResetPasswordView({
  token: initialToken,
  onBackToLogin,
  onSubmit = confirmPasswordReset,
}) {
  const [token] = useState(() => {
    if (initialToken) return initialToken;
    const params = new URLSearchParams(window.location.search);
    return params.get("token") || "";
  });

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;

    if (!token) {
      setError("This reset link is missing a valid token. Please request a new link.");
      return;
    }

    if (!newPassword) {
      setError("Please enter a new password.");
      return;
    }

    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match. Please verify and try again.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(token, newPassword);
      setIsSuccess(true);
    } catch (err) {
      if (err.code === "invalid_token") {
        setError("This password reset link is invalid or has expired. Please request a new reset link.");
      } else if (err.code === "invalid_password") {
        setError("Password does not meet requirements.");
      } else {
        setError("Unable to reset password right now. Please try again shortly.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="ltsa-open-design login-screen">
      <div className="login-shell reset-password-shell">
        <div className="login-brand">
          <img className="login-logo" src="/branding/AI5R-logo.svg" alt="AI5R" width="48" height="46" />
          <h1>LTSA Engineering</h1>
          <p className="login-tagline">
            Asset intelligence for rotating equipment — pumps, mechanical seals, and the
            maintenance history behind them.
          </p>
          <div className="running-line">
            <span className="status-signal normal">
              <span className="dot-lg" />
              Set new account password
            </span>
          </div>
        </div>

        <div className="login-card reset-password-card">
          {isSuccess ? (
            <div className="reset-password-success">
              <div className="login-card-head">
                <h2>Password Reset</h2>
                <p>Your password has been successfully updated.</p>
              </div>
              <div className="reset-password-notice">
                <p>You can now sign in to your AI5R LTSA workspace with your new password.</p>
              </div>
              <button
                type="button"
                className="btn-primary login-submit"
                onClick={onBackToLogin}
              >
                Sign In
              </button>
            </div>
          ) : !token ? (
            <div className="reset-password-invalid">
              <div className="login-card-head">
                <h2>Invalid Reset Link</h2>
                <p>The password reset link is invalid or incomplete.</p>
              </div>
              <div className="login-error" role="alert">
                No reset token was provided in the URL. Please use the complete link from your email or request a new one.
              </div>
              <button
                type="button"
                className="btn-primary login-submit"
                onClick={onBackToLogin}
              >
                Back to Sign In
              </button>
            </div>
          ) : (
            <div>
              <div className="login-card-head">
                <h2>Set new password</h2>
                <p>Choose a secure password for your account.</p>
              </div>

              <form onSubmit={handleSubmit} noValidate>
                <label className="login-field">
                  <span>New Password</span>
                  <input
                    type="password"
                    name="newPassword"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    disabled={isSubmitting}
                    required
                  />
                </label>

                <label className="login-field">
                  <span>Confirm New Password</span>
                  <input
                    type="password"
                    name="confirmPassword"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    disabled={isSubmitting}
                    required
                  />
                </label>

                {error && (
                  <div className="login-error" role="alert">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="btn-primary login-submit"
                  disabled={isSubmitting || !newPassword || !confirmPassword}
                >
                  {isSubmitting ? "Resetting password…" : "Reset Password"}
                </button>

                <div className="login-footer-links">
                  <button
                    type="button"
                    className="forgot-password-link"
                    onClick={onBackToLogin}
                    disabled={isSubmitting}
                  >
                    Back to Sign In
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
