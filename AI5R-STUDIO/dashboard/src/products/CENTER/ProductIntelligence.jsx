import {
    getProductIntelligence
}
from "./intelligence/productIntelligence";



export default function ProductIntelligence(){


    const data =
    getProductIntelligence();



    return (

        <div className="card">


            <h2>
                🧠 Product Intelligence
            </h2>


            <p>
                Total Products:
                {" "}
                {data.total}
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
                Planned:
                {" "}
                {data.planned}
            </p>


            <p>
                Platform Health:
                {" "}
                {data.health}
            </p>


        </div>

    );

}
