export default function StatusBar() {
    return (
        <footer
            style={{
                height: 28,
                background: "#151C33",
                borderTop: "1px solid #2A3558",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0 16px",
                color: "#94A3B8",
                fontSize: 12,
                boxSizing: "border-box",
            }}
        >
            <div>
                AI5R Studio v1.0
            </div>

            <div
                style={{
                    display: "flex",
                    gap: 20,
                }}
            >
                <span>Runtime: 🟢 Online</span>
                <span>Workers: 8</span>
                <span>Queue: 0</span>
            </div>
        </footer>
    );
}