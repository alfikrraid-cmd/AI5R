const API_URL = "http://localhost:8000";

export async function runOrganizationGoal(productName, goalId) {
  const response = await fetch(`${API_URL}/api/v1/organization/goal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      product_name: productName,
      goal_id: goalId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Organization API request failed: ${response.status}`);
  }

  return await response.json();
}
