export default function PanelContainer({
    children,
    columns,
    gap = 20,
}) {
    return (
        <div
            style={{
                display: columns ? "grid" : "flex",
                flexDirection: columns ? undefined : "column",
                gridTemplateColumns: columns
                    ? `repeat(${columns}, 1fr)`
                    : undefined,
                gap,
            }}
        >
            {children}
        </div>
    );
}
