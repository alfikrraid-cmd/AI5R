import { useState } from "react";
import "./LTSAOpenDesign.css";
import "./LoginView.css";

const ERROR_COPY = {
  invalid_credentials: "Email or password is incorrect. Please try again.",
  inactive_account: "This account is inactive. Contact your AI5R administrator.",
  server_unavailable: "LTSA Engineering is temporarily unavailable. Please try again shortly.",
};

export default function LoginView({ status, error, onSubmit }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const isLoading = status === "authenticating";

  function handleSubmit(event) {
    event.preventDefault();
    if (isLoading || !email || !password) return;
    // AuthContext already tracks the rejection in `status`/`error` state;
    // this call site only needs to trigger it, not handle the rejection
    // itself, but an unawaited rejected promise would otherwise surface as
    // an unhandled rejection.
    onSubmit(email, password).catch(() => {});
  }

  return (
    <div className="ltsa-open-design login-screen">
      <div className="login-shell">
        <div className="login-brand">
          <div className="eyebrow">AI5R</div>
          <h1>LTSA Engineering</h1>
          <p className="login-tagline">
            Asset intelligence for rotating equipment — pumps, mechanical seals, and the
            maintenance history behind them.
          </p>
          <div className="running-line">
            <span className="status-signal normal">
              <span className="dot-lg" />
              One workspace, permission-driven for every organization
            </span>
          </div>
        </div>

        <div className="login-card">
          <div className="login-card-head">
            <h2>Sign in</h2>
            <p>Enter your AI5R LTSA credentials to continue.</p>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <label className="login-field">
              <span>Email</span>
              <input
                type="email"
                name="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={isLoading}
                required
              />
            </label>

            <label className="login-field">
              <span>Password</span>
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={isLoading}
                required
              />
            </label>

            {error && (
              <div className="login-error" role="alert">
                {ERROR_COPY[error] ?? ERROR_COPY.invalid_credentials}
              </div>
            )}

            <button type="submit" className="btn-primary login-submit" disabled={isLoading}>
              {isLoading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
