export default function IntelligenceGraph(){

    const nodes = [

        "🌍 Reality",

        "👁 Observation",

        "🧠 LTSA Brain",

        "🤖 Digital Employee",

        "⚖ Decision",

        "⚡ Action",

        "💾 Memory",

        "🌱 Learning"

    ];


    return (

        <div className="card">

            <h2>
                AI5R Intelligence Graph
            </h2>


            {
                nodes.map(
                    (node,index)=>(

                        <p key={index}>

                            {index + 1}.
                            {" "}
                            {node}

                        </p>

                    )
                )
            }


        </div>

    );

}
