export default function UMKMAgents(){

    const agents = [

        "Marketing Agent",

        "Sales Agent",

        "Finance Agent",

        "Growth Agent"

    ];


    return (

        <div className="card">

            <h2>
                Digital Business Team
            </h2>


            {
                agents.map(
                    agent => (

                        <p key={agent}>
                            🤖 {agent} READY
                        </p>

                    )
                )
            }


        </div>

    );

}
