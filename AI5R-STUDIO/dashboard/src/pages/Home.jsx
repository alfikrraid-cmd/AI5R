import { Link } from "react-router-dom";

export default function Home() {
    return (

        <div className="min-h-screen bg-[#0B1020] text-white flex items-center justify-center">

            <div className="text-center">

                <h1 className="text-5xl font-bold mb-6">

                    🌳 AI5R Studio

                </h1>

                <p className="text-gray-400 mb-10">

                    One Root. Many Branches. Infinite Intelligence.

                </p>

                <Link

                    to="/ltsa"

                    className="bg-emerald-500 px-8 py-4 rounded-xl text-lg hover:bg-emerald-400"

                >

                    Open LTSA-BRAIN

                </Link>

            </div>

        </div>

    );
}