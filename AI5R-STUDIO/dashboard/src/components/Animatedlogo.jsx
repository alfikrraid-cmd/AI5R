import { motion } from "framer-motion";

export default function AnimatedLogo(){

    return(

        <motion.div

            animate={{

                scale:[1,1.05,1],

                opacity:[.8,1,.8]

            }}

            transition={{

                repeat:Infinity,

                duration:3

            }}

            className="relative"

        >

            <img

                src="/logo.svg"

                className="w-24"

            />

            <div className="absolute inset-0 blur-3xl bg-green-500 opacity-30"/>

        </motion.div>

    )

}