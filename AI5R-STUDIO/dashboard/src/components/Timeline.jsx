export default function Timeline({ events }) {
  return (
    <div style={{ marginTop: 40 }}>
      <h2>Organization Timeline</h2>

      {events.map((event, index) => (
        <div
          key={index}
          style={{
            borderLeft: "3px solid #4f46e5",
            paddingLeft: 20,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontWeight: 700,
              color: "#4f46e5",
            }}
          >
            {event.time}
          </div>

          <div>{event.message}</div>
        </div>
      ))}
    </div>
  );
}
