import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

const LiveStreamContext = createContext({
  events: [],
  status: "CONNECTING",
});

export function LiveStreamProvider({ children }) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("CONNECTING");

  useEffect(() => {
    let client;

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

    return () => client?.close();
  }, []);

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
