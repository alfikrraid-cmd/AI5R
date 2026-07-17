import { Card } from "../design-system";

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

        <Card title="Digital Employee Network">

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


        </Card>

    );

}
