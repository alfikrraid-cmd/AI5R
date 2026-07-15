import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { createMissionProposal } from "../services/missionApi";

export default function Mission() {
  const navigate = useNavigate();

  const proposal = useMemo(() => {
    const saved = localStorage.getItem("ai5r_current_proposal");

    if (saved) {
      return JSON.parse(saved);
    }

    return createMissionProposal("Build Restaurant Management System");
  }, []);

  return (
    <main className="page">
      <section className="card">
        <small style={{color:"#6366f1", fontWeight:700}}>
          MISSION PROPOSAL · {proposal.id}
        </small>

        <h1 style={{marginTop:10}}>
          {proposal.title}
        </h1>

        <p className="muted">
          {proposal.summary}
        </p>

        <hr style={{margin:"30px 0"}}/>

        <h3>Departments Required</h3>

        <table style={{width:"100%"}}>
          <tbody>
            {proposal.departments.map(([department, responsibility]) => (
              <tr key={department}>
                <td style={{padding:"10px 0"}}>{department}</td>
                <td style={{padding:"10px 0"}}>{responsibility}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <hr style={{margin:"30px 0"}}/>

        <div style={{
          display:"grid",
          gridTemplateColumns:"1fr 1fr",
          gap:20
        }}>
          <div>
            <h3>Estimated Duration</h3>
            <h2>{proposal.duration}</h2>
          </div>

          <div>
            <h3>Confidence</h3>
            <h2>{proposal.confidence}</h2>
          </div>
        </div>

        <hr style={{margin:"30px 0"}}/>

        <h3>Expected Deliverables</h3>

        <ul>
          {proposal.deliverables.map((deliverable) => (
            <li key={deliverable}>{deliverable}</li>
          ))}
        </ul>

        <button
          className="button"
          onClick={() => navigate("/progress")}
        >
          ✅ Approve Mission
        </button>
      </section>
    </main>
  );
}
