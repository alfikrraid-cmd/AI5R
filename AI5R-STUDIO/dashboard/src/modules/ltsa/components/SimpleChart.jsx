import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    Tooltip,
} from "recharts";

const data = [
    { name: "Mon", value: 12 },
    { name: "Tue", value: 18 },
    { name: "Wed", value: 24 },
    { name: "Thu", value: 21 },
    { name: "Fri", value: 31 },
    { name: "Sat", value: 26 },
    { name: "Sun", value: 38 },
];

export default function SimpleChart() {
    return (
        <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
                <AreaChart data={data}>
                    <XAxis
                        dataKey="name"
                        stroke="#94A3B8"
                    />

                    <Tooltip />

                    <Area
                        dataKey="value"
                        stroke="#22C55E"
                        fill="#22C55E"
                        fillOpacity={0.2}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}