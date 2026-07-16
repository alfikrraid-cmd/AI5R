export default function ContextMenu({ items = [], position, onClose }) {
    const top = position?.y ?? 0;
    const left = position?.x ?? 0;

    return (
        <div
            style={{
                position: "absolute",
                top,
                left,
                pointerEvents: "auto",
                minWidth: 180,
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderRadius: 10,
                boxShadow: "0 12px 30px rgba(0,0,0,.4)",
                padding: 6,
            }}
        >
            {items.map((item, index) => (
                <button
                    key={item.key ?? index}
                    type="button"
                    disabled={item.disabled}
                    onClick={() => {
                        item.onSelect?.();
                        onClose?.();
                    }}
                    style={{
                        display: "block",
                        width: "100%",
                        textAlign: "left",
                        background: "transparent",
                        border: "none",
                        borderRadius: 6,
                        padding: "8px 12px",
                        fontSize: 13,
                        color: item.disabled ? "#475569" : "#F1F5F9",
                        cursor: item.disabled ? "default" : "pointer",
                    }}
                >
                    {item.label}
                </button>
            ))}
        </div>
    );
}
