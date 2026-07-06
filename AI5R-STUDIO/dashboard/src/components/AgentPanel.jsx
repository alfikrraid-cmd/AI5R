export default function AgentPanel(){

    const agents = [
        "CEO AI",
        "Marketing Agent",
        "Research Agent",
        "Finance Agent"
    ];


    return (

        <div className="card">

            <h2>
                Digital Employees
            </h2>


            {
                agents.map(
                    agent => (
                        <p key={agent}>
                            🟢 {agent}
                        </p>
                    )
                )
            }

        </div>

    );

}
