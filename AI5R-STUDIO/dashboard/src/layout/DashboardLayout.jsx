export default function DashboardLayout({ children }) {
  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "Arial" }}>
      <aside style={{
        width: "260px",
        background: "#0b1220",
        color: "white",
        padding: "20px"
      }}>
        <h2>AI5R STUDIO</h2>
        <p>Control Tower</p>
      </aside>

      <main style={{ flex: 1, background: "#f5f6fa", padding: "20px" }}>
        {children}
      </main>
    </div>
  );
}

