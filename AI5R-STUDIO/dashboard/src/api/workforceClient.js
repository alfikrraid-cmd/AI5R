const API_URL = import.meta.env?.VITE_API_URL || "http://localhost:18000";
const SESSION_KEY = "ai5r.ltsa.session";

function getHeaders(extraHeaders = {}) {
  const headers = {
    Accept: "application/json",
    ...extraHeaders,
  };

  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const raw = window.localStorage.getItem(SESSION_KEY);
      if (raw) {
        const session = JSON.parse(raw);
        if (session?.token) {
          headers.Authorization = `Bearer ${session.token}`;
        }
      }
    }
  } catch {
    // Fallback safely if localStorage is unavailable
  }

  return headers;
}

async function handleResponse(response, contextMessage) {
  if (!response.ok) {
    let errorDetail = "";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || "";
    } catch {
      // Ignore json parse error on non-json error responses
    }
    throw new Error(
      `${contextMessage}: ${response.status}${errorDetail ? ` - ${errorDetail}` : ""}`
    );
  }
  return await response.json();
}

/**
 * Fetch all digital employees in the workforce.
 */
export async function fetchWorkforceEmployees({ signal } = {}) {
  const response = await fetch(`${API_URL}/api/workforce/employees`, {
    headers: getHeaders(),
    signal,
  });
  return handleResponse(response, "Failed to fetch workforce employees");
}

/**
 * Fetch detailed profile and recent activities for a single digital employee.
 */
export async function fetchWorkforceEmployee(employeeId, { signal } = {}) {
  if (!employeeId) {
    throw new Error("employeeId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/employees/${encodeURIComponent(employeeId)}`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch employee ${employeeId}`);
}

/**
 * Fetch the current state of the workforce board (published, claimed, completed, released).
 */
export async function fetchWorkforceBoard({ signal } = {}) {
  const response = await fetch(`${API_URL}/api/workforce/board`, {
    headers: getHeaders(),
    signal,
  });
  return handleResponse(response, "Failed to fetch workforce board");
}

/**
 * Fetch the workforce activity feed.
 */
export async function fetchWorkforceActivities({ limit = 50, employeeId, signal } = {}) {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (employeeId) params.set("employee_id", employeeId);

  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_URL}/api/workforce/activities${query}`, {
    headers: getHeaders(),
    signal,
  });
  return handleResponse(response, "Failed to fetch workforce activities");
}

/**
 * Fetch workforce operational, uptime, and capacity metrics.
 */
export async function fetchWorkforceMetrics({ signal } = {}) {
  const response = await fetch(`${API_URL}/api/workforce/metrics`, {
    headers: getHeaders(),
    signal,
  });
  return handleResponse(response, "Failed to fetch workforce metrics");
}

