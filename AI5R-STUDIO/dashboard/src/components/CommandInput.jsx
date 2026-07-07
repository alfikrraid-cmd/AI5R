import { useState } from "react";

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
        <div className="card">
            <h2>Command</h2>

            <form onSubmit={handleSubmit}>
                <textarea
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    placeholder="Type command for OSA..."
                    rows="5"
                />

                <button type="submit">
                    Execute
                </button>
            </form>
        </div>
    );
}

export default CommandInput;
