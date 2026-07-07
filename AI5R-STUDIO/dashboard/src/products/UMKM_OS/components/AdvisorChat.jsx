import {
    useState
}
from "react";


import {
    askAdvisor
}
from "../advisor/advisorEngine";



export default function AdvisorChat(){


    const [question,setQuestion] =
    useState("");


    const [answer,setAnswer] =
    useState(null);



    function submit(){

        setAnswer(
            askAdvisor(question)
        );

    }



    return (

        <div className="card">


            <h2>
                🤖 AI Business Advisor
            </h2>


            <input

                value={question}

                onChange={
                    e=>setQuestion(
                        e.target.value
                    )
                }

                placeholder="Ask your business question..."

            />


            <button
                onClick={submit}
            >
                Analyze
            </button>



            {
                answer && (

                    <div>

                        <p>
                            Insight:
                            {" "}
                            {answer.insight}
                        </p>


                        <p>
                            Recommendation:
                            {" "}
                            {answer.recommendation}
                        </p>


                        <p>
                            Priority:
                            {" "}
                            {answer.priority}
                        </p>

                    </div>

                )
            }


        </div>

    );

}
