export default function Tooltip({ content, anchorRect }) {
    const top = (anchorRect?.top ?? 0) - 8;
    const left = (anchorRect?.left ?? 0) + (anchorRect?.width ?? 0) / 2;

    return (
        <div
            style={{
                position: "absolute",
                top,
                left,
                transform: "translate(-50%, -100%)",
                pointerEvents: "none",
                background: "#1E293B",
                color: "#F1F5F9",
                fontSize: 12,
                padding: "6px 10px",
                borderRadius: 6,
                whiteSpace: "nowrap",
                boxShadow: "0 8px 20px rgba(0,0,0,.35)",
            }}
        >
            {content}
        </div>
    );
}
