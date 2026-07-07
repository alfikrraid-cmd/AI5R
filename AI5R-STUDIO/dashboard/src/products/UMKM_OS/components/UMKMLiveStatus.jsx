import {
    useEffect,
    useState
}
from "react";


import {
    getUMKMStatus
}
from "../api/umkmClient";



export default function UMKMLiveStatus(){


    const [data,setData] = useState(null);



    useEffect(()=>{

        getUMKMStatus()
        .then(
            result=>setData(result)
        );

    },[]);



    if(!data){

        return (

            <div className="card">

                Loading UMKM OS...

            </div>

        );

    }



    return (

        <div className="card">


            <h2>
                AI5R UMKM OS Live Status
            </h2>


            <p>
                Status:
                {" "}
                {data.status}
            </p>


            <p>
                Agents:
                {" "}
                {data.agents}
            </p>


            <p>
                Decision:
                {" "}
                {data.decision}
            </p>


            <p>
                Memory:
                {" "}
                {data.memories}
            </p>


            <p>
                Insight:
                {" "}
                {data.insight}
            </p>


        </div>

    );

}
