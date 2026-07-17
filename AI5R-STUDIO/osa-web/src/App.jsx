import {useState} from "react";
import Blueprint from "./components/Blueprint";
import DocumentUpload from "./components/DocumentUpload";
import DocumentReview from "./components/DocumentReview";
import "./style.css";


function App(){


const [blueprint,setBlueprint]=useState(null);
const [extraction,setExtraction]=useState(null);



function createBlueprint(){


setBlueprint({

system_name:
"AI5R FILM OS",

deployment:
"OWN SERVER",

agents:[

"STORY_AGENT",

"CHARACTER_AGENT",

"PRODUCTION_AGENT"

]

});


}



return (

<div className="container">


<h1>
🌳 OSA
</h1>


<p>
Design your AI system
</p>


<button
onClick={createBlueprint}
>

Generate Blueprint

</button>


<Blueprint
data={blueprint}
/>


<hr />


{
extraction
? <DocumentReview extraction={extraction} onSaved={() => setExtraction(null)} />
: <DocumentUpload onExtracted={setExtraction} />
}


</div>

)

}


export default App;
