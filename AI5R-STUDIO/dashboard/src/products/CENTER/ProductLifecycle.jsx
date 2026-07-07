import {
    PRODUCT_LIFECYCLE
}
from "./lifecycle/productLifecycle";



export default function ProductLifecycle(){


    return (

        <div className="card">


            <h2>
                🔄 Product Lifecycle
            </h2>


            {
                PRODUCT_LIFECYCLE.map(

                    item => (

                        <div key={item.product}>


                            <h3>
                                {item.product}
                            </h3>


                            <p>
                                Stage:
                                {" "}
                                {item.stage}
                            </p>


                            <p>
                                Version:
                                {" "}
                                {item.version}
                            </p>


                        </div>

                    )

                )
            }


        </div>

    );

}
