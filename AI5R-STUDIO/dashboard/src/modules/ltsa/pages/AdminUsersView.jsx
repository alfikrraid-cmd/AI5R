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
    email: "", password: "", organizationId: "", role: "TAP_ENGINEER",
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
    const newPassword = window.prompt(`New password for ${user.email}:`);
    if (!newPassword) return;
    runAction(() => resetAdminUserPassword(user.id, newPassword));
  }

  function handleCreateSubmit(event) {
    event.preventDefault();
    runAction(() =>
      createAdminUser({
        email: createForm.email,
        password: createForm.password,
        organizationId: createForm.organizationId,
        role: createForm.role,
      })
    );
    setShowCreate(false);
    setCreateForm({ email: "", password: "", organizationId: "", role: "TAP_ENGINEER" });
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
            aria-label="Email"
            placeholder="Email"
            value={createForm.email}
            onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
            required
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
            { key: "email", header: "Email" },
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
                    aria-label={`Change role for ${user.email}`}
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
