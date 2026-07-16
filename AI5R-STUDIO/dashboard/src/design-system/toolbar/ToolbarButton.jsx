export default function ToolbarButton({
    icon,
    label,
    onClick,
    disabled = false,
    active = false,
    title,
}) {
    return (
        <button
            type="button"
            title={title}
            disabled={disabled}
            onClick={onClick}
            style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: label ? "6px 12px" : "6px",
                background: active ? "#2563EB" : "transparent",
                border: "none",
                borderRadius: 8,
                color: disabled
                    ? "#475569"
                    : active
                        ? "#FFFFFF"
                        : "#CBD5E1",
                cursor: disabled ? "default" : "pointer",
                fontSize: 13,
                fontWeight: 500,
                opacity: disabled ? 0.6 : 1,
            }}
        >
            {icon}
            {label && <span>{label}</span>}
        </button>
    );
}
