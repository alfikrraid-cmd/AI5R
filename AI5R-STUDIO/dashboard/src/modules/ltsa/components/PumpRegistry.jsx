import { useState } from "react";

import Panel from "./Panel";
import StatusBadge from "./StatusBadge";

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
    {
        tag: "P-103",
        type: "Horizontal Split Case",
        manufacturer: "Sulzer",
        seal: "MS-003",
        status: "STANDBY",
    },
];

export default function PumpRegistry() {
    const [selectedPump] = useState(pumps[0]);

    return (
        <div>

            {/* HEADER */}

            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 24,
                }}
            >
                <div>

                    <h1
                        style={{
                            margin: 0,
                        }}
                    >
                        Pump Registry
                    </h1>

                    <p
                        style={{
                            marginTop: 8,
                            color: "#94A3B8",
                        }}
                    >
                        LTSA Engineering Assets
                    </p>

                </div>

                <StatusBadge status="ONLINE" />

            </div>

            {/* WORKSPACE */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 380px",
                    gap: 20,
                }}
            >

                {/* LEFT */}

                <Panel title="Pump List">

                    <table
                        style={{
                            width: "100%",
                            borderCollapse: "collapse",
                        }}
                    >

                        <thead>

                            <tr>

                                <th align="left">Tag</th>

                                <th align="left">Type</th>

                                <th align="left">Manufacturer</th>

                                <th align="left">Seal</th>

                                <th align="left">Status</th>

                            </tr>

                        </thead>

                        <tbody>

                            {pumps.map((pump) => (

                                <tr
                                    key={pump.tag}
                                    style={{
                                        cursor: "pointer",
                                        borderTop: "1px solid #1F2937",
                                    }}
                                >

                                    <td
                                        style={{
                                            padding: "12px 8px",
                                        }}
                                    >
                                        {pump.tag}
                                    </td>

                                    <td>{pump.type}</td>

                                    <td>{pump.manufacturer}</td>

                                    <td>{pump.seal}</td>

                                    <td>{pump.status}</td>

                                </tr>

                            ))}

                        </tbody>

                    </table>

                </Panel>

                {/* RIGHT */}

                <Panel title="Pump Detail">

                    <div
                        style={{
                            display: "grid",
                            gap: 14,
                        }}
                    >

                        <div>

                            <strong>Tag</strong>

                            <div>{selectedPump.tag}</div>

                        </div>

                        <div>

                            <strong>Type</strong>

                            <div>{selectedPump.type}</div>

                        </div>

                        <div>

                            <strong>Manufacturer</strong>

                            <div>{selectedPump.manufacturer}</div>

                        </div>

                        <div>

                            <strong>Seal</strong>

                            <div>{selectedPump.seal}</div>

                        </div>

                        <div>

                            <strong>Status</strong>

                            <div>{selectedPump.status}</div>

                        </div>

                    </div>

                </Panel>

            </div>

        </div>
    );
}