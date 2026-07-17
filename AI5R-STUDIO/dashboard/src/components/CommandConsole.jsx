import { useState } from "react";
import { sendCommand } from "../api/osaClient";
import { Button, Card } from "../design-system";

export default function CommandConsole() {
    const [command, setCommand] = useState("");
    const [busy, setBusy] = useState(false);
    const [history, setHistory] = useState([]);

    async function execute() {
        const prompt = command.trim();

        if (!prompt || busy) {
            return;
        }

        setBusy(true);

        try {
            const result = await sendCommand(prompt, "EMP-001");

            setHistory((current) => [
                {
                    command: prompt,
                    status: result.status,
                    task_id: result.task_id,
                    stage: result.stage,
                    response: result.response,
                },
                ...current,
            ]);

            setCommand("");
        } catch (error) {
            setHistory((current) => [
                {
                    command: prompt,
                    status: "FAILED",
                    response: error.message,
                },
                ...current,
            ]);
        } finally {
            setBusy(false);
        }
    }

    return (
        <Card title="AI5R Command Console">
            <input
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="Enter command..."
            />

            <Button onClick={execute} disabled={busy}>
                {busy ? "Submitting..." : "Execute"}
            </Button>

            <hr />

            {history.map((item, index) => (
                <div key={index}>
                    <strong>{item.command}</strong>

                    <br />

                    Status:
                    {" "}
                    {item.status}

                    <br />

                    Stage:
                    {" "}
                    {item.stage || "-"}

                    <br />

                    Task:
                    {" "}
                    {item.task_id || "-"}

                    <br />

                    Response:
                    {" "}
                    {item.response}

                    <hr />
                </div>
            ))}
        </Card>
    );
}
