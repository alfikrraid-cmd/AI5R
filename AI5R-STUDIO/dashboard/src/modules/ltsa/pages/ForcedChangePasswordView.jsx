import ChangePasswordForm from "../components/ChangePasswordForm";
import "./LTSAOpenDesign.css";
import "./LoginView.css";
import "./ForgotPasswordView.css";
import "./ResetPasswordView.css";

// LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- rendered by LTSAAuthGate INSTEAD of
// the whole authenticated shell while session.must_change_password is true,
// whatever the URL. The backend independently answers every API except
// GET /api/auth/me and POST /api/auth/change-password with 403
// password_change_required, so this screen is not the only barrier.
export default function ForcedChangePasswordView({ session, onSubmit, onLogout }) {
  return (
    <div className="ltsa-open-design login-screen" data-testid="forced-change-password">
      <div className="login-shell reset-password-shell">
        <div className="login-brand">
          <img className="login-logo" src="/branding/AI5R-logo.svg" alt="AI5R" width="48" height="46" />
          <h1>LTSA Engineering</h1>
          <p className="login-tagline">
            Asset intelligence for rotating equipment — pumps, mechanical seals, and the
            maintenance history behind them.
          </p>
        </div>

        <div className="login-card reset-password-card">
          <div className="login-card-head">
            <h2>Change your password</h2>
            <p>For security, you must create a new password before continuing to LTSA.</p>
          </div>

          <ChangePasswordForm
            idPrefix="forced-change-password"
            currentLabel="Current / Temporary Password"
            submitLabel="Change password and continue"
            username={session?.user?.username}
            email={session?.user?.email}
            onSubmit={onSubmit}
          />

          <div className="forced-change-password-footer">
            <button type="button" className="btn-link" onClick={onLogout}>
              Log out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
