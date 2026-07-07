function ExecutionStatus() {
    const modules = [
        "Brain",
        "Memory",
        "Reasoning",
        "Execution",
        "Deployment"
    ];

    return (
        <div className="card">
            <h2>Execution Status</h2>

            <div className="status-grid">
                {modules.map((module) => (
                    <div key={module} className="status-pill">
                        <span>{module}</span>
                        <strong>ACTIVE</strong>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default ExecutionStatus;
