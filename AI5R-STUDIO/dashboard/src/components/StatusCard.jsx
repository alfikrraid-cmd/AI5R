import { CheckCircle } from "lucide-react";

export default function StatusCard() {

    return (

        <div className="grid grid-cols-3 gap-6 mt-20">

            <div className="bg-[#111B31] rounded-2xl p-6">

                <CheckCircle className="text-green-400"/>

                <h2 className="mt-4 font-semibold">

                    AI Employees

                </h2>

                <p className="text-gray-400">

                    8 Online

                </p>

            </div>

            <div className="bg-[#111B31] rounded-2xl p-6">

                <CheckCircle className="text-yellow-400"/>

                <h2 className="mt-4 font-semibold">

                    Pending Approval

                </h2>

                <p className="text-gray-400">

                    2 Items

                </p>

            </div>

            <div className="bg-[#111B31] rounded-2xl p-6">

                <CheckCircle className="text-green-400"/>

                <h2 className="mt-4 font-semibold">

                    System

                </h2>

                <p className="text-gray-400">

                    Operational

                </p>

            </div>

        </div>

    );

}