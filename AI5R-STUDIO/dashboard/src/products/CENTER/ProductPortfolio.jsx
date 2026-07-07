import {
    PRODUCT_PORTFOLIO
}
from "./portfolio/portfolioAnalytics";



export default function ProductPortfolio(){


    return (

        <div className="card">


            <h2>
                📈 Product Portfolio Analytics
            </h2>


            {
                PRODUCT_PORTFOLIO.map(

                    item => (

                        <div key={item.product}>


                            <h3>
                                {item.product}
                            </h3>


                            <p>
                                Market:
                                {" "}
                                {item.market}
                            </p>


                            <p>
                                Priority:
                                {" "}
                                {item.priority}
                            </p>


                        </div>

                    )

                )
            }


        </div>

    );

}
