import { useEffect, useState } from "react";

import {
    getEmployees,
    getTasks,
    sendCommand
} from "../api/osaClient";

import EmployeeSelector from "../components/EmployeeSelector";
import CommandInput from "../components/CommandInput";
import ConversationPanel from "../components/ConversationPanel";
import TaskQueue from "../components/TaskQueue";
import ExecutionStatus from "../components/ExecutionStatus";
import BrainEventStream from "../components/BrainEventStream";

function CommandCenter() {
    const [employees, setEmployees] = useState([]);
    const [selectedEmployee, setSelectedEmployee] = useState("");
    const [tasks, setTasks] = useState([]);
    const [messages, setMessages] = useState([
        {
            sender: "OSA",
            text: "Command Center ready."
        }
    ]);

    useEffect(() => {
        getEmployees().then((data) => {
            setEmployees(data);

            if (data.length > 0) {
                setSelectedEmployee(data[0].id);
            }
        });

        getTasks().then(setTasks);
    }, []);

    async function handleExecute(prompt) {
        setMessages((current) => [
            ...current,
            {
                sender: "USER",
                text: prompt
            }
        ]);

        const result = await sendCommand(prompt, selectedEmployee);

        setMessages((current) => [
            ...current,
            {
                sender: "OSA",
                text: `${result.response} | Stage: ${result.stage} | Task: ${result.task_id}`
            }
        ]);

        setTasks((current) => [
            {
                id: result.task_id,
                title: prompt,
                status: result.stage
            },
            ...current
        ]);
    }

    return (
        <div className="command-center">
            <h1>OSA Command Center</h1>

            <div className="command-layout">
                <div className="command-left">
                    <EmployeeSelector
                        employees={employees}
                        selectedEmployee={selectedEmployee}
                        onSelect={setSelectedEmployee}
                    />

                    <CommandInput onExecute={handleExecute} />

                    <ExecutionStatus />

                    <BrainEventStream />
                </div>

                <div className="command-right">
                    <ConversationPanel messages={messages} />
                    <TaskQueue tasks={tasks} />
                </div>
            </div>
        </div>
    );
}

export default CommandCenter;
