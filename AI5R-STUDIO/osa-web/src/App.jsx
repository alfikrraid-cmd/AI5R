import {useState} from "react";
import "./style.css";


function App(){


const [messages,setMessages] = useState([

{
role:"osa",
text:"Halo, saya OSA. Sistem apa yang ingin Anda bangun?"
}

]);


const [input,setInput] = useState("");



function sendMessage(){


if(!input)
return;


const userMessage={

role:"user",

text:input

};


const osaMessage={

role:"osa",

text:
"Saya memahami kebutuhan Anda. Saya akan menganalisa tujuan, pengguna, workflow, dan deployment sistem."

};



setMessages([

...messages,

userMessage,

osaMessage

]);


setInput("");

}



return (

<div className="container">


<h1>
🌳 OSA
</h1>


<h2>
Opportunity System Aji
</h2>


<div className="chat">


{
messages.map(
(msg,index)=>(

<div
key={index}
className={msg.role}
>

<b>
{msg.role}
</b>

<p>
{msg.text}
</p>


</div>

)

)
}


</div>



<input

value={input}

onChange={
(e)=>setInput(e.target.value)
}

placeholder="Jelaskan sistem yang ingin dibuat..."

/>


<button
onClick={sendMessage}
>

Kirim

</button>


</div>

)

}


export default App;
