function ConversationPanel({ messages }) {
    return (
        <div className="card">
            <h2>Conversation</h2>

            <div className="conversation-panel">
                {messages.map((message, index) => (
                    <div key={index} className={`message ${message.sender.toLowerCase()}`}>
                        <strong>{message.sender}</strong>
                        <p>{message.text}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default ConversationPanel;
