import { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import { visibleTabKeys, can, PERMISSIONS } from "../auth/permissions";
import LoginView from "./LoginView";
import LTSAWorkspace from "./LTSAWorkspace";
import AdminUsersView from "./AdminUsersView";
import "./LTSAOpenDesign.css";
import "./LTSAAuthGate.css";

// MWO-LTSA-AUTH-003A-FINAL
const ROLE_LABEL = {
  SUPERUSER: "Superuser",
  TAP_ADMIN: "TAP Admin",
  TAP_ENGINEER: "TAP Engineer",
  JOHN_CRANE_ENGINEER: "John Crane Engineer",
  PERTAMINA_ENGINEER: "Pertamina Engineer",
  PERTAMINA_VIEWER: "Pertamina Viewer",
};

// MWO-LTSA-ADMIN-USERS-WIRING-001 -- the one route this gate itself owns,
// deliberately separate from LTSAWorkspace's own internal WORKSPACE_KEYS
// tab routing (WorkspaceRegistry.js), which this file does not touch.
// Phase 0's own audit found WorkspaceRegistry.js/LTSAWorkspace.jsx/
// WorkspaceShell.jsx are substantial, currently-uncommitted, unrelated
// in-progress WIP -- and precisely LTSAWorkspace.jsx's own TABS/PAGES
// insertion point sits inside that WIP's own already-modified lines
// (confirmed via `git diff`'s hunk boundaries), so extending it here
// would either corrupt that work or force it into this commit. Routing
// one layer up instead (before LTSAWorkspace is even rendered) reuses the
// exact same pushState/popstate convention LTSAWorkspace.jsx's own
// handleNavigate/workspaceLocation/parseWorkspaceLocation already
// establish -- not a parallel router, the same one applied one level
// higher, entirely within already-clean, already-committed files.
const ADMIN_USERS_ROUTE = "/ltsa/admin/users";

function IdentityBar({ session, onLogout, canManageUsers, isAdminUsersRoute, onNavigateAdminUsers, onNavigateWorkspace }) {
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
                {/* MWO-LTSA-ADMIN-USERS-WIRING-001 -- capability-driven,
                    never `role === "..."`. Hiding this is UX only: the
                    backend (routers/admin_users.py) and AdminUsersView's
                    own canManageUsers prop remain the real gate even if a
                    non-admin user reaches the route directly. */}
                {canManageUsers && !isAdminUsersRoute && (
                  <button type="button" className="btn-link auth-identity-admin-users" onClick={onNavigateAdminUsers}>
                    Admin — Users
                  </button>
                )}
                {isAdminUsersRoute && (
                  <button type="button" className="btn-link auth-identity-back-to-workspace" onClick={onNavigateWorkspace}>
                    Back to LTSA Workspace
                  </button>
                )}
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

// MWO-AI5R-LTSA-COPILOT-001 -- repointed from "history" to "dashboard" so
// a successful login lands directly on the Executive Dashboard (where the
// new Engineering Copilot is mounted), per this MWO's own "Dashboard AI
// must be immediately usable after login" requirement -- the one minimum
// redirect change its Hard Rule 8 allows. Guard below is unchanged: a
// role without dashboard access (PERMISSIONS.DASHBOARD_READ ==
// internal_inventory.read -- TAP_ADMIN/TAP_ENGINEER/SUPERUSER only, per
// permissions.js's own frozen-screenshot rationale) still falls back to
// that role's first visible tab, exactly as it already did for "history".
const DEFAULT_LANDING_KEY = "dashboard";

function AuthenticatedLTSA({ organizationContext, platformContext }) {
  const { session, logout } = useAuth();
  const [pathname, setPathname] = useState(window.location.pathname);
  const allowedKeys = visibleTabKeys(session);
  const capabilities = {
    allowedKeys,
    can: (permission) => can(session, permission),
  };
  const initialActiveKey = allowedKeys.includes(DEFAULT_LANDING_KEY) ? DEFAULT_LANDING_KEY : allowedKeys[0];
  const canManageUsers = can(session, PERMISSIONS.ADMIN_ACCESS);
  const isAdminUsersRoute = pathname === ADMIN_USERS_ROUTE;

  useEffect(() => {
    function handlePopState() {
      setPathname(window.location.pathname);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigateTo(path) {
    window.history.pushState({}, "", path);
    setPathname(path);
  }

  return (
    <div>
      <IdentityBar
        session={session}
        onLogout={logout}
        canManageUsers={canManageUsers}
        isAdminUsersRoute={isAdminUsersRoute}
        onNavigateAdminUsers={() => navigateTo(ADMIN_USERS_ROUTE)}
        onNavigateWorkspace={() => navigateTo("/ltsa")}
      />
      {isAdminUsersRoute ? (
        // MWO-LTSA-ADMIN-USERS-WIRING-001 -- Phase 3 direct-route security:
        // canManageUsers is passed through unconditionally; a user who
        // reaches this route without admin.users (e.g. by typing the URL)
        // gets AdminUsersView's own already-tested "Not authorized"
        // EmptyState, never the real user list/actions -- the backend
        // (every /api/admin/users route) remains the actual enforcement
        // point regardless of what this prop says.
        <AdminUsersView canManageUsers={canManageUsers} session={session} />
      ) : (
        <LTSAWorkspace
          initialActiveKey={initialActiveKey}
          capabilities={capabilities}
          organizationContext={organizationContext}
          platformContext={platformContext}
        />
      )}
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
