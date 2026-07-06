import StatusCard from "./components/StatusCard";
import AgentPanel from "./components/AgentPanel";
import BrainActivity from "./components/BrainActivity";
import MemoryPanel from "./components/MemoryPanel";


function App(){

    return (

        <div className="dashboard">


            <h1>
                🌳 AI5R OS COMMAND CENTER
            </h1>


            <div className="grid">

                <StatusCard
                    title="System"
                    value="ONLINE"
                />

                <StatusCard
                    title="Brain"
                    value="ACTIVE"
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


        </div>

    );

}


export default App;
