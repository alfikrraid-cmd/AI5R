import {
    useEffect,
    useState
} from "react";


import {
    getSystemStatus
} from "./api/ai5rClient";


import StatusCard from "./components/StatusCard";
import AgentPanel from "./components/AgentPanel";
import BrainActivity from "./components/BrainActivity";
import MemoryPanel from "./components/MemoryPanel";
import BrainStream from "./components/BrainStream";
import EmployeePanel from "./components/EmployeePanel";
import Timeline from "./components/Timeline";



function App(){


    const [system,setSystem] = useState(
        {
            status:"LOADING"
        }
    );



    useEffect(()=>{


        getSystemStatus()
            .then(data=>{
                setSystem(data);
            });


    },[]);



    return (

        <div className="dashboard">


            <h1>
                🌳 AI5R OS COMMAND CENTER
            </h1>



            <div className="grid">


                <StatusCard
                    title="System"
                    value={
                        system.status
                    }
                />


                <StatusCard
                    title="Service"
                    value={
                        system.service || "-"
                    }
                />


                <StatusCard
                    title="Agents"
                    value="4"
                />


                <StatusCard
                    title="Memory"
                    value="120"
                />


            </div>


            <AgentPanel />

            <BrainActivity />

            <MemoryPanel />

            <BrainStream />

            <EmployeePanel />

            <Timeline />


        </div>

    );

}


export default App;
