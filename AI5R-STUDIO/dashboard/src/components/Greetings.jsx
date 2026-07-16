import { motion } from "framer-motion";

export default function Greeting() {

    const hour = new Date().getHours();

    let greeting = "Good Evening";

    if (hour < 12) {
        greeting = "Good Morning";
    } else if (hour < 17) {
        greeting = "Good Afternoon";
    }

    return (

        <motion.div
            initial={{ opacity: 0, y: -30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .6 }}
            className="text-center"
        >

            <img
                src="/logo.svg"
                className="w-24 mx-auto mb-8"
            />

            <h1 className="text-6xl font-bold">
                AI5R
            </h1>

            <p className="text-green-400 mt-2 uppercase tracking-widest">
                Office
            </p>

            <h2 className="text-2xl mt-10 font-semibold">

                {greeting}, Chief.

            </h2>

            <p className="text-gray-400 mt-3">
                Your AI Company is Ready.
            </p>

        </motion.div>

    );

}