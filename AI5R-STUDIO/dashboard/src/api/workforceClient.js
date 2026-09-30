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

/**
 * Assign a new task or work item to a digital employee or position.
 */
export async function assignWorkforceTask({
  title,
  description = "",
  positionId,
  employeeId,
  isProduction = false,
  metadata = {},
  signal,
} = {}) {
  if (!title || !title.trim()) {
    throw new Error("Task title is required");
  }
  const payload = {
    title: title.trim(),
    description,
    position_id: positionId || undefined,
    employee_id: employeeId || undefined,
    is_production: Boolean(isProduction),
    metadata,
  };
  const response = await fetch(`${API_URL}/api/workforce/tasks/assign`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
    signal,
  });
  return handleResponse(response, "Failed to assign workforce task");
}

/**
 * Send an instruction/message to chat with a digital employee.
 */
export async function sendWorkforceChat({
  employeeId,
  message,
  conversationId,
  metadata = {},
  signal,
} = {}) {
  if (!employeeId) {
    throw new Error("employeeId is required");
  }
  if (!message || !message.trim()) {
    throw new Error("Message is required");
  }
  const payload = {
    employee_id: employeeId,
    message: message.trim(),
    conversation_id: conversationId || undefined,
    metadata,
  };
  const response = await fetch(`${API_URL}/api/workforce/chat`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
    signal,
  });
  return handleResponse(response, "Failed to send workforce chat");
}

/**
 * Release a completed task, enforcing the Human Chief Approval Gate for production tasks.
 */
export async function releaseWorkforceTask(
  workItemId,
  {
    approverId = "CHIEF-USER-01",
    approverRole = "CHIEF",
    isHuman = true,
    metadata = {},
    signal,
  } = {}
) {
  if (!workItemId) {
    throw new Error("workItemId is required");
  }
  const payload = {
    approver_id: approverId,
    approver_role: approverRole,
    is_human: isHuman,
    metadata,
  };
  const response = await fetch(
    `${API_URL}/api/workforce/tasks/${encodeURIComponent(workItemId)}/release`,
    {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
      signal,
    }
  );
  return handleResponse(response, `Failed to release task ${workItemId}`);
}

/**
 * Create/delegate a multi-agent engineering mission to NEXA (PROJECT_MANAGER).
 */
export async function createWorkforceMission({
  title,
  description = "",
  isProduction = false,
  metadata = {},
  signal,
} = {}) {
  if (!title || !title.trim()) {
    throw new Error("Mission title is required");
  }
  const payload = {
    title: title.trim(),
    description,
    is_production: Boolean(isProduction),
    metadata,
  };
  const response = await fetch(`${API_URL}/api/workforce/missions`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
    signal,
  });
  return handleResponse(response, "Failed to create workforce mission");
}

/**
 * Fetch all workforce missions.
 */
export async function fetchWorkforceMissions({ signal } = {}) {
  const response = await fetch(`${API_URL}/api/workforce/missions`, {
    headers: getHeaders(),
    signal,
  });
  return handleResponse(response, "Failed to fetch workforce missions");
}

/**
 * Fetch a single workforce mission by ID.
 */
export async function fetchWorkforceMission(missionId, { signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch mission ${missionId}`);
}

/**
 * Execute a claimed task through the Agent Execution Adapter (read-only analysis).
 */
export async function executeWorkforceTask(workItemId, { signal } = {}) {
  if (!workItemId) {
    throw new Error("workItemId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/tasks/${encodeURIComponent(workItemId)}/execute`,
    {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      signal,
    }
  );
  return handleResponse(response, `Failed to execute task ${workItemId}`);
}

/**
 * Fetch all execution artifacts created for a work item.
 */
export async function fetchTaskArtifacts(workItemId, { signal } = {}) {
  if (!workItemId) {
    throw new Error("workItemId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/tasks/${encodeURIComponent(workItemId)}/artifacts`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch artifacts for task ${workItemId}`);
}

/**
 * Fetch a single execution artifact by ID.
 */
export async function fetchWorkforceArtifact(artifactId, { signal } = {}) {
  if (!artifactId) {
    throw new Error("artifactId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/artifacts/${encodeURIComponent(artifactId)}`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch artifact ${artifactId}`);
}


/**
 * Trigger Level 6 autonomous orchestration of a mission.
 */
export async function orchestrateWorkforceMission(missionId, { signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/orchestrate`,
    {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      signal,
    }
  );
  return handleResponse(response, `Failed to orchestrate mission ${missionId}`);
}

/**
 * Fetch the generated plan and execution topology of a mission.
 */
export async function fetchMissionPlan(missionId, { signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/plan`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch plan for mission ${missionId}`);
}

/**
 * Fetch decomposed tasks of a mission.
 */
export async function fetchMissionTasks(missionId, { signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/tasks`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch tasks for mission ${missionId}`);
}

/**
 * Fetch structured review findings for a mission.
 */
export async function fetchMissionFindings(missionId, { signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/findings`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch findings for mission ${missionId}`);
}

/**
 * Fetch immutable ledger events for a mission.
 */
export async function fetchMissionEvents(missionId, { signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/events`,
    {
      headers: getHeaders(),
      signal,
    }
  );
  return handleResponse(response, `Failed to fetch events for mission ${missionId}`);
}

/**
 * Human Chief Approval Gate for mission completion.
 */
export async function approveWorkforceMission(
  missionId,
  {
    approverId = "raid",
    approverRole = "CHIEF_ARCHITECT",
    isHuman = true,
    metadata = {},
    signal,
  } = {}
) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const payload = {
    approver_id: approverId,
    approver_role: approverRole,
    is_human: Boolean(isHuman),
    metadata,
  };
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/approve`,
    {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
      signal,
    }
  );
  return handleResponse(response, `Failed to approve mission ${missionId}`);
}

/**
 * Human Chief rejection of mission.
 */
export async function rejectWorkforceMission(
  missionId,
  { approverId = "raid", approverRole = "CHIEF_ARCHITECT", reason = "", signal } = {}
) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const payload = {
    approver_id: approverId,
    approver_role: approverRole,
    reason,
  };
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/reject`,
    {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
      signal,
    }
  );
  return handleResponse(response, `Failed to reject mission ${missionId}`);
}

/**
 * Cancel an in-progress mission.
 */
export async function cancelWorkforceMission(missionId, { reason = "", signal } = {}) {
  if (!missionId) {
    throw new Error("missionId is required");
  }
  const payload = { reason };
  const response = await fetch(
    `${API_URL}/api/workforce/missions/${encodeURIComponent(missionId)}/cancel`,
    {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
      signal,
    }
  );
  return handleResponse(response, `Failed to cancel mission ${missionId}`);
}
