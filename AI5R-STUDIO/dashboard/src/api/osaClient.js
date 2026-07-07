export async function getEmployees(){
    return [
        {
            id: "EMP-001",
            name: "Marketing AI",
            role: "Campaign Planner",
            status: "READY"
        },
        {
            id: "EMP-002",
            name: "Research AI",
            role: "Opportunity Scanner",
            status: "READY"
        },
        {
            id: "EMP-003",
            name: "Execution AI",
            role: "Task Executor",
            status: "WAITING"
        }
    ];
}

export async function sendCommand(prompt, employeeId){
    return {
        status: "SUCCESS",
        task_id: "TASK-001",
        employee_id: employeeId,
        response: `Command received: ${prompt}`,
        stage: "PLANNING"
    };
}

export async function getTasks(){
    return [
        {
            id: "TASK-001",
            title: "Create campaign strategy",
            status: "RUNNING"
        },
        {
            id: "TASK-002",
            title: "Scan opportunity database",
            status: "COMPLETED"
        },
        {
            id: "TASK-003",
            title: "Prepare execution plan",
            status: "WAITING"
        }
    ];
}
