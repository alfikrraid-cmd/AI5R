import { useState } from "react";
import { requestPasswordReset } from "../auth/authClient";
import "./LTSAOpenDesign.css";
import "./LoginView.css";
import "./ForgotPasswordView.css";

export default function ForgotPasswordView({ onBackToLogin, onSubmit = requestPasswordReset }) {
  const [identifier, setIdentifier] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = identifier.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(trimmed);
      setIsSubmitted(true);
    } catch (err) {
      if (err.code === "rate_limited") {
        setError("Too many password reset requests. Please wait a few minutes before trying again.");
      } else {
        setError("Unable to process request right now. Please try again shortly.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="ltsa-open-design login-screen">
      <div className="login-shell forgot-password-shell">
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
              Secure self-service account recovery
            </span>
          </div>
        </div>

        <div className="login-card forgot-password-card">
          {isSubmitted ? (
            <div className="forgot-password-success">
              <div className="login-card-head">
                <h2>Check your inbox</h2>
                <p>
                  If an account matches <strong>{identifier}</strong> and is eligible, password reset instructions have been sent.
                </p>
              </div>
              <div className="forgot-password-notice">
                <p>
                  The password reset link is valid for <strong>15 minutes</strong>. If you do not see the email, check your spam or junk folder.
                </p>
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
                <h2>Forgot password?</h2>
                <p>Enter your username or registered email to receive a password reset link.</p>
              </div>

              <form onSubmit={handleSubmit} noValidate>
                <label className="login-field">
                  <span>Username or Email</span>
                  <input
                    type="text"
                    name="identifier"
                    autoComplete="username"
                    value={identifier}
                    onChange={(event) => setIdentifier(event.target.value)}
                    disabled={isSubmitting}
                    placeholder="e.g. john or john@example.com"
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
                  disabled={isSubmitting || !identifier.trim()}
                >
                  {isSubmitting ? "Sending instructions…" : "Send Reset Link"}
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
