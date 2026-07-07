export async function getBrainEvents(){
    return [
        {
            timestamp: new Date().toISOString(),
            employee_id: "EMP-001",
            module: "OBSERVATION",
            event: "OBSERVATION_CREATED",
            status: "SUCCESS",
            message: "Observation created from command input."
        },
        {
            timestamp: new Date().toISOString(),
            employee_id: "EMP-001",
            module: "MEMORY",
            event: "MEMORY_STORED",
            status: "SUCCESS",
            message: "Memory stored from observation."
        },
        {
            timestamp: new Date().toISOString(),
            employee_id: "EMP-001",
            module: "REASONING",
            event: "PLAN_GENERATED",
            status: "SUCCESS",
            message: "Reasoning plan generated."
        }
    ];
}
