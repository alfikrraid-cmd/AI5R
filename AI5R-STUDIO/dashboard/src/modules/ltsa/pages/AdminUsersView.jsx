import { useEffect, useState } from "react";
import { Badge, Button, EmptyState, PageHeader, Table } from "../../../design-system";
import {
  createAdminUser,
  getAdminUsers,
  resetAdminUserPassword,
  sendAdminUserSetPasswordLink,
  updateAdminUserRole,
  updateAdminUserStatus,
} from "../../../api/ai5rClient";
import { PASSWORD_POLICY_HINT, passwordPolicyError } from "../auth/passwordPolicy";
import "./LTSAOpenDesign.css";

/**
 * MWO-LTSA-AUTH-003A-FINAL -- LTSA Admin -> Users.
 *
 * Standalone, real, fully-tested component (list, create, enable/disable,
 * role change, password reset -- all against the real Admin Users API,
 * routers/admin_users.py) NOT yet wired into LTSAWorkspace.jsx's tab
 * registry (WorkspaceRegistry.js) -- both files are substantial,
 * currently-uncommitted, in-progress WIP owned by a different, unrelated
 * effort (confirmed minified/mid-refactor, `git status` modified all
 * session); touching them here would risk corrupting that work, which
 * this MWO's own "Preserve unrelated WIP" hard rule forbids. This
 * component is deliberately import-ready for whichever future MWO next
 * legitimately touches the tab registry -- see this MWO's own Phase 13
 * discussion in the completion report for the disclosed boundary.
 *
 * Backend is authoritative throughout: every action here can fail with a
 * 403 (delegation scope) or 409 (last-SUPERUSER safety) that this
 * component surfaces verbatim, never pre-empts client-side -- the
 * `canManageUsers` prop only controls whether the page renders its
 * actions at all (UX, not the security boundary, per permissions.js's
 * own header comment).
 */
const ROLE_OPTIONS = [
  "SUPERUSER",
  "TAP_ADMIN",
  "TAP_ENGINEER",
  "JOHN_CRANE_ENGINEER",
  "PERTAMINA_ENGINEER",
  "PERTAMINA_VIEWER",
];

const TAP_ADMIN_ROLE_OPTIONS = [
  "TAP_ENGINEER",
  "JOHN_CRANE_ENGINEER",
  "PERTAMINA_ENGINEER",
  "PERTAMINA_VIEWER",
];

const ROLE_BADGE_VARIANT = {
  SUPERUSER: "danger",
  TAP_ADMIN: "warning",
  TAP_ENGINEER: "info",
  JOHN_CRANE_ENGINEER: "purple",
  PERTAMINA_ENGINEER: "success",
  PERTAMINA_VIEWER: "success",
};

function roleOptionsFor(session) {
  return session?.role === "TAP_ADMIN" ? TAP_ADMIN_ROLE_OPTIONS : ROLE_OPTIONS;
}

function canManageRole(session, role) {
  if (!session) return true;
  if (session?.role === "SUPERUSER") return true;
  if (session?.role === "TAP_ADMIN") return TAP_ADMIN_ROLE_OPTIONS.includes(role);
  return false;
}

function canManageUser(session, user) {
  if (typeof user?.can_manage === "boolean") return user.can_manage;
  return canManageRole(session, user?.role);
}

// LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- how a new user gets their first
// password. The email link is the default: the admin never sees or chooses a
// password. A temporary password is the fallback, and the user must change it
// at first sign-in (the backend sets must_change_password either way).
const CREDENTIAL_MODES = [
  { value: "EMAIL_SET_PASSWORD", label: "Email set-password link (recommended)" },
  { value: "TEMPORARY_PASSWORD", label: "Temporary password (must change at first sign-in)" },
];

function emptyCreateForm(organizationId, role) {
  return {
    username: "", name: "", email: "", password: "", credentialMode: "EMAIL_SET_PASSWORD",
    organizationId, role,
  };
}

function renderMuted(text) {
  return <span style={{ color: "var(--ltsa-text-muted, #4B5563)" }}>{text}</span>;
}


