import { motion } from "framer-motion";

export default function FloatingParticles(){

    return(

        <>

        {[...Array(20)].map((_,i)=>(

            <motion.div

                key={i}

                className="absolute w-2 h-2 rounded-full bg-green-400"

                initial={{

                    x:Math.random()*1400,

                    y:Math.random()*800,

                    opacity:.2

                }}

                animate={{

                    y:["0%","-40%"],

                    opacity:[.2,.8,.2]

                }}

                transition={{

                    repeat:Infinity,

                    duration:5+Math.random()*5

                }}

            />

        ))}

        </>

    )

}