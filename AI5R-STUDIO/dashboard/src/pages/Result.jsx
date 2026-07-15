import { useMemo } from "react";
import { createMissionProposal } from "../services/missionApi";

const files = [
  "app/main.py",
  "app/routers/auth.py",
  "app/schemas.py",
  "README.md",
  "requirements.txt",
  "openapi.json",
];

export default function Result() {

  const proposal = useMemo(() => {

    const saved = localStorage.getItem("ai5r_current_proposal");

    if(saved){
      return JSON.parse(saved);
    }

    return createMissionProposal(
      "Build Restaurant Management System"
    );

  },[]);

  return (

    <main className="page">

      <section className="card">

        <div
          style={{
            textAlign:"center",
            marginBottom:40
          }}
        >

          <h1
            style={{
              fontSize:52,
              marginBottom:10
            }}
          >
            🎉
          </h1>

          <h1>Mission Completed</h1>

          <p className="muted">

            Your AI Organization has successfully completed the mission.

          </p>

        </div>

        <hr/>

        <h2>Mission</h2>

        <p>{proposal.title}</p>

        <hr/>

        <h2>Manufacturing Summary</h2>

        <table style={{width:"100%"}}>

          <tbody>

            <tr>
              <td>Mission ID</td>
              <td>MISSION-0001</td>
            </tr>

            <tr>
              <td>Organization</td>
              <td>IT Department</td>
            </tr>

            <tr>
              <td>Employees</td>
              <td>6 Digital Employees</td>
            </tr>

            <tr>
              <td>Factory</td>
              <td>AI5R Digital Factory</td>
            </tr>

            <tr>
              <td>Status</td>
              <td style={{color:"#16a34a"}}>
                BUILD VALID
              </td>
            </tr>

          </tbody>

        </table>

        <hr/>

        <h2>Artifacts</h2>

        {files.map(file=>(

          <div
            key={file}
            style={{
              padding:"8px 0"
            }}
          >

            ✓ {file}

          </div>

        ))}

        <hr/>

        <div
          style={{
            display:"flex",
            gap:20,
            flexWrap:"wrap",
            marginTop:30
          }}
        >

          <button className="button">
            📦 Download ZIP
          </button>

          <button className="button">
            📄 View Source
          </button>

          <button className="button">
            🚀 Deploy
          </button>

        </div>

      </section>

      <section
        className="card"
        style={{
          marginTop:30
        }}
      >

        <h2>Manufacturing Certificate</h2>

        <div
          style={{
            border:"2px dashed #4f46e5",
            borderRadius:16,
            padding:30,
            marginTop:20
          }}
        >

          <h3>🌳 AI5R Digital Factory</h3>

          <p>

            This certifies that the requested digital product
            has been successfully manufactured by AI5R.

          </p>

          <table style={{width:"100%"}}>

            <tbody>

              <tr>

                <td>Mission</td>

                <td>MISSION-0001</td>

              </tr>

              <tr>

                <td>Factory</td>

                <td>AI5R Digital Factory</td>

              </tr>

              <tr>

                <td>Department</td>

                <td>IT Department</td>

              </tr>

              <tr>

                <td>Result</td>

                <td>SUCCESS</td>

              </tr>

            </tbody>

          </table>

        </div>

      </section>

    </main>

  );

}
