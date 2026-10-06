import { clearStoredSession, getStoredSession, storeSession } from "../../../api/ai5rClient";

// MWO-LTSA-AUTH-002 -- real AUTH-001 backend integration, replacing the
// MWO-LTSA-AUTH-OPEN-DESIGN-001 demo implementation this module used to
// contain. Same exported contract (login/getSession/logout) that
// AuthContext.jsx already talks to, so AuthContext itself needed no
// changes -- only this module's bodies changed, exactly as that MWO's own
// header comment anticipated.
//
// Talks to the real, exact AUTH-001 contract (CORE-SERVICES/BACKEND-API/
// routers/auth.py):
//   POST /api/auth/login {email, password}
//     -> {access_token, token_type, user:{id,email}, organization:{id,code},
//         role, permissions}
//   GET  /api/auth/me (Authorization: Bearer <token>)
//     -> {user:{id,email}, organization:{id,code}, role, permissions}
//
// The backend's users table (migration 007) has no display-name column --
// email or username can be the real identity string; username is preferred for display when present, with email preserved for legacy users
// where the frozen IdentityBar renders session.user.name. Likewise
// organization.displayName is the backend's own `code` (e.g. "TAP",
// "PERTAMINA_RU_II") verbatim -- never a hardcoded TAP/Pertamina RU II
// table here (Rule 8).
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18000";

function toSession(identityPayload, token) {
  const user = identityPayload.user || {};
  const org = identityPayload.organization || {};
  const email = identityPayload.email ?? user.email ?? null;
  const username = identityPayload.username ?? user.username ?? null;
  const name = identityPayload.name || user.name || username || email || "Unknown User";

  return {
    user: {
      id: identityPayload.id ?? user.id,
      email,
      username,
      name,
    },
    organization: {
      id: org.id,
      code: org.code,
      name: org.name ?? org.code,
      displayName: org.code,
    },
    role: identityPayload.role,
    permissions: identityPayload.permissions,
    data_scope_type: identityPayload.data_scope_type ?? null,
    data_scope_value: identityPayload.data_scope_value ?? null,
    token,
  };
}

function serverUnavailableError() {
  const error = new Error("server_unavailable");
  error.code = "server_unavailable";
  return error;
}

export async function login({ identifier, email, password }) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: identifier ?? email, email, password }),
    });
  } catch {
    throw serverUnavailableError();
  }

  if (response.status === 401) {
    // AUTH-001's authenticate() deliberately returns the SAME generic
    // failure for unknown user, wrong password, and disabled user (login-
    // enumeration resistance -- auth_service.py's own docstring). The
    // frontend cannot and must not try to distinguish "inactive" from
    // "wrong password" here; that would defeat the backend's own
    // protection and leak account existence. invalid_credentials is the
    // one state LoginView shows for every 401.
    const error = new Error("invalid_credentials");
    error.code = "invalid_credentials";
    throw error;
  }

  if (!response.ok) {
    throw serverUnavailableError();
  }

  const body = await response.json();
  const session = toSession(body, body.access_token);
  storeSession(session);
  return session;
}

export async function getSession() {
  const stored = getStoredSession();
  if (!stored?.token) return null;

  let response;
  try {
    response = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${stored.token}` },
    });
  } catch {
    // A network failure on reload must not be treated as "still
    // authenticated" -- fall back to LoginView rather than trusting a
    // possibly-stale local copy the backend can no longer vouch for.
    return null;
  }

  if (!response.ok) {
    // Covers expired/tampered token AND a membership disabled since the
    // token was issued (dependencies.get_current_user re-resolves live on
    // every request, never trusts the token's own claims) -- both are a
    // real 401 from the same real endpoint, so both clear the session.
    clearStoredSession();
    return null;
  }

  const body = await response.json();
  const session = toSession(body, stored.token);
  storeSession(session);
  return session;
}

export function logout() {
  clearStoredSession();
}

export async function requestPasswordReset(identifier) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier }),
    });
  } catch {
    throw serverUnavailableError();
  }

  if (response.status === 429) {
    const error = new Error("rate_limited");
    error.code = "rate_limited";
    throw error;
  }

  if (!response.ok) {
    throw serverUnavailableError();
  }

  return response.json();
}

export async function confirmPasswordReset(token, newPassword) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  } catch {
    throw serverUnavailableError();
  }

  if (response.status === 400) {
    const error = new Error("invalid_token");
    error.code = "invalid_token";
    throw error;
  }

  if (response.status === 422) {
    const error = new Error("invalid_password");
    error.code = "invalid_password";
    throw error;
  }

  if (!response.ok) {
    throw serverUnavailableError();
  }

  return response.json();
}

export async function updateProfileEmail(email) {
  const stored = getStoredSession();
  if (!stored?.token) {
    const error = new Error("unauthorized");
    error.code = "unauthorized";
    throw error;
  }

  let response;
  try {
    response = await fetch(`${API_URL}/api/auth/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${stored.token}`,
      },
      body: JSON.stringify({ email }),
    });
  } catch {
    throw serverUnavailableError();
  }

  if (response.status === 401) {
    clearStoredSession();
    const error = new Error("unauthorized");
    error.code = "unauthorized";
    throw error;
  }

  if (response.status === 409) {
    const error = new Error("email_already_in_use");
    error.code = "email_already_in_use";
    throw error;
  }

  if (response.status === 422 || response.status === 400) {
    let detail = "invalid_email";
    try {
      const errBody = await response.json();
      if (errBody?.detail) {
        detail = typeof errBody.detail === "string" ? errBody.detail : "invalid_email";
      }
    } catch {
      // ignore
    }
    const error = new Error(detail);
    error.code = "invalid_email";
    error.detail = detail;
    throw error;
  }

  if (!response.ok) {
    throw serverUnavailableError();
  }

  const body = await response.json();
  const session = toSession(body, stored.token);
  storeSession(session);
  return session;
}

