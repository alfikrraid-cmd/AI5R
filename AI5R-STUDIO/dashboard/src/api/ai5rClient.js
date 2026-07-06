const API_URL = "http://localhost:8000";


export async function getSystemStatus(){

    return {
        status: "ONLINE",
        agents: 5,
        brain: "ACTIVE",
        memories: 120
    };
}