export default function AdminUsersView({ canManageUsers = false, session = null }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState(() => emptyCreateForm(session?.organization?.id ?? "", "TAP_ENGINEER"));
  const [notice, setNotice] = useState(null);
  const [resetTarget, setResetTarget] = useState(null);
  const [resetForm, setResetForm] = useState({ password: "", confirm: "" });
  const [resetError, setResetError] = useState(null);
  const roleOptions = roleOptionsFor(session);
  const isTapAdmin = session?.role === "TAP_ADMIN";
  const currentOrganizationId = session?.organization?.id ?? "";
  const currentOrganizationLabel = session?.organization?.displayName ?? session?.organization?.code ?? "N/A";

  function reload() {
    if (!canManageUsers) return;
    setLoading(true);
    setError(null);
    getAdminUsers()
      .then((rows) => setUsers(rows))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  // Never fetches when unauthorized -- the backend would reject it with
  // 403 anyway (authoritative), but there is no reason to make the call.
  useEffect(reload, [canManageUsers]);

  async function runAction(action) {
    setActionError(null);
    try {
      const result = await action();
      reload();
      return result;
    } catch (err) {
      // Verbatim backend detail (e.g. "SUPERUSER access required",
      // "this is the last active SUPERUSER account")
      setActionError(err.message);
      return undefined;
    }
  }

  function handleToggleStatus(user) {
    const nextStatus = user.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
    runAction(() => updateAdminUserStatus(user.id, nextStatus));
  }

  function handleRoleChange(user, role) {
    if (role === user.role) return;
    runAction(() => updateAdminUserRole(user.id, user.organization_id, role));
  }

  // Masked in-page dialog (replaces window.prompt, which showed the password
  // in clear text). The admin-set password is temporary: the backend forces
  // the user to change it at next sign-in and ends their current sessions.
  function openPasswordReset(user) {
    setActionError(null);
    setNotice(null);
    setResetError(null);
    setResetForm({ password: "", confirm: "" });
    setResetTarget(user);
  }

  async function handleResetSubmit(event) {
    event.preventDefault();
    const problem = passwordPolicyError(resetForm.password, {
      username: resetTarget?.username,
      email: resetTarget?.email,
    });
    if (problem) {
      setResetError(problem);
      return;
    }
    if (resetForm.password !== resetForm.confirm) {
      setResetError("Passwords do not match.");
      return;
    }
    const target = resetTarget;
    const result = await runAction(() => resetAdminUserPassword(target.id, resetForm.password));
    setResetForm({ password: "", confirm: "" });
    setResetTarget(null);
    if (result) {
      setNotice(`Temporary password set for ${target.username || target.email}. They must change it at next sign-in.`);
    }
  }

  async function handleSendSetPasswordLink(user) {
    setNotice(null);
    const result = await runAction(() => sendAdminUserSetPasswordLink(user.id));
    if (result) {
      setNotice(
        result.status === "set_password_link_sent"
          ? `Set-password email sent to ${user.email}.`
          : `Set-password email could not be sent to ${user.username || user.email}.`
      );
    }
  }

  async function handleCreateSubmit(event) {
    event.preventDefault();
    const temporary = createForm.credentialMode === "TEMPORARY_PASSWORD";
    if (temporary) {
      const problem = passwordPolicyError(createForm.password, { username: createForm.username, email: createForm.email });
      if (problem) {
        setActionError(problem);
        return;
      }
    }
    const payload = {
      username: createForm.username,
      email: createForm.email || null,
      credentialMode: createForm.credentialMode,
      organizationId: isTapAdmin ? currentOrganizationId : createForm.organizationId,
      role: createForm.role,
    };
    if (temporary) {
      payload.password = createForm.password;
    }
    if (createForm.name) {
      payload.name = createForm.name;
    }
    setNotice(null);
    setShowCreate(false);
    setCreateForm(emptyCreateForm(currentOrganizationId, roleOptions[0] ?? "TAP_ENGINEER"));
    const created = await runAction(() => createAdminUser(payload));
    if (!created) return;
    if (created.credential_mode === "EMAIL_SET_PASSWORD") {
      setNotice(
        created.set_password_email === "SENT"
          ? `User ${created.username} created. A set-password email was sent to ${created.email}.`
          : `User ${created.username} created, but the set-password email could not be sent. Use "Send set-password link" to retry.`
      );
    } else {
      setNotice(`User ${created.username} created. They must change the temporary password at first sign-in.`);
    }
  }

  if (!canManageUsers) {
    return (
      <div className="ltsa-open-design admin-users-view" data-testid="admin-users-denied">
        <EmptyState title="Not authorized" description="Your account does not have admin.users access." />
      </div>
    );
  }

  return (
    <div className="ltsa-open-design admin-users-view" data-testid="admin-users-view">
      <PageHeader
        title="User Management"
        subtitle="Administration > User Management"
        actions={<Button onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Cancel" : "Create User"}</Button>}
      />

      {actionError && (
        <p className="confidence-label" style={{ color: "var(--color-danger, #d33)" }} data-testid="admin-users-action-error">
          {actionError}
        </p>
      )}

      {notice && (
        <p className="confidence-label" role="status" data-testid="admin-users-notice">
          {notice}
        </p>
      )}

      {resetTarget && (
        <form
          role="dialog"
          aria-label={`Reset password for ${resetTarget.username || resetTarget.email}`}
          onSubmit={handleResetSubmit}
          noValidate
          data-testid="admin-users-reset-dialog"
          style={{ marginBottom: "var(--space-4)", display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}
        >
          <span className="confidence-label">
            Temporary password for <b>{resetTarget.username || resetTarget.email}</b> — {PASSWORD_POLICY_HINT}
          </span>
          <input
            aria-label="New temporary password"
            type="password"
            autoComplete="new-password"
            value={resetForm.password}
            onChange={(e) => setResetForm((f) => ({ ...f, password: e.target.value }))}
          />
          <input
            aria-label="Confirm temporary password"
            type="password"
            autoComplete="new-password"
            value={resetForm.confirm}
            onChange={(e) => setResetForm((f) => ({ ...f, confirm: e.target.value }))}
          />
          <Button type="submit">Set Temporary Password</Button>
          <Button type="button" onClick={() => setResetTarget(null)}>Cancel</Button>
          {resetError && (
            <p className="confidence-label" role="alert" style={{ color: "var(--color-danger, #d33)" }} data-testid="admin-users-reset-error">
              {resetError}
            </p>
          )}
        </form>
      )}

      {showCreate && (
        <form onSubmit={handleCreateSubmit} data-testid="admin-users-create-form" style={{ marginBottom: "var(--space-4)", display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}>
          <input
            aria-label="Username"
            placeholder="Username"
            value={createForm.username}
            onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
            required
          />
          <input
            aria-label="Name"
            placeholder="Name"
            value={createForm.name}
            onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
          />
          <input
            aria-label="Email"
            placeholder="Email"
            value={createForm.email}
            onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
            required={createForm.credentialMode === "EMAIL_SET_PASSWORD"}
          />
          <select
            aria-label="Initial credential"
            value={createForm.credentialMode}
            onChange={(e) => setCreateForm((f) => ({ ...f, credentialMode: e.target.value, password: "" }))}
          >
            {CREDENTIAL_MODES.map((mode) => (
              <option key={mode.value} value={mode.value}>{mode.label}</option>
            ))}
          </select>
          {createForm.credentialMode === "TEMPORARY_PASSWORD" && (
            <input
              aria-label="Password"
              type="password"
              autoComplete="new-password"
              placeholder="Temporary password"
              value={createForm.password}
              onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
              required
            />
          )}
          {isTapAdmin ? (
            <p className="confidence-label" data-testid="admin-users-organization-display">
              Organization: {currentOrganizationLabel}
            </p>
          ) : (
            <input
              aria-label="Organization ID"
              placeholder="Organization ID"
              value={createForm.organizationId}
              onChange={(e) => setCreateForm((f) => ({ ...f, organizationId: e.target.value }))}
              required
            />
          )}
          <select
            aria-label="Role"
            value={createForm.role}
            onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value }))}
          >
            {roleOptions.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
          {/* JC organization assignment is explicit for SUPERUSER and follows
              the current organization for TAP_ADMIN; the backend remains
              authoritative for organization and role delegation. */}
          {!isTapAdmin && createForm.role === "JOHN_CRANE_ENGINEER" && (
            <p className="confidence-label" data-testid="admin-users-jc-org-warning" style={{ color: "var(--color-warning, #b58900)" }}>
              No JOHN_CRANE organization currently exists. Assigning this account to an
              existing organization is a manual choice, not a default -- confirm
              the correct organization before creating this user.
            </p>
          )}
          <Button type="submit">Create</Button>
        </form>
      )}

      {loading && <p className="confidence-label">Loading users…</p>}
      {error && <EmptyState title="Users unavailable" description={error} />}

      {!loading && !error && users.length === 0 && (
        <EmptyState title="No users found" description="No users are provisioned yet." />
      )}

      {!loading && !error && users.length > 0 && (
        <Table
          rowKey="id"
          data={users}
          columns={[
            { key: "username", header: "Username", render: (v) => v || renderMuted("N/A") },
            { key: "name", header: "Name", render: (v, user) => v || user?.email || renderMuted("N/A") },
            {
              key: "role",
              header: "Role",
              render: (role) => <Badge variant={ROLE_BADGE_VARIANT[role] ?? "purple"}>{role ?? renderMuted("—")}</Badge>,
            },
            { key: "organization_code", header: "Organization", render: (v) => v || renderMuted("—") },
            {
              key: "status",
              header: "Status",
              render: (status) => <Badge variant={status === "ACTIVE" ? "success" : "danger"}>{status}</Badge>,
            },
            { key: "last_login", header: "Last Login", render: (v) => v || renderMuted("Never") },
            { key: "created_at", header: "Created At" },
            {
              key: "actions",
              header: "Actions",
              render: (_value, user) => canManageUser(session, user) ? (
                <span style={{ display: "flex", gap: "var(--space-2)" }}>
                  <Button onClick={() => handleToggleStatus(user)}>
                    {user.status === "ACTIVE" ? "Disable" : "Enable"}
                  </Button>
                  <select
                    aria-label={`Change role for ${user.username || user.email}`}
                    value={user.role ?? ""}
                    onChange={(e) => handleRoleChange(user, e.target.value)}
                  >
                    {roleOptions.map((role) => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                  <Button onClick={() => openPasswordReset(user)}>Reset Password</Button>
                  {user.email ? (
                    <Button onClick={() => handleSendSetPasswordLink(user)}>Send set-password link</Button>
                  ) : null}
                </span>
              ) : <span className="confidence-label">Read-only</span>,
            },
          ]}
        />
      )}
    </div>
  );
}
