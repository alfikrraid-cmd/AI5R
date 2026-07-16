import { Mic, Paperclip, Rocket } from "lucide-react";
import { motion } from "framer-motion";

export default function MissionInput() {

    return (

        <motion.div

            initial={{ opacity: 0 }}

            animate={{ opacity: 1 }}

            transition={{ delay: .4 }}

            className="mt-16"

        >

            <label className="text-lg text-gray-300">

                Apa yang ingin Anda kerjakan hari ini?

            </label>

            <textarea

                rows="4"

                placeholder="Contoh: Saya ingin memenangkan tender PLN..."

                className="w-full mt-4 rounded-2xl bg-[#10172A] border border-[#1D2843] p-6 outline-none text-lg"

            />

            <div className="flex justify-between items-center mt-6">

                <div className="flex gap-4">

                    <button className="p-3 rounded-xl bg-[#18233d] hover:bg-[#213055]">

                        <Mic size={20} />

                    </button>

                    <button className="p-3 rounded-xl bg-[#18233d] hover:bg-[#213055]">

                        <Paperclip size={20} />

                    </button>

                </div>

                <button

                    className="flex items-center gap-2 bg-green-500 hover:bg-green-400 text-black px-8 py-4 rounded-2xl font-semibold"

                >

                    <Rocket size={20}/>

                    Mulai Bekerja

                </button>

            </div>

        </motion.div>

    );

}