const activities = [
    {
        time: "09:25",
        text: "Pump Manufactured",
        color: "#22C55E",
    },
    {
        time: "09:23",
        text: "Seal Relationship Created",
        color: "#3B82F6",
    },
    {
        time: "09:21",
        text: "Maintenance Imported",
        color: "#F59E0B",
    },
    {
        time: "09:18",
        text: "Knowledge Updated",
        color: "#8B5CF6",
    },
];

export default function ActivityTimeline() {
    return (
        <div>
            {activities.map((item) => (
                <div
                    key={`${item.time}-${item.text}`}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "12px 0",
                        borderBottom: "1px solid #1F2937",
                    }}
                >
                    <div
                        style={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            background: item.color,
                            flexShrink: 0,
                        }}
                    />

                    <div style={{ minWidth: 60, color: "#94A3B8" }}>
                        {item.time}
                    </div>

                    <div>{item.text}</div>
                </div>
            ))}
        </div>
    );
}