export default function BrainStream(){

    const events = [
        "👁 Observation received",
        "🧠 Reasoning process started",
        "⚖ Decision generated",
        "⚡ Action executed",
        "💾 Memory stored",
        "🌱 Learning updated"
    ];

    return (
        <div className="card">

            <h2>
                Live Brain Activity
            </h2>

            {
                events.map(
                    (event,index)=>(
                        <p key={index}>
                            {event}
                        </p>
                    )
                )
            }

        </div>
    );
}
