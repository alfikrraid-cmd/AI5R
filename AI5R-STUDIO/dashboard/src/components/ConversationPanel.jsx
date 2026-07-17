import { Card } from "../design-system";

function ConversationPanel({ messages }) {
    return (
        <Card title="Conversation">
            <div className="conversation-panel">
                {messages.map((message, index) => (
                    <div key={index} className={`message ${message.sender.toLowerCase()}`}>
                        <strong>{message.sender}</strong>
                        <p>{message.text}</p>
                    </div>
                ))}
            </div>
        </Card>
    );
}

export default ConversationPanel;
