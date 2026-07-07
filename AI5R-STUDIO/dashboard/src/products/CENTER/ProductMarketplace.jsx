import {
    MARKETPLACE_PRODUCTS
}
from "./marketplace/marketplaceProducts";



export default function ProductMarketplace(){


    return (

        <div className="card">


            <h2>
                🏪 AI5R Product Marketplace
            </h2>


            {
                MARKETPLACE_PRODUCTS.map(

                    product => (

                        <div key={product.name}>


                            <h3>
                                {product.name}
                            </h3>


                            <p>
                                {product.description}
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


        </div>

    );

}
