function Blueprint({data}){


if(!data)
return null;


return (

<div className="blueprint">


<h2>
System Blueprint
</h2>


<h3>
{data.system_name}
</h3>


<p>
Deployment:
{data.deployment}
</p>


<h4>
Agents
</h4>


<ul>

{
data.agents.map(
(agent,index)=>(

<li key={index}>
{agent}
</li>

)

)
}

</ul>


<button>
Build This System
</button>


</div>

)

}


export default Blueprint;
