import { useState } from "react";
import { Badge, Button, EmptyState, PageHeader } from "../../../design-system";
import { activateWhatsAppGroup, registerWhatsAppGroup } from "../../../api/ai5rClient";
import WhatsAppSenderAccessView from "./WhatsAppSenderAccessView";
import "./LTSAOpenDesign.css";

/**
 * AI5R-WHATSAPP-GROUP-ADMIN-001 -- LTSA Admin -> WhatsApp Groups.
 *
 * Minimal register -> activate lifecycle UI over the existing
 * routers/whatsapp_group_agent_admin.py endpoints (admin.users-gated,
 * same permission AdminUsersView already uses). Reachable only via the
 * "whatsapp-groups" tab, which permissions.js's TAB_PERMISSIONS +
 * visibleTabKeys() already hide from any session without admin.users --
 * the same trust model every other LTSA tab already relies on (no tab's
 * page component repeats its own redundant gate); the backend remains
 * the authoritative enforcement point regardless.
 *
 * The raw WhatsApp group JID is never persisted by this component: it
 * lives only in local React state while the owner is typing it, is sent
 * once in the register request body, and is cleared from state
 * immediately after that request settles (success or failure alike). It
 * is never written to localStorage/sessionStorage, never logged (no
 * console.* call in this file touches it), and the backend's own
 * register/activate response projection never echoes it back either --
 * so there is nothing left here to redact after submission.
 */
const GROUP_JID_PATTERN = /^\d+@g\.us$/;

function friendlyErrorMessage(error) {
  if (error?.status === 403) {
    return "You do not have permission to manage WhatsApp groups.";
  }
  return error?.message || "WhatsApp Group Admin API unavailable";
}

function truncateHash(hash) {
  if (typeof hash !== "string" || hash.length === 0) return "—";
  return hash.length > 12 ? `${hash.slice(0, 12)}…` : hash;
}

export default function WhatsAppGroupsView() {
  const [groupIdInput, setGroupIdInput] = useState("");
  const [displayLabelInput, setDisplayLabelInput] = useState("");
  const [validationError, setValidationError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [registered, setRegistered] = useState(null);
  const [activating, setActivating] = useState(false);

  async function handleRegisterSubmit(event) {
    event.preventDefault();
    const groupId = groupIdInput.trim();
    const displayLabel = displayLabelInput.trim();
    setValidationError(null);
    setActionError(null);

    if (!groupId) {
      setValidationError("Group JID is required.");
      return;
    }
    if (!displayLabel) {
      setValidationError("Display Label is required.");
      return;
    }
    if (!GROUP_JID_PATTERN.test(groupId)) {
      setValidationError('Group JID must be a numeric WhatsApp group id ending in "@g.us".');
      return;
    }

    setSubmitting(true);
    try {
      const response = await registerWhatsAppGroup({ groupId, displayLabel });
      setRegistered(response?.data ?? null);
    } catch (error) {
      setActionError(friendlyErrorMessage(error));
    } finally {
      // Cleared whether the request succeeded or failed -- this
      // component never keeps the raw JID around past one submit.
      setGroupIdInput("");
      setSubmitting(false);
    }
  }

  async function handleActivate() {
    if (!registered?.group_hash) return;
    setActionError(null);
    setActivating(true);
    try {
      const response = await activateWhatsAppGroup({ groupHash: registered.group_hash });
      setRegistered(response?.data ?? registered);
    } catch (error) {
      setActionError(friendlyErrorMessage(error));
    } finally {
      setActivating(false);
    }
  }

  return (
    <div className="ltsa-open-design" data-testid="whatsapp-groups-view">
      <PageHeader title="WhatsApp Groups" subtitle="LTSA Admin — WhatsApp group authorization" />

      <h2 style={{ margin: 0 }}>Group Authorization</h2>

      {actionError && (
        <p
          className="confidence-label"
          style={{ color: "var(--color-danger, #d33)" }}
          data-testid="whatsapp-groups-action-error"
        >
          {actionError}
        </p>
      )}

      <form
        onSubmit={handleRegisterSubmit}
        data-testid="whatsapp-groups-register-form"
        style={{ marginBottom: "var(--space-4)" }}
      >
        <div>
          <label htmlFor="whatsapp-group-jid">Group JID</label>
          <input
            id="whatsapp-group-jid"
            aria-label="Group JID"
            placeholder="120363xxxxxxxxxx@g.us"
            value={groupIdInput}
            onChange={(e) => setGroupIdInput(e.target.value)}
            autoComplete="off"
          />
        </div>
        <div>
          <label htmlFor="whatsapp-group-label">Display Label</label>
          <input
            id="whatsapp-group-label"
            aria-label="Display Label"
            placeholder="AI5R LTSA WhatsApp Group"
            value={displayLabelInput}
            onChange={(e) => setDisplayLabelInput(e.target.value)}
          />
        </div>
        {validationError && (
          <p
            className="confidence-label"
            style={{ color: "var(--color-danger, #d33)" }}
            data-testid="whatsapp-groups-validation-error"
          >
            {validationError}
          </p>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Registering…" : "Register Group"}
        </Button>
      </form>

      {registered && (
        <div data-testid="whatsapp-groups-registered-summary">
          <p>Display Label: {registered.display_label ?? "—"}</p>
          <p>
            Group Identifier: <span data-testid="whatsapp-groups-redacted-id">REDACTED</span>
          </p>
          <p>Group Hash: {truncateHash(registered.group_hash)}</p>
          <p>
            Status:{" "}
            <Badge variant={registered.status === "ACTIVE" ? "success" : "warning"}>
              {registered.status ?? "—"}
            </Badge>
          </p>
          {registered.status !== "ACTIVE" && (
            <Button onClick={handleActivate} disabled={activating}>
              {activating ? "Activating…" : "Activate Group"}
            </Button>
          )}
        </div>
      )}

      {!registered && (
        <EmptyState
          title="No group registered yet in this session"
          description="Paste the group's WhatsApp JID and a display label above, then Register."
        />
      )}

      <WhatsAppSenderAccessView />
    </div>
  );
}
