import {
    PRODUCT_ROADMAP
}
from "./roadmap/productRoadmap";



export default function ProductRoadmap(){


    return (

        <div className="card">


            <h2>
                🗺️ AI5R Product Roadmap
            </h2>


            {
                PRODUCT_ROADMAP.map(

                    item => (

                        <div key={item.product}>


                            <h3>
                                {item.phase}
                            </h3>


                            <p>
                                Product:
                                {" "}
                                {item.product}
                            </p>


                            <p>
                                Action:
                                {" "}
                                {item.action}
                            </p>


                        </div>

                    )

                )
            }


        </div>

    );

}
