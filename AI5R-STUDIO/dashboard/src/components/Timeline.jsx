export default function Timeline(){

    const activities = [

        "10:01 👁 Reality detected",

        "10:02 🧠 Brain analyzed",

        "10:03 🤖 Employee assigned",

        "10:04 ⚡ Action executed",

        "10:05 💾 Experience stored",

        "10:06 🌱 Learning updated"

    ];


    return (

        <div className="card">

            <h2>
                Realtime Timeline
            </h2>


            {
                activities.map(
                    (activity,index)=>(

                        <p key={index}>
                            {activity}
                        </p>

                    )
                )
            }


        </div>

    );

}
