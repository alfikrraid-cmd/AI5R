/**
 * MWO-LTSA-TAP-GROUP-AGENT-001 -- thin HTTP client to the backend's
 * internal, ingress-secret-gated Group Agent endpoint. No retry/business
 * logic here: a network failure surfaces as a rejected promise, and
 * index.js's own caller decides what (if anything) to reply -- this
 * module never fabricates an "unavailable" reply itself, so there is
 * exactly one place (the backend, or index.js's own catch) that owns
 * user-facing failure text.
 */

export function createGroupAgentClient({ baseUrl, ingressSecret, fetchImpl = fetch }) {
  if (!baseUrl) throw new Error("createGroupAgentClient requires baseUrl");
  if (!ingressSecret) throw new Error("createGroupAgentClient requires ingressSecret");

  return {
    async sendGroupMessage(event) {
      const response = await fetchImpl(`${baseUrl.replace(/\/$/, "")}/api/ltsa/whatsapp-group/message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-ai5r-whatsapp-group-ingress-secret": ingressSecret,
        },
        body: JSON.stringify(event),
      });
      if (!response.ok) {
        throw new Error(`group agent backend returned HTTP ${response.status}`);
      }
      return response.json();
    },
  };
}
