export default function Popover({ content, anchorRect, placement = "bottom" }) {
    const top =
        placement === "top"
            ? (anchorRect?.top ?? 0) - 8
            : (anchorRect?.top ?? 0) + (anchorRect?.height ?? 0) + 8;

    const left = anchorRect?.left ?? 0;

    return (
        <div
            style={{
                position: "absolute",
                top,
                left,
                transform: placement === "top" ? "translateY(-100%)" : undefined,
                pointerEvents: "auto",
                minWidth: 200,
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderRadius: 10,
                boxShadow: "0 12px 30px rgba(0,0,0,.4)",
                padding: 12,
                color: "#F1F5F9",
                fontSize: 13,
            }}
        >
            {content}
        </div>
    );
}
