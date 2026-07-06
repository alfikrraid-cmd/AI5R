const API_URL = "http://localhost:8000";


export async function getSystemStatus(){

    try {

        const response = await fetch(
            `${API_URL}/health`
        );


        if(!response.ok){

            throw new Error(
                "API unavailable"
            );

        }


        return await response.json();


    } catch(error){

        return {

            status:"OFFLINE",

            system:"AI5R",

            service:"COMMAND_CENTER"

        };

    }

}
