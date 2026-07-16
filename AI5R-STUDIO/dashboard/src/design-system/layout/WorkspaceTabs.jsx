export default function WorkspaceTabs() {
    return (
        <div
            style={{
                height: 60,
                background: "red",
                color: "white",
                display: "flex",
                alignItems: "center",
                gap: 20,
                padding: "0 20px",
                fontWeight: "bold",
                fontSize: 18,
            }}
        >
            <div>DASHBOARD</div>
            <div>PUMP</div>
            <div>SEAL</div>
            <div>+</div>
        </div>
    );
}