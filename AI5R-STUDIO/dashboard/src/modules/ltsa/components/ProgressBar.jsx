export default function ProgressBar({
    value,
    max,
    color = "#3B82F6",
}) {
    const percent = (value / max) * 100;

    return (
        <div
            style={{
                marginTop: 10,
            }}
        >
            <div
                style={{
                    width: "100%",
                    height: 10,
                    background: "#1F2937",
                    borderRadius: 99,
                    overflow: "hidden",
                }}
            >
                <div
                    style={{
                        width: `${percent}%`,
                        height: "100%",
                        background: color,
                    }}
                />
            </div>
        </div>
    );
}