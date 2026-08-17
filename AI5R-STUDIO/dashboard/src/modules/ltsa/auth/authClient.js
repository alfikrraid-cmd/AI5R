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
// email is the only real identity string it has, so it is what's shown
// where the frozen IdentityBar renders session.user.name. Likewise
// organization.displayName is the backend's own `code` (e.g. "TAP",
// "PERTAMINA_RU_II") verbatim -- never a hardcoded TAP/Pertamina RU II
// table here (Rule 8).
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18000";

function toSession(identityPayload, token) {
  return {
    user: {
      id: identityPayload.user.id,
      email: identityPayload.user.email,
      name: identityPayload.user.email,
    },
    organization: {
      id: identityPayload.organization.id,
      code: identityPayload.organization.code,
      displayName: identityPayload.organization.code,
    },
    role: identityPayload.role,
    permissions: identityPayload.permissions,
    token,
  };
}

function serverUnavailableError() {
  const error = new Error("server_unavailable");
  error.code = "server_unavailable";
  return error;
}

export async function login({ email, password }) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
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
