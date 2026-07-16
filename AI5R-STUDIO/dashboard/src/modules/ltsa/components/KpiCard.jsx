import ProgressBar from "./ProgressBar";

export default function KpiCard({
    title,
    value,
    subtitle = "",
    color = "#22C55E",
    progress,
    max,
}) {
    return (
        <div
            style={{
                background: "#111827",
                border: "1px solid #1F2937",
                borderLeft: `5px solid ${color}`,
                borderRadius: 14,
                padding: 20,
            }}
        >
            <div
                style={{
                    color: "#94A3B8",
                    fontSize: 13,
                    letterSpacing: 1,
                    textTransform: "uppercase",
                }}
            >
                {title}
            </div>

            <div
                style={{
                    fontSize: 34,
                    fontWeight: 700,
                    marginTop: 14,
                }}
            >
                {value}
            </div>

            <div
                style={{
                    marginTop: 10,
                    color: "#94A3B8",
                    fontSize: 13,
                }}
            >
                {subtitle}
            </div>

            {progress !== undefined && (
                <ProgressBar
                    value={progress}
                    max={max}
                    color={color}
                />
            )}
        </div>
    );
}