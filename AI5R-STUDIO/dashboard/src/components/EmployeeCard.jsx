export default function EmployeeCard({

title,

status,

task,

progress

}){

return(

<div

style={{

background:"white",

padding:20,

borderRadius:20,

boxShadow:"0 10px 30px rgba(0,0,0,.08)"

}}

>

<div

style={{

display:"flex",

justifyContent:"space-between"

}}

>

<strong>

{title}

</strong>

<span>

{status}

</span>

</div>

<div

style={{

marginTop:15,

color:"#64748b"

}}

>

{task}

</div>

<div

style={{

height:10,

background:"#e2e8f0",

borderRadius:999,

marginTop:20

}}

>

<div

style={{

width:progress+"%",

height:10,

background:"#4f46e5",

borderRadius:999

}}

>

</div>

</div>

</div>

)

}
