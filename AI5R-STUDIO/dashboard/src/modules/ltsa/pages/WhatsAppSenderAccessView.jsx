import { useEffect, useState } from "react";
import { Badge, Button, EmptyState } from "../../../design-system";
import { activateWhatsAppNumber, getAdminUsers, registerWhatsAppNumber } from "../../../api/ai5rClient";

/**
 * AI5R-WHATSAPP-SENDER-ADMIN-001 -- LTSA Admin -> WhatsApp Groups ->
 * Sender Access.
 *
 * Links a WhatsApp phone number to an EXISTING AI5R user account
 * (POST /api/admin/users/{user_id}/whatsapp/register then .../activate,
 * routers/admin_users.py) -- the same admin.users-gated router and
 * apiFetch mechanism the rest of this admin area already uses. This
 * screen never assigns or changes role/scope: those remain
 * organization_memberships' own source of truth (whatsapp_registration_
 * service.py's own header), so there is deliberately no control here
 * that could set either -- the user picker and the read-only Role field
 * are the only user-identity inputs.
 *
 * Scope note: GET /api/admin/users (the canonical admin user source
 * reused below) does not currently return data_scope_type/
 * data_scope_value for a user -- verified directly against
 * routers/admin_users.py's own _user_summary() projection, which has no
 * such field. Rather than fabricate a value, the Scope row says so
 * plainly; it is not a placeholder for a future value this component
 * invents.
 *
 * The raw phone number lives only in local React state while the admin
 * is typing it, is sent once in the register request body, and is
 * cleared immediately after that request settles (success or failure
 * alike), and also whenever the selected user changes -- never written
 * to localStorage/sessionStorage, never logged. The backend's own
 * register/activate responses never echo the raw phone back either. The
 * returned sender_e164_sha256 (a one-way hash, not the phone itself) is
 * kept only long enough to pass to activate, and is not displayed --
 * shown as "REDACTED" as an extra precaution, consistent with how the
 * Group Authorization section above treats its own identifier.
 *
 * State-safety note (owner UAT finding): there is no GET endpoint that
 * looks up an existing sender's status by user_id -- only POST register
 * and POST activate exist on routers/admin_users.py -- so this screen
 * cannot ask the backend "what is this user's current WhatsApp status"
 * on selection; it can only know the outcome of a register/activate
 * call made THIS session. Two things follow from that:
 *   1. Switching the selected user must show a neutral "not loaded"
 *      state, never a leftover ACTIVE/PENDING badge -- this was already
 *      true synchronously (handleSelectUser clears `result`), but NOT
 *      against a register/activate response that was still in flight
 *      for the PREVIOUSLY selected user and resolves after the switch.
 *   2. Every stored result is tagged with the user_id the request was
 *      actually made for (`result.userId`), and every render of that
 *      result is gated on `result.userId === selectedUserId` -- a
 *      stale response for user A can still finish and get stored, but
 *      it can never be displayed while user B is selected (nor can its
 *      hash be handed to Activate for the wrong user), matching the
 *      "result.userId === selectedUserId" guard.
 */
function friendlyErrorMessage(error) {
  return error?.message || "Admin Users API unavailable";
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
  // { userId, sender_e164_sha256, status } | null -- always tagged with
  // the user_id the request was made for; see the state-safety note
  // above for why every render of this must check result.userId.
  const [result, setResult] = useState(null);

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
  // may still be sitting in `result`, but it never satisfies this.
  const resultForSelectedUser = result && result.userId === selectedUserId ? result : null;

  function handleSelectUser(userId) {
    setSelectedUserId(userId);
    setPhoneInput("");
    setResult(null);
    setActionError(null);
    setValidationError(null);
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
      const response = await registerWhatsAppNumber(requestUserId, { phoneNumber });
      // Tagged with the user this request was actually for -- if the
      // admin has since selected a different user, resultForSelectedUser
      // above will simply never match this entry.
      setResult({ ...(response?.data ?? {}), userId: requestUserId });
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
    // Only ever acts on the CURRENTLY selected user's own result -- the
    // sender_e164_sha256 used here can never belong to a different user,
    // because resultForSelectedUser is already gated above.
    if (!resultForSelectedUser?.sender_e164_sha256) return;
    const requestUserId = selectedUserId;
    setActionError(null);
    setActivating(true);
    try {
      const response = await activateWhatsAppNumber(requestUserId, resultForSelectedUser.sender_e164_sha256);
      setResult({ ...(response?.data ?? resultForSelectedUser), userId: requestUserId });
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
        <form
          onSubmit={handleRegisterSubmit}
          data-testid="whatsapp-sender-register-form"
          style={{ marginTop: "var(--space-4)" }}
        >
          <div>
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
                <span data-testid="whatsapp-sender-scope">
                  Not exposed by the current Admin Users API
                </span>{" "}
                (read-only)
              </p>
            </div>
          )}

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
      )}

      {selectedUser && (
        <div data-testid="whatsapp-sender-status-card" style={{ marginTop: "var(--space-4)" }}>
          {resultForSelectedUser ? (
            <>
              <p>
                Identifier: <span data-testid="whatsapp-sender-redacted-id">REDACTED</span>
              </p>
              <p>
                Status:{" "}
                <Badge variant={resultForSelectedUser.status === "ACTIVE" ? "success" : "warning"}>
                  {resultForSelectedUser.status ?? "—"}
                </Badge>
              </p>
              {resultForSelectedUser.status !== "ACTIVE" && (
                <Button onClick={handleActivate} disabled={activating}>
                  {activating ? "Activating…" : "Activate Number"}
                </Button>
              )}
            </>
          ) : (
            // Honest neutral state -- there is no backend lookup to ask
            // "is this user already registered/active", so this never
            // claims NOT_REGISTERED, and it is re-shown every time the
            // selected user changes (never carries a previous user's
            // result across a switch, see resultForSelectedUser above).
            <p className="confidence-label" data-testid="whatsapp-sender-status-neutral">
              Status not loaded for this user.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
