export default function CtoBanner() {

  return (

    <div
      style={{
        display:"flex",
        alignItems:"center",
        gap:20,
        background:"white",
        borderRadius:20,
        padding:20,
        marginBottom:30,
        boxShadow:"0 10px 30px rgba(0,0,0,.08)"
      }}
    >

      <div
        style={{
          width:72,
          height:72,
          borderRadius:"50%",
          background:"#4f46e5",
          color:"white",
          display:"flex",
          alignItems:"center",
          justifyContent:"center",
          fontSize:30,
          fontWeight:700
        }}
      >
        J
      </div>

      <div>

        <div
          style={{
            fontWeight:700,
            fontSize:22
          }}
        >
          Jazari — AI CTO
        </div>

        <div
          style={{
            color:"#64748b",
            marginTop:6
          }}
        >
          Supervising Digital Workforce...
        </div>

      </div>

      <div
        style={{
          marginLeft:"auto",
          padding:"8px 18px",
          background:"#dcfce7",
          borderRadius:999,
          fontWeight:700,
          color:"#15803d"
        }}
      >
        ● LIVE
      </div>

    </div>

  );

}
