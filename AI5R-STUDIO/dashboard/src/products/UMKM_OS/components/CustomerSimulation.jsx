import {
    useState
}
from "react";


import {
    simulateBusinessConversation
}
from "../simulation/customerSimulation";



export default function CustomerSimulation(){


    const [question,setQuestion] =
    useState("");


    const [response,setResponse] =
    useState(null);



    function ask(){

        setResponse(

            simulateBusinessConversation(
                question
            )

        );

    }



    return (

        <div className="card">


            <h2>
                💬 Owner Simulation
            </h2>


            <input

                value={question}

                onChange={
                    e=>setQuestion(
                        e.target.value
                    )
                }

                placeholder="Ask AI5R about your business..."

            />


            <button
                onClick={ask}
            >
                Ask AI5R
            </button>



            {
                response && (

                    <div>

                        <p>
                            Analysis:
                            {" "}
                            {response.analysis}
                        </p>


                        <p>
                            Priority:
                            {" "}
                            {response.priority}
                        </p>


                        <h4>
                            Action Plan
                        </h4>


                        {
                            response.actions.map(
                                action => (

                                    <p key={action}>
                                        ✅ {action}
                                    </p>

                                )
                            )
                        }

                    </div>

                )
            }


        </div>

    );

}
