import { Card } from "../design-system";

export default function AgentPanel(){

    const agents = [
        "CEO AI",
        "Marketing Agent",
        "Research Agent",
        "Finance Agent"
    ];


    return (

        <Card title="Digital Employees">

            {
                agents.map(
                    agent => (
                        <p key={agent}>
                            🟢 {agent}
                        </p>
                    )
                )
            }

        </Card>

    );

}
