import {
    DEPLOYMENT_STATUS
}
from "./deployment/deploymentStatus";



export default function ProductDeployment(){


    return (

        <div className="card">


            <h2>
                🚀 Deployment Monitor
            </h2>


            {
                DEPLOYMENT_STATUS.map(

                    item => (

                        <div key={item.product}>


                            <h3>
                                {item.product}
                            </h3>


                            <p>
                                Runtime:
                                {" "}
                                {item.runtime}
                            </p>


                            <p>
                                Agents:
                                {" "}
                                {item.agents}
                            </p>


                            <p>
                                Health:
                                {" "}
                                {item.health}
                            </p>


                        </div>

                    )

                )
            }


        </div>

    );

}
