export default function Workspace({ children }) {
    return (
        <main
            style={{
                flex: 1,
                background: "#0B1020",
                padding: 24,
                overflow: "auto",
                minHeight: "calc(100vh - 64px)",
                boxSizing: "border-box",
            }}
        >
            {children}
        </main>
    );
}