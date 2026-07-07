import {
    getProductRecommendation
}
from "./recommendation/productRecommendation";



export default function ProductRecommendation(){


    const recommendations =
    getProductRecommendation();



    return (

        <div className="card">


            <h2>
                🧠 AI5R Product Strategy Recommendation
            </h2>


            {
                recommendations.map(

                    item => (

                        <div key={item.product}>


                            <h3>
                                {item.product}
                            </h3>


                            <p>
                                Action:
                                {" "}
                                {item.action}
                            </p>


                            <p>
                                Reason:
                                {" "}
                                {item.reason}
                            </p>


                        </div>

                    )

                )
            }


        </div>

    );

}
