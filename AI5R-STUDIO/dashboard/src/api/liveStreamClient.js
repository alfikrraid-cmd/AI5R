export function createLiveStreamClient({
  endpoint = "/api/studio/events/stream",
  onEvent,
  onError,
} = {}) {
  if (typeof EventSource === "undefined") {
    throw new Error("EventSource is not available in this environment");
  }

  const source = new EventSource(endpoint);

  source.onmessage = (message) => {
    try {
      const payload = JSON.parse(message.data);

      if (onEvent) {
        onEvent(payload);
      }
    } catch (error) {
      if (onError) {
        onError(error);
      }
    }
  };

  source.onerror = (error) => {
    if (onError) {
      onError(error);
    }
  };

  return {
    close() {
      source.close();
    },
  };
}
