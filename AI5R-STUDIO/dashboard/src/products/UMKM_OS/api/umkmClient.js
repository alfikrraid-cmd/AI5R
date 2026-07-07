const UMKM_API =
"http://localhost:8000";



export async function getUMKMStatus(){

    try{

        const response = await fetch(
            `${UMKM_API}/umkm/status`
        );


        if(!response.ok){

            throw new Error(
                "UMKM API unavailable"
            );

        }


        return await response.json();


    }catch(error){

        return {

            product:
            "AI5R UMKM OS",

            status:
            "DEMO",

            agents:4,

            decision:
            "HIGH",

            memories:245,

            insight:
            "Retention campaign recommended"

        };

    }

}
