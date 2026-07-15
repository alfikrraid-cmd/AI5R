import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { createMissionProposal } from "../services/missionApi";

import CtoBanner from "../components/CtoBanner";
import EmployeeCard from "../components/EmployeeCard";
import Timeline from "../components/Timeline";

export default function Progress() {

  const navigate = useNavigate();

  const proposal = useMemo(() => {

    const saved = localStorage.getItem("ai5r_current_proposal");

    if (saved) {
      return JSON.parse(saved);
    }

    return createMissionProposal(
      "Build Restaurant Management System"
    );

  }, []);

  const timeline = [

    {
      time:"10:31",
      message:"CEO approved mission"
    },

    {
      time:"10:32",
      message:"CTO completed architecture"
    },

    {
      time:"10:33",
      message:"Project Manager created sprint"
    },

    {
      time:"10:34",
      message:"Backend Engineer started coding"
    },

    {
      time:"10:35",
      message:"main.py generated"
    },

    {
      time:"10:36",
      message:"auth.py generated"
    },

    {
      time:"10:37",
      message:"README generated"
    },

    {
      time:"10:38",
      message:"ZIP exported"
    },

  ];

  const files = [

    "app/main.py",

    "app/routers/auth.py",

    "app/schemas.py",

    "README.md",

    "requirements.txt",

    "openapi.json",

  ];

  return (

    <main className="page">

      <CtoBanner />

      <section className="card">

        <small
          style={{
            color:"#4f46e5",
            fontWeight:700
          }}
        >

          MISSION IN PROGRESS

        </small>

        <h1
          style={{
            marginTop:10
          }}
        >

          {proposal.title}

        </h1>

        <p className="muted">

          AI Organization is manufacturing your product.

        </p>

      </section>

      <div

        style={{

          display:"grid",

          gridTemplateColumns:"repeat(auto-fit,minmax(260px,1fr))",

          gap:20,

          marginTop:30

        }}

      >

        <EmployeeCard

          title="AI CEO"

          status="ACTIVE"

          task="Mission Approved"

          progress={100}

        />

        <EmployeeCard

          title="AI CTO"

          status="SUPERVISING"

          task="Architecture Review"

          progress={95}

        />

        <EmployeeCard

          title="Project Manager"

          status="PLANNING"

          task="Creating Sprint"

          progress={85}

        />

        <EmployeeCard

          title="Backend Engineer"

          status="EXECUTING"

          task="Generating FastAPI"

          progress={72}

        />

        <EmployeeCard

          title="QA Engineer"

          status="WAITING"

          task="Waiting Backend"

          progress={20}

        />

        <EmployeeCard

          title="DevOps Engineer"

          status="IDLE"

          task="Waiting Deployment"

          progress={10}

        />

        <EmployeeCard

          title="Digital Factory"

          status="RUNNING"

          task="Generating Artifacts"

          progress={65}

        />

      </div>

      <section

        className="card"

        style={{

          marginTop:30

        }}

      >

        <h2>

          Generated Files

        </h2>

        <div

          style={{

            display:"flex",

            flexWrap:"wrap",

            gap:10,

            marginTop:20

          }}

        >

          {

            files.map(file=>(

              <div

                key={file}

                style={{

                  padding:"10px 16px",

                  background:"#ecfdf5",

                  borderRadius:999,

                  color:"#15803d",

                  fontWeight:700

                }}

              >

                ✓ {file}

              </div>

            ))

          }

        </div>

      </section>

      <section

        className="card"

        style={{

          marginTop:30

        }}

      >

        <Timeline events={timeline} />

      </section>

      <div

        style={{

          marginTop:30,

          textAlign:"center"

        }}

      >

        <button

          className="button"

          onClick={()=>navigate("/result")}

        >

          Continue to Delivery →

        </button>

      </div>

    </main>

  );

}
