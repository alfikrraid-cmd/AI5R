export default function EmployeePanel(){

    const employees = [

        {
            name:"CEO AI",
            state:"THINKING"
        },

        {
            name:"Marketing Agent",
            state:"EXECUTING"
        },

        {
            name:"Research Agent",
            state:"OBSERVING"
        },

        {
            name:"Finance Agent",
            state:"WAITING"
        }

    ];


    return (

        <div className="card">

            <h2>
                Digital Employee Network
            </h2>


            {
                employees.map(
                    employee => (

                        <p key={employee.name}>

                            🟢 {employee.name}

                            {" - "}

                            {employee.state}

                        </p>

                    )
                )
            }


        </div>

    );

}
