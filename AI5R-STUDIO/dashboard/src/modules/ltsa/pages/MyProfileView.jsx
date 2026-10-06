import { useEffect, useState } from "react";
import { useOptionalAuth } from "../auth/AuthContext";
import { formatAreaScopeDisplay } from "../utils/areaScopeDisplay";
import ChangePasswordForm from "../components/ChangePasswordForm";
import "./LTSAOpenDesign.css";
import "./MyProfileView.css";

export const ROLE_LABEL = {
  SUPERUSER: "Superuser",
  TAP_ADMIN: "TAP Admin",
  TAP_ENGINEER: "TAP Engineer",
  JOHN_CRANE_ENGINEER: "John Crane Engineer",
  PERTAMINA_ENGINEER: "Pertamina Engineer",
  PERTAMINA_VIEWER: "Pertamina Viewer",
};

export default function MyProfileView({ session: propSession, onNavigateWorkspace, onUpdateEmail, onChangePassword }) {
  const auth = useOptionalAuth() || {};
  const currentSession = propSession || auth.session;
  const updateEmailFn = onUpdateEmail || auth.updateEmail;
  const changePasswordFn = onChangePassword || auth.changePassword;
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordChanged, setPasswordChanged] = useState(false);

  const currentEmail = currentSession?.user?.email || "";
  const [isEditing, setIsEditing] = useState(false);
  const [emailDraft, setEmailDraft] = useState(currentEmail);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    if (!isEditing) {
      setEmailDraft(currentSession?.user?.email || "");
    }
  }, [currentSession?.user?.email, isEditing]);

  const fullName = currentSession?.user?.name || "—";
  const username = currentSession?.user?.username || currentSession?.user?.email || "—";
  const organizationLabel =
    currentSession?.organization?.name ||
    currentSession?.organization?.displayName ||
    currentSession?.organization?.code ||
    "—";
  const roleLabel = ROLE_LABEL[currentSession?.role] ?? currentSession?.role ?? "—";
  const areaAccessLabel = formatAreaScopeDisplay(
    currentSession?.data_scope_type,
    currentSession?.data_scope_value
  );

  const hasRegisteredEmail = Boolean(currentSession?.user?.email && currentSession.user.email.trim());

  function handleStartEdit() {
    setIsEditing(true);
    setEmailDraft(currentSession?.user?.email || "");
    setErrorMessage(null);
    setSuccessMessage(null);
  }

  function handleCancelEdit() {
    setIsEditing(false);
    setEmailDraft(currentSession?.user?.email || "");
    setErrorMessage(null);
  }

  async function handleSaveEmail(event) {
    event.preventDefault();
    const trimmed = emailDraft.trim();
    if (!trimmed) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      if (updateEmailFn) {
        await updateEmailFn(trimmed);
      }
      setIsEditing(false);
      setSuccessMessage("Email updated successfully. Password reset is now available.");
    } catch (err) {
      if (err?.code === "email_already_in_use" || err?.message?.toLowerCase().includes("already in use")) {
        setErrorMessage("This email address is already in use by another account.");
      } else if (err?.code === "invalid_email" || err?.code === "unprocessable_entity" || err?.status === 422) {
        setErrorMessage("Please enter a valid email address.");
      } else {
        setErrorMessage("Unable to update email. Please try again.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="ltsa-open-design ltsa-profile-page">
      <div className="ltsa-profile-container">
        <div className="profile-nav-bar">
          <button
            type="button"
            className="btn-link profile-back-btn"
            onClick={onNavigateWorkspace}
            aria-label="Back to LTSA Workspace"
          >
            &larr; Back to LTSA Workspace
          </button>
        </div>

        <header className="profile-page-header">
          <h1>My Profile</h1>
          <p>Manage your LTSA identity, organization, and account security.</p>
        </header>

        {/* User Identity & Scope Card */}
        <section className="profile-card" aria-labelledby="profile-information-heading">
          <div className="profile-card-header">
            <h2 id="profile-information-heading">Profile Information</h2>
          </div>

          <div className="profile-card-body">
            <div className="profile-field-grid">
              <div className="profile-field">
                <span className="profile-field-label">Full Name</span>
                <span className="profile-field-value" data-testid="profile-full-name">{fullName}</span>
              </div>

              <div className="profile-field">
                <span className="profile-field-label">Username</span>
                <span className="profile-field-value" data-testid="profile-username">{username}</span>
              </div>

              <div className="profile-field">
                <span className="profile-field-label">Organization</span>
                <span className="profile-field-value" data-testid="profile-organization">{organizationLabel}</span>
              </div>

              <div className="profile-field">
                <span className="profile-field-label">Role</span>
                <span className="profile-field-value">
                  <span className="profile-badge" data-testid="profile-role">{roleLabel}</span>
                </span>
              </div>

              <div className="profile-field">
                <span className="profile-field-label">Area Access</span>
                <span className="profile-field-value">
                  <span className="profile-badge" data-testid="profile-area-access">{areaAccessLabel}</span>
                </span>
              </div>

              {/* Registered Email Management */}
              <div className="profile-field profile-field-full profile-email-section">
                <span className="profile-field-label">Registered Email</span>
                
                {errorMessage && (
                  <div className="profile-feedback error" role="alert" data-testid="profile-email-error">
                    {errorMessage}
                  </div>
                )}

                {successMessage && (
                  <div className="profile-feedback success" role="status" data-testid="profile-email-success">
                    {successMessage}
                  </div>
                )}

                {!isEditing ? (
                  <div className="profile-email-row">
                    <div className="profile-email-display">
                      <span
                        className={`profile-field-value ${!hasRegisteredEmail ? "muted" : ""}`}
                        data-testid="profile-email-display"
                      >
                        {hasRegisteredEmail ? currentSession.user.email : "(not registered)"}
                      </span>

                      {!hasRegisteredEmail && (
                        <span
                          className="profile-action-required-badge"
                          data-testid="profile-email-action-required"
                        >
                          Action Required: Register email to enable password reset
                        </span>
                      )}
                    </div>

                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleStartEdit}
                      data-testid="profile-edit-email-btn"
                    >
                      {hasRegisteredEmail ? "Edit Email" : "Register Email"}
                    </button>
                  </div>
                ) : (
                  <form className="profile-email-form" onSubmit={handleSaveEmail} noValidate>
                    <input
                      type="email"
                      className="profile-email-input"
                      value={emailDraft}
                      onChange={(e) => setEmailDraft(e.target.value)}
                      placeholder="user@example.com"
                      disabled={isSaving}
                      aria-label="Email address"
                      data-testid="profile-email-input"
                      autoFocus
                    />
                    <button
                      type="submit"
                      className="btn-primary"
                      disabled={isSaving}
                      data-testid="profile-save-email-btn"
                    >
                      {isSaving ? "Saving…" : "Save"}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleCancelEdit}
                      disabled={isSaving}
                      data-testid="profile-cancel-email-btn"
                    >
                      Cancel
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Security & Credentials Card */}
        <section className="profile-card" aria-labelledby="profile-security-heading">
          <div className="profile-card-header">
            <h2 id="profile-security-heading">Security &amp; Credentials</h2>
            <p>Manage your account password and recovery methods.</p>
          </div>

          <div className="profile-card-body">
            <div className="profile-security-row">
              <div className="profile-field profile-security-info">
                <span className="profile-field-label">Password</span>
                <span className="profile-field-value profile-password-mask" data-testid="profile-password-display">
                  ••••••••••••
                </span>
              </div>

              {!isChangingPassword ? (
                <div className="profile-security-action">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setPasswordChanged(false);
                      setIsChangingPassword(true);
                    }}
                    disabled={!changePasswordFn}
                    data-testid="profile-change-password-btn"
                  >
                    Change Password
                  </button>
                  <span className="profile-security-hint">Other signed-in sessions end after a change</span>
                </div>
              ) : null}
            </div>

            {passwordChanged ? (
              <div className="profile-feedback success" role="status" data-testid="profile-password-success">
                Password changed. Other signed-in sessions have been signed out.
              </div>
            ) : null}

            {isChangingPassword ? (
              <div className="profile-change-password" data-testid="profile-change-password-panel">
                <ChangePasswordForm
                  idPrefix="profile-change-password"
                  username={currentSession?.user?.username}
                  email={currentSession?.user?.email}
                  onSubmit={changePasswordFn}
                  onCancel={() => setIsChangingPassword(false)}
                  onSuccess={() => {
                    setIsChangingPassword(false);
                    setPasswordChanged(true);
                  }}
                />
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
