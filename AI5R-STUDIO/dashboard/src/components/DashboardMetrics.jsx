export default function DashboardMetrics({
    data
}){


    return (

        <div className="grid">


            <div className="card">

                <h3>System</h3>

                <strong>
                    {data.system_status}
                </strong>

            </div>



            <div className="card">

                <h3>Brain</h3>

                <strong>
                    {data.brain_status}
                </strong>

            </div>



            <div className="card">

                <h3>Agents</h3>

                <strong>
                    {data.agents}
                </strong>

            </div>



            <div className="card">

                <h3>Memory</h3>

                <strong>
                    {data.memories}
                </strong>

            </div>


        </div>

    );

}
