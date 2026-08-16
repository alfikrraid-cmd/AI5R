import OrganizationContext from "../../../platform/OrganizationContext";
import { ROLES } from "./permissions";

// Frontend-first auth client (MWO-LTSA-AUTH-OPEN-DESIGN-001). Mirrors the
// AUTH-001 contract's intended endpoints:
//   POST /api/auth/login  -> { user, organization, role, permissions, token }
//   GET  /api/auth/me     -> same session shape
//
// AUTH-001A (backend) does not exist yet, so this module is a demo
// implementation of that exact contract shape. When the real endpoints
// land, only this file's two exported functions need new bodies -- every
// consumer (AuthContext) already talks to the contract, not to demo data.
// Demo-only: never a production security bypass, isolated to this module.

const TAP = new OrganizationContext({
  organizationId: "org-tap",
  slug: "tap",
  displayName: "TAP",
});

const PERTAMINA_RU2 = new OrganizationContext({
  organizationId: "org-pertamina-ru2",
  slug: "pertamina-ru2",
  displayName: "Pertamina RU II",
});

const DEMO_USERS = [
  {
    email: "admin@tap.co.id",
    password: "demo123",
    status: "active",
    user: { userId: "u-tap-admin", name: "Andra Wicaksono" },
    organization: TAP,
    role: ROLES.TAP_ADMIN,
  },
  {
    email: "engineer@tap.co.id",
    password: "demo123",
    status: "active",
    user: { userId: "u-tap-engineer", name: "Rizal Pratama" },
    organization: TAP,
    role: ROLES.TAP_ENGINEER,
  },
  {
    email: "budi.santoso@pertamina.com",
    password: "demo123",
    status: "active",
    user: { userId: "u-pertamina-engineer", name: "Budi Santoso" },
    organization: PERTAMINA_RU2,
    role: ROLES.PERTAMINA_ENGINEER,
  },
  {
    email: "viewer@pertamina.com",
    password: "demo123",
    status: "inactive",
    user: { userId: "u-pertamina-viewer", name: "Siti Rahayu" },
    organization: PERTAMINA_RU2,
    role: ROLES.PERTAMINA_VIEWER,
  },
];

const SESSION_KEY = "ai5r.ltsa.session";
const LATENCY_MS = 420;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toSession(record) {
  return {
    user: record.user,
    organization: {
      organizationId: record.organization.organizationId,
      slug: record.organization.slug,
      displayName: record.organization.displayName,
    },
    role: record.role,
    token: `demo.${record.user.userId}`,
  };
}

// AUTH_UNAVAILABLE is a demo-only escape hatch (never triggered by real
// input) so the "server unavailable" state is reachable for design/QA
// without needing a real backend outage.
export async function login({ email, password }) {
  await delay(LATENCY_MS);

  if (String(email).trim().toLowerCase() === "unavailable@demo") {
    const error = new Error("server_unavailable");
    error.code = "server_unavailable";
    throw error;
  }

  const record = DEMO_USERS.find((candidate) => candidate.email.toLowerCase() === String(email).trim().toLowerCase());

  if (!record || record.password !== password) {
    const error = new Error("invalid_credentials");
    error.code = "invalid_credentials";
    throw error;
  }

  if (record.status !== "active") {
    const error = new Error("inactive_account");
    error.code = "inactive_account";
    throw error;
  }

  const session = toSession(record);
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export async function getSession() {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function logout() {
  window.localStorage.removeItem(SESSION_KEY);
}
