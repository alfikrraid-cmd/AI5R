import { Card, StatusBadge } from "../design-system";

function ExecutionStatus() {
    const modules = [
        "Brain",
        "Memory",
        "Reasoning",
        "Execution",
        "Deployment"
    ];

    return (
        <Card title="Execution Status">
            <div className="status-grid">
                {modules.map((module) => (
                    <StatusBadge key={module} label={module} status="ACTIVE" />
                ))}
            </div>
        </Card>
    );
}

export default ExecutionStatus;
