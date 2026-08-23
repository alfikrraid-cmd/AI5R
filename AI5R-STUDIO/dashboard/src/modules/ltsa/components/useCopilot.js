import { useCallback, useState } from "react";
import { askCopilot } from "../../../api/ai5rClient";

// MWO-AI5R-LTSA-COPILOT-001 -- thin state machine over askCopilot(), no
// business logic of its own (the backend already decides FACT vs
// DATA_GAP; this hook only maps that + transport outcomes onto the six
// UI states CopilotPanel.jsx renders: idle, loading, answer, data_gap,
// error, unauthorized). A 401 is already handled globally by
// ai5rClient's onUnauthorized hook (session cleared, redirected to
// LoginView) -- "unauthorized" here additionally covers a 403 (missing
// permission), which does not clear the session.
export default function useCopilot(assetContext) {
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const ask = useCallback(
    async (question) => {
      const trimmed = (question ?? "").trim();
      if (!trimmed) return;

      setStatus("loading");
      setErrorMessage(null);

      try {
        const payload = await askCopilot(trimmed, assetContext);
        setResult(payload);
        setStatus(payload?.kind === "DATA_GAP" ? "data_gap" : "answer");
      } catch (error) {
        setResult(null);
        setErrorMessage(error?.message ?? "Copilot is currently unavailable.");
        setStatus(error?.status === 401 || error?.status === 403 ? "unauthorized" : "error");
      }
    },
    [assetContext]
  );

  const reset = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setErrorMessage(null);
  }, []);

  return { status, result, errorMessage, ask, reset };
}
