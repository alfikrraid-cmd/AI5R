import {
    getCommandCenter
}
from "./command/commandCenter";



export default function ProductCommandCenter(){


    const data =
    getCommandCenter();



    return (

        <div className="card">


            <h2>
                🌳 {data.platform}
            </h2>


            <p>
                Status:
                {" "}
                {data.status}
            </p>


            <p>
                Products:
                {" "}
                {data.products}
            </p>


            <p>
                Active:
                {" "}
                {data.active}
            </p>


            <p>
                Building:
                {" "}
                {data.building}
            </p>


            <p>
                Health:
                {" "}
                {data.health}
            </p>


        </div>

    );

}
