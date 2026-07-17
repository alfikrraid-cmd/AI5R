import { useState } from "react";
import { Button, Card } from "../design-system";

function CommandInput({ onExecute }) {
    const [prompt, setPrompt] = useState("");

    function handleSubmit(event) {
        event.preventDefault();

        if (!prompt.trim()) {
            return;
        }

        onExecute(prompt);
        setPrompt("");
    }

    return (
        <Card title="Command">
            <form onSubmit={handleSubmit}>
                <textarea
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    placeholder="Type command for OSA..."
                    rows="5"
                />

                <Button type="submit">
                    Execute
                </Button>
            </form>
        </Card>
    );
}

export default CommandInput;
