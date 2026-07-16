export default function Header() {
    return (
        <header
            style={{
                height: 70,
                borderBottom: "1px solid #1E293B",
                background: "#0B1020",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0 24px",
            }}
        >
            <h3>AI5R Digital Factory</h3>

            <div
                style={{
                    color: "#94A3B8",
                }}
            >
                Sandy Aguswiensyah
            </div>
        </header>
    );
}