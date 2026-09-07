import { useEffect, useRef, useState } from "react";
import { Badge, Button, EmptyState } from "../../../design-system";
import {
  activateWhatsAppNumber,
  getAdminUsers,
  getWhatsAppSenderStatus,
  registerWhatsAppNumber,
} from "../../../api/ai5rClient";

/**
 * AI5R-WHATSAPP-SENDER-ADMIN-001 / AI5R-WHATSAPP-SENDER-STATUS-001 --
 * LTSA Admin -> WhatsApp Groups -> Sender Access.
 *
 * Links a WhatsApp phone number to an EXISTING AI5R user account
 * (POST /api/admin/users/{user_id}/whatsapp/register then .../activate)
 * and, on user selection, auto-loads that user's ACTUAL WhatsApp status
 * from the canonical read-only lookup
 * (GET /api/admin/users/{user_id}/whatsapp/status) -- all three routes
 * on routers/admin_users.py, same admin.users-gated router and
 * apiFetch/_adminUsersRequest mechanism the rest of this admin area
 * already uses. This screen never assigns or changes role/scope: those
 * remain organization_memberships' own source of truth, so there is
 * deliberately no control here that could set either -- the user picker
 * and the read-only Role field are the only user-identity inputs.
 *
 * Scope note: GET /api/admin/users (the canonical admin user source
 * reused below for the picker) does not currently return
 * data_scope_type/data_scope_value for a user -- verified directly
 * against routers/admin_users.py's own _user_summary() projection.
 * Rather than fabricate a value, the Scope row says so plainly.
 *
 * The raw phone number lives only in local React state while the admin
 * is typing it, is sent once in the register request body, and is
 * cleared immediately after that request settles (success or failure
 * alike), and also whenever the selected user changes -- never written
 * to localStorage/sessionStorage, never logged. No backend response in
 * this flow (register/activate/status) ever echoes the raw phone back.
 * The returned sender_e164_sha256 (a one-way hash, not the phone
 * itself) is exposed by the status lookup ONLY while PENDING (needed to
 * complete Activate -- see get_whatsapp_identity_status's own docstring
 * on the backend), never once ACTIVE, and is never displayed in this UI
 * either way -- shown as "REDACTED", consistent with Group Authorization.
 *
 * State-safety (owner UAT finding, generalized to the new auto-load
 * flow): every status lookup/register/activate result is tagged with
 * the user_id the request was actually made for, and every render of
 * that result is gated on `entry.userId === selectedUserId` -- a
 * response for a previously selected user can still resolve and get
 * stored after the admin has switched to someone else, but it can never
 * be displayed for the wrong user, nor can its hash be handed to
 * Activate for the wrong user (see statusForSelectedUser below).
 */
function friendlyErrorMessage(error) {
  return error?.message || "Admin Users API unavailable";
}

function statusKindFor(data) {
  if (data?.status === "ACTIVE") return "ACTIVE";
  if (data?.status === "PENDING") return "PENDING";
  return "NOT_REGISTERED";
}

