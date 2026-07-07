import {
    DemoAnalytics
}
from "../analytics/demoAnalytics";



export default function DemoAnalytics(){


    const analytics =
    new DemoAnalytics();


    analytics.track(
        "ADVISOR_USED"
    );


    analytics.track(
        "AGENT_VIEWED"
    );


    const data =
    analytics.summary();



    return (

        <div className="card">


            <h2>
                📊 Demo Analytics
            </h2>


            <p>
                Events:
                {" "}
                {data.total_events}
            </p>


            <p>
                Advisor:
                ACTIVE
            </p>


            <p>
                Agents:
                MONITORED
            </p>


        </div>

    );

}
