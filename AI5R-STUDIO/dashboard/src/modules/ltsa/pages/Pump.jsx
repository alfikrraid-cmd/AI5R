export default function Pump() {

    const pumps = [
        {
            tag: "P-101",
            type: "Centrifugal",
            manufacturer: "KSB",
            seal: "MS-001",
            status: "ACTIVE",
        },
        {
            tag: "P-102",
            type: "Vertical",
            manufacturer: "Flowserve",
            seal: "MS-002",
            status: "ACTIVE",
        },
    ];

    return (
        <div>

            <h1>Pump Registry</h1>

            <table
                style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    marginTop: 20,
                }}
            >
                <thead>
                    <tr>
                        <th>Tag</th>
                        <th>Type</th>
                        <th>Manufacturer</th>
                        <th>Seal</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                    {pumps.map((pump) => (
                        <tr key={pump.tag}>
                            <td>{pump.tag}</td>
                            <td>{pump.type}</td>
                            <td>{pump.manufacturer}</td>
                            <td>{pump.seal}</td>
                            <td>{pump.status}</td>
                        </tr>
                    ))}
                </tbody>

            </table>

        </div>
    );
}