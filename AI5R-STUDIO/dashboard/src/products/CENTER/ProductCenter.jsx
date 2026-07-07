import {
    AI5R_PRODUCTS
}
from "./productRegistry";



export default function ProductCenter(){


    return (

        <div className="card">


            <h2>
                🌳 AI5R Product Center
            </h2>


            {
                AI5R_PRODUCTS.map(
                    product => (

                        <div key={product.id}>


                            <h3>
                                {product.name}
                            </h3>


                            <p>
                                Category:
                                {" "}
                                {product.category}
                            </p>


                            <p>
                                Status:
                                {" "}
                                {product.status}
                            </p>


                        </div>

                    )
                )
            }


            <p>

                Total Products:
                {" "}
                {AI5R_PRODUCTS.length}

            </p>


        </div>

    );

}
