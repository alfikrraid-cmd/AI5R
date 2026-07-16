import KpiCard from "../components/KpiCard";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import RuntimeMetricCard from "../components/RuntimeMetricCard";
import QueueTable from "../components/QueueTable";
import ActivityTimeline from "../components/ActivityTimeline";
import SimpleChart from "../components/SimpleChart";

export default function Dashboard() {
    return (
        <div
            style={{
                background: "#0B1020",
                minHeight: "100vh",
                color: "white",
                padding: 40,
            }}
        >
            {/* HEADER */}

            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 30,
                }}
            >
                <div>
                    <h1
                        style={{
                            margin: 0,
                        }}
                    >
                        LTSA Engineering Dashboard
                    </h1>

                    <p
                        style={{
                            marginTop: 8,
                            color: "#94A3B8",
                        }}
                    >
                        Engineering Digital Factory
                    </p>
                </div>

                <StatusBadge status="ONLINE" />
            </div>

            {/* KPI */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(5,1fr)",
                    gap: 20,
                    marginBottom: 30,
                }}
            >
                <KpiCard
                    title="Factory Runtime"
                    value="ONLINE"
                    subtitle="Healthy"
                    color="#22C55E"
                />

                <KpiCard
                    title="Factory Packs"
                    value="3 / 5"
                    subtitle="Pump • Seal • Maintenance"
                    color="#3B82F6"
                    progress={3}
                    max={5}
                />

                <KpiCard
                    title="Queue"
                    value="0"
                    subtitle="Idle"
                    color="#F59E0B"
                />

                <KpiCard
                    title="Tests"
                    value="203"
                    subtitle="PASS"
                    color="#22C55E"
                />

                <KpiCard
                    title="Knowledge"
                    value="932"
                    subtitle="Engineering Objects"
                    color="#8B5CF6"
                />
            </div>

            {/* ROW 1 */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 20,
                    marginBottom: 20,
                }}
            >
                <Panel title="Runtime Metrics">
                    <div
                        style={{
                            display: "grid",
                            gap: 12,
                        }}
                    >
                        <RuntimeMetricCard
                            title="CPU"
                            value="18%"
                        />

                        <RuntimeMetricCard
                            title="Memory"
                            value="41%"
                            color="#3B82F6"
                        />

                        <RuntimeMetricCard
                            title="Workers"
                            value="8 / 8"
                            color="#F59E0B"
                        />

                        <RuntimeMetricCard
                            title="Latency"
                            value="42 ms"
                            color="#8B5CF6"
                        />
                    </div>
                </Panel>

                <Panel title="Manufacturing Queue">
                    <QueueTable />
                </Panel>
            </div>

            {/* ROW 2 */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 20,
                    marginBottom: 20,
                }}
            >
                <Panel title="Runtime Activity">
                    <ActivityTimeline />
                </Panel>

                <Panel title="Manufacturing Trend">
                    <SimpleChart />
                </Panel>
            </div>

            {/* ROW 3 */}

            <Panel title="Engineering Knowledge Graph">
                <div
                    style={{
                        height: 260,
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        color: "#94A3B8",
                        border: "1px dashed #374151",
                        borderRadius: 12,
                    }}
                >
                    React Flow Knowledge Graph
                </div>
            </Panel>

            {/* ROW 4 */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 20,
                    marginTop: 20,
                }}
            >
                <Panel title="AI Recommendation">
                    <div
                        style={{
                            lineHeight: 2,
                        }}
                    >
                        <strong>Pump P-101</strong>

                        <br />

                        Mechanical Seal should be replaced.

                        <br />

                        Confidence : <strong>98%</strong>
                    </div>
                </Panel>

                <Panel title="Recent Manufacturing">
                    <div
                        style={{
                            lineHeight: 2,
                        }}
                    >
                        ✔ Pump Manufactured

                        <br />

                        ✔ Seal Relationship Created

                        <br />

                        ✔ Knowledge Updated
                    </div>
                </Panel>
            </div>
        </div>
    );
}