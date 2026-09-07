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
 * alike) -- never written to localStorage/sessionStorage, never logged.
 * The backend's own register/activate responses never echo the raw
 * phone back either. The returned sender_e164_sha256 (a one-way hash,
 * not the phone itself) is kept only long enough to pass to activate,
 * and is not displayed -- shown as "REDACTED" as an extra precaution,
 * consistent with how the Group Authorization section above treats its
 * own identifier.
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
  const [registration, setRegistration] = useState(null);

  useEffect(() => {
    setUsersLoading(true);
    setUsersError(null);
    getAdminUsers()
      .then((rows) => setUsers(Array.isArray(rows) ? rows : []))
      .catch((err) => setUsersError(friendlyErrorMessage(err)))
      .finally(() => setUsersLoading(false));
  }, []);

  const selectedUser = users.find((u) => u.id === selectedUserId) ?? null;

  function handleSelectUser(userId) {
    setSelectedUserId(userId);
    setRegistration(null);
    setActionError(null);
    setValidationError(null);
  }

  async function handleRegisterSubmit(event) {
    event.preventDefault();
    const phoneNumber = phoneInput.trim();
    setValidationError(null);
    setActionError(null);

    if (!selectedUserId) {
      setValidationError("Select a user first.");
      return;
    }
    if (!phoneNumber) {
      setValidationError("WhatsApp number is required.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await registerWhatsAppNumber(selectedUserId, { phoneNumber });
      setRegistration(response?.data ?? null);
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
    if (!selectedUserId || !registration?.sender_e164_sha256) return;
    setActionError(null);
    setActivating(true);
    try {
      const response = await activateWhatsAppNumber(selectedUserId, registration.sender_e164_sha256);
      setRegistration(response?.data ?? registration);
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

      {registration && (
        <div data-testid="whatsapp-sender-registration-summary">
          <p>
            Identifier: <span data-testid="whatsapp-sender-redacted-id">REDACTED</span>
          </p>
          <p>
            Status:{" "}
            <Badge variant={registration.status === "ACTIVE" ? "success" : "warning"}>
              {registration.status ?? "—"}
            </Badge>
          </p>
          {registration.status !== "ACTIVE" && (
            <Button onClick={handleActivate} disabled={activating}>
              {activating ? "Activating…" : "Activate Number"}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
