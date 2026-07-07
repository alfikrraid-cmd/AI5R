import { useEffect, useState } from "react";


import {
    getSystemStatus,
    getDashboardData
} from "./api/ai5rClient";


import StatusCard from "./components/StatusCard";
import AgentPanel from "./components/AgentPanel";
import BrainActivity from "./components/BrainActivity";
import MemoryPanel from "./components/MemoryPanel";
import BrainStream from "./components/BrainStream";
import LiveEventStream from "./components/LiveEventStream";
import LiveRuntimeStatus from "./components/LiveRuntimeStatus";
import LiveOrganizationTree from "./components/LiveOrganizationTree";
import LiveTaskTimeline from "./components/LiveTaskTimeline";
import BrainEventStream from "./components/BrainEventStream";
import EmployeePanel from "./components/EmployeePanel";
import Timeline from "./components/Timeline";
import IntelligenceGraph from "./components/IntelligenceGraph";
import CommandConsole from "./components/CommandConsole";
import { UMKMOverview, UMKMAgents, UMKMInsight } from "./products/UMKM_OS";
import UMKMLiveStatus from "./products/UMKM_OS/components/UMKMLiveStatus";
import AdvisorChat from "./products/UMKM_OS/components/AdvisorChat";
import ExecutiveDashboard from "./products/UMKM_OS/components/ExecutiveDashboard";



function App(){


    const [system,setSystem] = useState(
        {
            status:"LOADING"
        }
    );


    const [dashboard,setDashboard] = useState(
        {
            agents:0,
            memories:0
        }
    );



    useEffect(()=>{


        getSystemStatus()
            .then(data=>{
                setSystem(data);
            });


        getDashboardData()
            .then(data=>{
                setDashboard(data);
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
                    value={
                        dashboard.agents
                    }
                />


                <StatusCard
                    title="Memory"
                    value={
                        dashboard.memories
                    }
                />


            </div>



            <AgentPanel />

            <BrainActivity />

            <MemoryPanel />

            <BrainStream />
            <LiveRuntimeStatus />
            <LiveOrganizationTree />
            <LiveTaskTimeline />
            <LiveEventStream />

            <BrainEventStream />

            <EmployeePanel />

            <Timeline />

            <IntelligenceGraph />

            <CommandConsole />

            <UMKMOverview />

            <UMKMAgents />

            <UMKMInsight />

            <UMKMLiveStatus />

            <AdvisorChat />

            <ExecutiveDashboard />


        </div>

    );

}


export default App;
