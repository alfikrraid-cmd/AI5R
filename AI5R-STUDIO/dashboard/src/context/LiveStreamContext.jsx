import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

const LiveStreamContext = createContext({
  events: [],
  status: "CONNECTING",
});

export function LiveStreamProvider({ children }) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("CONNECTING");
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const originalPushState = window.history.pushState;
    const originalReplaceState = window.history.replaceState;
    const notifyPathChange = () => setPathname(window.location.pathname);
    window.history.pushState = function pushState(...args) {
      const result = originalPushState.apply(this, args);
      notifyPathChange();
      return result;
    };
    window.history.replaceState = function replaceState(...args) {
      const result = originalReplaceState.apply(this, args);
      notifyPathChange();
      return result;
    };
    window.addEventListener("popstate", notifyPathChange);
    let client;

    if (pathname.startsWith("/ltsa")) {
      setStatus("UNAVAILABLE");
      return () => {
        window.history.pushState = originalPushState;
        window.history.replaceState = originalReplaceState;
        window.removeEventListener("popstate", notifyPathChange);
      };
    }

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          setStatus("LIVE");
          setEvents((current) => [event, ...current].slice(0, 100));
        },
        onError: () => {
          setStatus("RECONNECTING");
        },
      });
    } catch {
      setStatus("UNAVAILABLE");
    }

    return () => {
      client?.close();
      window.history.pushState = originalPushState;
      window.history.replaceState = originalReplaceState;
      window.removeEventListener("popstate", notifyPathChange);
    };
  }, [pathname]);

  const value = useMemo(
    () => ({
      events,
      status,
    }),
    [events, status]
  );

  return (
    <LiveStreamContext.Provider value={value}>
      {children}
    </LiveStreamContext.Provider>
  );
}

export function useLiveStream() {
  return useContext(LiveStreamContext);
}
