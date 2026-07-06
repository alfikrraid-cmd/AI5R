import { useState } from "react";


export default function CommandConsole(){

    const [command,setCommand] = useState("");

    const [history,setHistory] = useState([]);



    function execute(){

        if(!command) return;


        setHistory([
            ...history,
            command
        ]);


        setCommand("");

    }



    return (

        <div className="card">

            <h2>
                AI5R Command Console
            </h2>


            <input

                value={command}

                onChange={
                    e=>setCommand(
                        e.target.value
                    )
                }

                placeholder="Enter command..."

            />


            <button
                onClick={execute}
            >
                Execute
            </button>


            {
                history.map(
                    (item,index)=>(

                        <p key={index}>
                            &gt; {item}
                        </p>

                    )
                )
            }


        </div>

    );

}
