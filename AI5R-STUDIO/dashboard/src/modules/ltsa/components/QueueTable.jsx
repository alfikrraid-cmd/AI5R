const queue = [
    {
        id: "WO-001",
        type: "Pump",
        status: "Running",
        color: "#22C55E",
    },
    {
        id: "WO-002",
        type: "Seal",
        status: "Queued",
        color: "#F59E0B",
    },
    {
        id: "WO-003",
        type: "Maintenance",
        status: "Completed",
        color: "#3B82F6",
    },
];

export default function QueueTable() {
    return (
        <table
            style={{
                width: "100%",
                borderCollapse: "collapse",
                color: "white",
            }}
        >
            <thead>
                <tr
                    style={{
                        color: "#94A3B8",
                        textAlign: "left",
                        borderBottom: "1px solid #1F2937",
                    }}
                >
                    <th style={{ padding: 12 }}>Work Order</th>
                    <th style={{ padding: 12 }}>Factory Pack</th>
                    <th style={{ padding: 12 }}>Status</th>
                </tr>
            </thead>

            <tbody>
                {queue.map((item) => (
                    <tr
                        key={item.id}
                        style={{
                            borderBottom: "1px solid #1F2937",
                        }}
                    >
                        <td style={{ padding: 12 }}>
                            {item.id}
                        </td>

                        <td style={{ padding: 12 }}>
                            {item.type}
                        </td>

                        <td style={{ padding: 12 }}>
                            <span
                                style={{
                                    background: item.color,
                                    color: "white",
                                    padding: "4px 10px",
                                    borderRadius: 20,
                                    fontSize: 12,
                                    fontWeight: 600,
                                }}
                            >
                                {item.status}
                            </span>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}