export default function WhatsAppSenderAccessView() {
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [phoneInput, setPhoneInput] = useState("");
  const [validationError, setValidationError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [activating, setActivating] = useState(false);
  // { userId, kind: "LOADING"|"NOT_REGISTERED"|"PENDING"|"ACTIVE"|"ERROR", data?, message? } | null
  const [status, setStatus] = useState(null);
  // Tracks the LATEST selectedUserId synchronously (state itself is only
  // current as of the last render) so a stale async response can check
  // "is this still what's selected" at resolution time, not call time --
  // and be truly ignored (never even written to `status`) rather than
  // merely hidden by a render-time gate, per Gate 6's own "ignore stale
  // responses" requirement (distinct from "render only current data").
  const selectedUserIdRef = useRef(selectedUserId);

  useEffect(() => {
    setUsersLoading(true);
    setUsersError(null);
    getAdminUsers()
      .then((rows) => setUsers(Array.isArray(rows) ? rows : []))
      .catch((err) => setUsersError(friendlyErrorMessage(err)))
      .finally(() => setUsersLoading(false));
  }, []);

  const selectedUser = users.find((u) => u.id === selectedUserId) ?? null;
  // Only ever non-null when it was produced BY and FOR the currently
  // selected user -- a stale response for a previously selected user
  // may still be sitting in `status`, but it never satisfies this.
  const statusForSelectedUser = status && status.userId === selectedUserId ? status : null;

  async function loadStatus(userId) {
    setStatus({ userId, kind: "LOADING" });
    try {
      const response = await getWhatsAppSenderStatus(userId);
      if (userId !== selectedUserIdRef.current) return; // stale -- ignored entirely
      const data = response?.data ?? { registered: false, status: "NOT_REGISTERED" };
      setStatus({ userId, kind: statusKindFor(data), data });
    } catch (error) {
      if (userId !== selectedUserIdRef.current) return;
      // Never transformed into NOT_REGISTERED -- a failed lookup is not
      // evidence of anything about the user's actual registration state.
      setStatus({ userId, kind: "ERROR", message: friendlyErrorMessage(error) });
    }
  }

  function handleSelectUser(userId) {
    selectedUserIdRef.current = userId;
    setSelectedUserId(userId);
    setPhoneInput("");
    setActionError(null);
    setValidationError(null);
    if (userId) {
      loadStatus(userId);
    } else {
      setStatus(null);
    }
  }

  async function handleRegisterSubmit(event) {
    event.preventDefault();
    const phoneNumber = phoneInput.trim();
    const requestUserId = selectedUserId;
    setValidationError(null);
    setActionError(null);

    if (!requestUserId) {
      setValidationError("Select a user first.");
      return;
    }
    if (!phoneNumber) {
      setValidationError("WhatsApp number is required.");
      return;
    }

    setSubmitting(true);
    try {
      await registerWhatsAppNumber(requestUserId, { phoneNumber });
      // Never rely on the register response alone -- re-fetch the
      // canonical status so the card reflects what the backend actually
      // stored, tagged/gated exactly like every other lookup here.
      await loadStatus(requestUserId);
    } catch (error) {
      setActionError(friendlyErrorMessage(error));
    } finally {
      // Cleared whether the request succeeded or failed -- this
      // component never keeps the raw phone number around past one
      // submit.
      setPhoneInput("");
      setSubmitting(false);
    }
  }

  async function handleActivate() {
    // Only ever acts on the CURRENTLY selected user's own PENDING
    // status -- the sender_e164_sha256 used here can never belong to a
    // different user, because statusForSelectedUser is already gated.
    if (statusForSelectedUser?.kind !== "PENDING" || !statusForSelectedUser.data?.sender_e164_sha256) return;
    const requestUserId = selectedUserId;
    const senderHash = statusForSelectedUser.data.sender_e164_sha256;
    setActionError(null);
    setActivating(true);
    try {
      await activateWhatsAppNumber(requestUserId, senderHash);
      await loadStatus(requestUserId);
    } catch (error) {
      setActionError(friendlyErrorMessage(error));
    } finally {
      setActivating(false);
    }
  }

  return (
    <div className="ltsa-open-design" data-testid="whatsapp-sender-access-view" style={{ marginTop: "var(--space-6)" }}>
      <h2 style={{ margin: 0 }}>Sender Access</h2>
      <p className="confidence-label">WhatsApp access inherits this user's existing AI5R role and scope.</p>

      {actionError && (
        <p
          className="confidence-label"
          style={{ color: "var(--color-danger, #d33)" }}
          data-testid="whatsapp-sender-action-error"
        >
          {actionError}
        </p>
      )}

      {usersLoading && <p className="confidence-label">Loading users…</p>}
      {usersError && <EmptyState title="Users unavailable" description={usersError} />}

      {!usersLoading && !usersError && (
        <div style={{ marginTop: "var(--space-4)" }}>
          <label htmlFor="whatsapp-sender-user">User</label>
          <select
            id="whatsapp-sender-user"
            aria-label="User"
            value={selectedUserId}
            onChange={(e) => handleSelectUser(e.target.value)}
          >
            <option value="">Select a user…</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.username || u.email || u.id}
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedUser && (
        <div data-testid="whatsapp-sender-user-detail">
          <p>Name: {selectedUser.username ?? "—"}</p>
          <p>Email: {selectedUser.email ?? "—"}</p>
          <p>Organization: {selectedUser.organization_name ?? selectedUser.organization_code ?? "—"}</p>
          <p>
            Role: <span data-testid="whatsapp-sender-role">{selectedUser.role ?? "—"}</span> (read-only)
          </p>
          <p>
            Scope:{" "}
            <span data-testid="whatsapp-sender-scope">Not exposed by the current Admin Users API</span> (read-only)
          </p>
        </div>
      )}

      {selectedUser && (
        <div data-testid="whatsapp-sender-status-card" style={{ marginTop: "var(--space-4)" }}>
          {statusForSelectedUser?.kind === "LOADING" && (
            <p className="confidence-label" data-testid="whatsapp-sender-status-loading">
              Loading WhatsApp status…
            </p>
          )}

          {statusForSelectedUser?.kind === "ERROR" && (
            <>
              <p
                className="confidence-label"
                style={{ color: "var(--color-danger, #d33)" }}
                data-testid="whatsapp-sender-status-error"
              >
                Unable to load WhatsApp access status.
              </p>
              <Button onClick={() => loadStatus(selectedUserId)}>Retry</Button>
            </>
          )}

          {statusForSelectedUser?.kind === "ACTIVE" && (
            <>
              <p>
                Identifier: <span data-testid="whatsapp-sender-redacted-id">REDACTED</span>
              </p>
              {statusForSelectedUser.data?.provider && <p>Provider: {statusForSelectedUser.data.provider}</p>}
              <p>
                Status: <Badge variant="success">ACTIVE</Badge>
              </p>
            </>
          )}

          {statusForSelectedUser?.kind === "PENDING" && (
            <>
              <p>
                Identifier: <span data-testid="whatsapp-sender-redacted-id">REDACTED</span>
              </p>
              {statusForSelectedUser.data?.provider && <p>Provider: {statusForSelectedUser.data.provider}</p>}
              <p>
                Status: <Badge variant="warning">PENDING</Badge>
              </p>
              <Button onClick={handleActivate} disabled={activating}>
                {activating ? "Activating…" : "Activate Number"}
              </Button>
            </>
          )}

          {statusForSelectedUser?.kind === "NOT_REGISTERED" && (
            <>
              <p data-testid="whatsapp-sender-not-registered">Not registered</p>
              <form onSubmit={handleRegisterSubmit} data-testid="whatsapp-sender-register-form">
                <div>
                  <label htmlFor="whatsapp-sender-number">WhatsApp Number</label>
                  <input
                    id="whatsapp-sender-number"
                    aria-label="WhatsApp Number"
                    placeholder="+62..."
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    autoComplete="off"
                  />
                </div>
                {validationError && (
                  <p
                    className="confidence-label"
                    style={{ color: "var(--color-danger, #d33)" }}
                    data-testid="whatsapp-sender-validation-error"
                  >
                    {validationError}
                  </p>
                )}
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Registering…" : "Register Number"}
                </Button>
              </form>
            </>
          )}
        </div>
      )}
    </div>
  );
}
