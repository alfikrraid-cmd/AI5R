const API_URL = "http://localhost:8000";


export async function getSystemStatus(){

    try{

        const response = await fetch(
            `${API_URL}/health`
        );


        if(!response.ok){

            throw new Error(
                "API unavailable"
            );

        }


        return await response.json();


    }catch(error){

        return {

            status:"OFFLINE",

            system:"AI5R",

            service:"COMMAND_CENTER"

        };

    }

}



export async function getDashboardData(){

    try{

        const response = await fetch(
            `${API_URL}/dashboard`
        );


        if(!response.ok){

            throw new Error(
                "Dashboard API unavailable"
            );

        }


        return await response.json();


    }catch(error){

        return {

            system_status:"OFFLINE",

            brain_status:"UNKNOWN",

            agents:0,

            memories:0,

            governance:"UNKNOWN"

        };

    }

}
