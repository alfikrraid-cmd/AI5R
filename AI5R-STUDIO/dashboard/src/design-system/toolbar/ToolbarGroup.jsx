export default function ToolbarGroup({ children }) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
            }}
        >
            {children}
        </div>
    );
}
