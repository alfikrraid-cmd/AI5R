import { useState } from "react";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import { visibleTabKeys, can, PERMISSIONS } from "../auth/permissions";
import LoginView from "./LoginView";
import LTSAWorkspace from "./LTSAWorkspace";
import "./LTSAOpenDesign.css";
import "./LTSAAuthGate.css";

const ROLE_LABEL = {
  TAP_ADMIN: "TAP Admin",
  TAP_ENGINEER: "TAP Engineer",
  PERTAMINA_ENGINEER: "Pertamina Engineer",
  PERTAMINA_VIEWER: "Pertamina Viewer",
};

function IdentityBar({ session, onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="ltsa-open-design">
      <div className="chrome-bar auth-identity-bar">
        <div className="chrome-inner">
          <div className="crumb">
            <span className="eyebrow">AI5R</span>
            <span className="sep">/</span>
            <b>LTSA Engineering</b>
            <span className="sep">/</span>
            <span>{session.organization.displayName}</span>
          </div>

          <div className="auth-identity-menu">
            <button
              type="button"
              className="btn-link auth-identity-trigger"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
            >
              {session.user.name}
              <span className="auth-identity-role">{ROLE_LABEL[session.role] ?? session.role}</span>
            </button>

            {menuOpen && (
              <div className="auth-identity-dropdown" role="menu">
                <div className="auth-identity-row">
                  <span className="auth-identity-label">Name</span>
                  <span>{session.user.name}</span>
                </div>
                <div className="auth-identity-row">
                  <span className="auth-identity-label">Organization</span>
                  <span>{session.organization.displayName}</span>
                </div>
                <div className="auth-identity-row">
                  <span className="auth-identity-label">Role</span>
                  <span>{ROLE_LABEL[session.role] ?? session.role}</span>
                </div>
                <button type="button" className="btn-link auth-identity-logout" onClick={onLogout}>
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Pre-auth (MWO-LTSA-UI-V2-001 and earlier), every LTSA caller landed on
// "history" by default (ApplicationAdapter's initialActiveKey="history").
// AUTH must not change that default for a role that still has it -- only
// fall back to that role's first visible tab when "history" itself isn't
// permitted, so this stays additive (permission-driven), not a re-pick of
// the existing landing behavior.
const DEFAULT_LANDING_KEY = "history";

function AuthenticatedLTSA({ organizationContext, platformContext }) {
  const { session, logout } = useAuth();
  const allowedKeys = visibleTabKeys(session);
  const capabilities = {
    allowedKeys,
    can: (permission) => can(session, permission),
  };
  const initialActiveKey = allowedKeys.includes(DEFAULT_LANDING_KEY) ? DEFAULT_LANDING_KEY : allowedKeys[0];

  return (
    <div>
      <IdentityBar session={session} onLogout={logout} />
      <LTSAWorkspace
        initialActiveKey={initialActiveKey}
        capabilities={capabilities}
        organizationContext={organizationContext}
        platformContext={platformContext}
      />
    </div>
  );
}

function LTSAAuthGateInner(props) {
  const { status, error, login } = useAuth();

  if (status === "checking") {
    return null;
  }

  if (status === "authenticated") {
    return <AuthenticatedLTSA {...props} />;
  }

  return <LoginView status={status} error={error} onSubmit={login} />;
}

// AUTHENTICATED LTSA SHELL layer (MWO-LTSA-AUTH-OPEN-DESIGN-001). LTSA is a
// standalone product (MWO-LTSA-STANDALONE-PRODUCT-SHELL-001): the platform
// renders this with no surrounding Studio chrome, so this component owns
// the entire LTSA-facing shell (IdentityBar + LTSAWorkspace). Authentication
// is a state of this one product, not a second application -- when
// authenticated this renders the exact same LTSAWorkspace every other MWO
// already built, with only tab visibility now permission-driven.
export default function LTSAAuthGate(props) {
  return (
    <AuthProvider>
      <LTSAAuthGateInner {...props} />
    </AuthProvider>
  );
}
