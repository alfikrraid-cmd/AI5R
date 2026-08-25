import { useEffect, useState } from "react";
import { Badge, Button, EmptyState, PageHeader, Table } from "../../../design-system";
import {
  createAdminUser,
  getAdminUsers,
  resetAdminUserPassword,
  updateAdminUserRole,
  updateAdminUserStatus,
} from "../../../api/ai5rClient";
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

const ROLE_BADGE_VARIANT = {
  SUPERUSER: "danger",
  TAP_ADMIN: "warning",
  TAP_ENGINEER: "info",
  JOHN_CRANE_ENGINEER: "purple",
  PERTAMINA_ENGINEER: "success",
  PERTAMINA_VIEWER: "success",
};

export default function AdminUsersView({ canManageUsers = false }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: "", email: "", password: "", organizationId: "", role: "TAP_ENGINEER",
  });

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
      await action();
      reload();
    } catch (err) {
      // Verbatim backend detail (e.g. "TAP_ADMIN is not authorized to
      // manage SUPERUSER accounts", "this is the last active SUPERUSER
      // account") -- never a generic "failed" message.
      setActionError(err.message);
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

  function handlePasswordReset(user) {
    const newPassword = window.prompt(`New password for ${user.username || user.email}:`);
    if (!newPassword) return;
    runAction(() => resetAdminUserPassword(user.id, newPassword));
  }

  function handleCreateSubmit(event) {
    event.preventDefault();
    runAction(() =>
      createAdminUser({
        username: createForm.username,
        email: createForm.email || null,
        password: createForm.password,
        organizationId: createForm.organizationId,
        role: createForm.role,
      })
    );
    setShowCreate(false);
    setCreateForm({ username: "", email: "", password: "", organizationId: "", role: "TAP_ENGINEER" });
  }

  if (!canManageUsers) {
    return (
      <div className="ltsa-open-design" data-testid="admin-users-denied">
        <EmptyState title="Not authorized" description="Your account does not have admin.users access." />
      </div>
    );
  }

  return (
    <div className="ltsa-open-design" data-testid="admin-users-view">
      <PageHeader
        title="Users"
        subtitle="LTSA Admin — user administration"
        actions={<Button onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Cancel" : "Create User"}</Button>}
      />

      {actionError && (
        <p className="confidence-label" style={{ color: "var(--color-danger, #d33)" }} data-testid="admin-users-action-error">
          {actionError}
        </p>
      )}

      {showCreate && (
        <form onSubmit={handleCreateSubmit} data-testid="admin-users-create-form" style={{ marginBottom: "var(--space-4)" }}>
          <input
            aria-label="Username"
            placeholder="Username"
            value={createForm.username}
            onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
            required
          />
          <input
            aria-label="Email"
            placeholder="Email"
            value={createForm.email}
            onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
          />
          <input
            aria-label="Password"
            type="password"
            placeholder="Temporary password"
            value={createForm.password}
            onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
            required
          />
          <input
            aria-label="Organization ID"
            placeholder="Organization ID"
            value={createForm.organizationId}
            onChange={(e) => setCreateForm((f) => ({ ...f, organizationId: e.target.value }))}
            required
          />
          <select
            aria-label="Role"
            value={createForm.role}
            onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value }))}
          >
            {ROLE_OPTIONS.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
          {/* MWO-LTSA-ADMIN-USERS-WIRING-001 -- Phase 5: no "JOHN_CRANE"
              organization exists yet (AUTH-003A-FINAL's own disclosed gap;
              not fabricated here). This is a visible warning, not a
              block -- the backend accepts any existing organization_id
              the caller supplies, and only a SUPERUSER can even reach
              this form for this role (JOHN_CRANE_ENGINEER is outside
              TAP_ADMIN's delegation scope). Assigning the new account to
              TAP's own organization is never done silently by this form;
              the operator must type that organization id themselves,
              with this warning visible. */}
          {createForm.role === "JOHN_CRANE_ENGINEER" && (
            <p className="confidence-label" data-testid="admin-users-jc-org-warning" style={{ color: "var(--color-warning, #b58900)" }}>
              No JOHN_CRANE organization currently exists. Assigning this account to an
              existing organization (e.g. TAP) is a manual choice, not a default -- confirm
              the correct Organization ID before creating this user.
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
            { key: "username", header: "Username", render: (v) => v ?? "N/A" },
            { key: "email", header: "Email", render: (v) => v ?? "N/A" },
            {
              key: "role",
              header: "Role",
              render: (role) => <Badge variant={ROLE_BADGE_VARIANT[role] ?? "purple"}>{role ?? "—"}</Badge>,
            },
            { key: "organization_code", header: "Organization", render: (v) => v ?? "—" },
            {
              key: "status",
              header: "Status",
              render: (status) => <Badge variant={status === "ACTIVE" ? "success" : "danger"}>{status}</Badge>,
            },
            { key: "created_at", header: "Created At" },
            { key: "updated_at", header: "Last Updated At" },
            {
              key: "actions",
              header: "Actions",
              render: (_value, user) => (
                <span style={{ display: "flex", gap: "var(--space-2)" }}>
                  <Button onClick={() => handleToggleStatus(user)}>
                    {user.status === "ACTIVE" ? "Disable" : "Enable"}
                  </Button>
                  <select
                    aria-label={`Change role for ${user.username || user.email}`}
                    value={user.role ?? ""}
                    onChange={(e) => handleRoleChange(user, e.target.value)}
                  >
                    {ROLE_OPTIONS.map((role) => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                  <Button onClick={() => handlePasswordReset(user)}>Reset Password</Button>
                </span>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
