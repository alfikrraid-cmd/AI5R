import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { onUnauthorized } from "../../../api/ai5rClient";
import * as authClient from "./authClient";

const AuthContext = createContext(null);

// status: "checking" | "unauthenticated" | "authenticating" | "authenticated"
// error: null | "invalid_credentials" | "inactive_account" | "server_unavailable"
export function AuthProvider({ children, client = authClient }) {
  const [status, setStatus] = useState("checking");
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    client.getSession().then((existing) => {
      if (cancelled) return;
      if (existing) {
        setSession(existing);
        setStatus("authenticated");
      } else {
        setStatus("unauthenticated");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [client]);

  const login = useCallback(
    async (email, password) => {
      setStatus("authenticating");
      setError(null);
      try {
        const nextSession = await client.login({ email, password });
        setSession(nextSession);
        setStatus("authenticated");
        return nextSession;
      } catch (err) {
        setStatus("unauthenticated");
        setError(err?.code ?? "invalid_credentials");
        throw err;
      }
    },
    [client]
  );

  const logout = useCallback(() => {
    client.logout();
    setSession(null);
    setStatus("unauthenticated");
    setError(null);
  }, [client]);

  // MWO-LTSA-AUTH-002 Rule 6 -- a 401 from ANY protected LTSA request (not
  // just /api/auth/me) must clear the session and return to LoginView.
  // ai5rClient.js's apiFetch() already clears the stored session on 401;
  // this registers the matching React-state clear so the UI actually
  // reflects it, without ai5rClient depending on React.
  useEffect(() => {
    onUnauthorized(() => {
      setSession(null);
      setStatus("unauthenticated");
      setError(null);
    });
  }, []);

  const value = useMemo(
    () => ({ status, session, error, login, logout }),
    [status, session, error, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
