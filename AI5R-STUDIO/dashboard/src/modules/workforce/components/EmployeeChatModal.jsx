import { useEffect, useRef, useState } from "react";
import Badge from "../../../design-system/components/Badge";
import Modal from "../../../design-system/components/Modal";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";
import { sendWorkforceChat } from "../../../api/workforceClient";

export default function EmployeeChatModal({
  isOpen,
  onClose,
  employee,
  conversations = {},
  onUpdateConversation,
}) {
  const [inputMessage, setInputMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const employeeId = employee?.employee_id;
  const conversation = (employeeId && conversations[employeeId]) || {
    conversationId: null,
    messages: [],
  };

  useEffect(() => {
    if (isOpen) {
      setInputMessage("");
      setError(null);
      setSending(false);
    }
  }, [isOpen, employeeId]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
    }
  }, [conversation.messages, isOpen]);

  if (!isOpen || !employee) return null;

  async function handleSend(e) {
    e?.preventDefault?.();
    const trimmed = inputMessage.trim();
    if (!trimmed || sending) return;

    setError(null);
    setSending(true);

    const optimisticUserMessage = {
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...conversation.messages, optimisticUserMessage];
    onUpdateConversation?.(employeeId, {
      conversationId: conversation.conversationId,
      messages: updatedMessages,
    });
    setInputMessage("");

    try {
      const result = await sendWorkforceChat({
        employeeId: employee.employee_id,
        message: trimmed,
        conversationId: conversation.conversationId,
      });

      const serverMessages = result.messages || [
        ...updatedMessages,
        {
          role: "assistant",
          content: result.response,
          timestamp: new Date().toISOString(),
        },
      ];

      onUpdateConversation?.(employeeId, {
        conversationId: result.conversation_id || conversation.conversationId,
        messages: serverMessages,
      });
    } catch (err) {
      setError(err.message || "Failed to send message to employee");
    } finally {
      setSending(false);
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Chat with ${employee.employee_name}`}
    >
      <div
        data-testid="employee-chat-modal"
        style={{ display: "flex", flexDirection: "column", gap: spacing.sm, minHeight: 380 }}
      >
        {/* Employee Subheader */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            paddingBottom: spacing.xs,
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <div>
            <span style={{ fontSize: typography.size.sm, fontWeight: typography.weight.bold, color: colors.text }}>
              {employee.role || employee.title}
            </span>
            <span style={{ fontSize: typography.size.xs, color: colors.textMuted, marginLeft: spacing.xs }}>
              (<code>{employee.position_id}</code>)
            </span>
          </div>
          <Badge variant={employee.status === "AVAILABLE" ? "success" : "purple"}>
            {employee.status}
          </Badge>
        </div>

        {/* Non-Approval Safety Banner */}
        <div
          style={{
            background: "rgba(59, 130, 246, 0.1)",
            border: `1px solid ${colors.info}`,
            borderRadius: spacing.xs,
            padding: "6px 10px",
            fontSize: typography.size.xs,
            color: colors.info,
          }}
        >
          ℹ️ Direct employee instruction thread. Chat messages cannot trigger production deployments or bypass the Human Chief Approval Gate.
        </div>

        {/* Error Banner */}
        {error ? (
          <div
            data-testid="chat-error-banner"
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${colors.danger}`,
              borderRadius: spacing.xs,
              padding: spacing.xs,
              color: colors.danger,
              fontSize: typography.size.xs,
            }}
          >
            {error}
          </div>
        ) : null}

        {/* Messages Area */}
        <div
          data-testid="chat-messages-container"
          style={{
            flex: 1,
            maxHeight: 240,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: spacing.xs,
            padding: spacing.xs,
            background: colors.background,
            borderRadius: spacing.xs,
            border: `1px solid ${colors.border}`,
          }}
        >
          {conversation.messages.length === 0 ? (
            <div
              data-testid="chat-empty-state"
              style={{
                margin: "auto",
                color: colors.textMuted,
                fontSize: typography.size.sm,
                textAlign: "center",
                padding: spacing.md,
              }}
            >
              No messages yet. Send an instruction to start.
            </div>
          ) : (
            conversation.messages.map((msg, idx) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={idx}
                  data-testid={`chat-message-${msg.role}`}
                  style={{
                    alignSelf: isUser ? "flex-end" : "flex-start",
                    maxWidth: "80%",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: typography.weight.bold,
                      color: isUser ? colors.info : colors.purple,
                      marginBottom: 2,
                    }}
                  >
                    {isUser ? "Chief" : employee.employee_name}
                  </span>
                  <div
                    style={{
                      background: isUser ? colors.info : colors.panel,
                      color: colors.text,
                      padding: "6px 12px",
                      borderRadius: spacing.xs,
                      fontSize: typography.size.sm,
                      border: `1px solid ${isUser ? colors.info : colors.border}`,
                      wordBreak: "break-word",
                    }}
                  >
                    {msg.content}
                  </div>
                </div>
              );
            })
          )}
          {sending ? (
            <div
              data-testid="chat-sending-indicator"
              style={{
                alignSelf: "flex-start",
                fontSize: typography.size.xs,
                color: colors.textMuted,
                fontStyle: "italic",
                padding: 4,
              }}
            >
              {employee.employee_name} is processing instruction...
            </div>
          ) : null}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form
          data-testid="chat-form"
          onSubmit={handleSend}
          style={{ display: "flex", gap: spacing.xs, alignItems: "center" }}
        >
          <input
            data-testid="chat-message-input"
            type="text"
            placeholder={`Message ${employee.employee_name}...`}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={sending}
            style={{
              flex: 1,
              background: colors.background,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.sm}px`,
              fontSize: typography.size.sm,
            }}
          />
          <button
            type="submit"
            data-testid="chat-send-button"
            disabled={sending || !inputMessage.trim()}
            style={{
              background: (sending || !inputMessage.trim()) ? colors.textMuted : colors.info,
              color: colors.text,
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              cursor: (sending || !inputMessage.trim()) ? "not-allowed" : "pointer",
            }}
          >
            {sending ? "Sending..." : "Send"}
          </button>
        </form>
      </div>
    </Modal>
  );
}
