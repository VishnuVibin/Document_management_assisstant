import { useState } from "react";
import { askQuestion } from "../services/api";
import SourceList from "./SourceList";

function Chat() {

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {

    if (!question.trim()) {
      return;
    }

    const userQuestion = question;

    setMessages((prev) => [
      ...prev,
      {
        type: "user",
        text: userQuestion,
      },
    ]);

    setQuestion("");
    setLoading(true);

    try {

      const response = await askQuestion(
        userQuestion
      );

      setMessages((prev) => [
        ...prev,
        {
          type: "ai",
          text:
            response.answer ||
            response.response ||
            "No answer received.",
          sources:
            response.sources || [],
        },
      ]);

    } catch (error) {

      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          type: "ai",
          text: "Sorry, something went wrong.",
          sources: [],
        },
      ]);

    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div className="chat">

      <h2>Ask AI</h2>

      <div className="chat-window">

        {messages.length === 0 && (
          <div className="empty-chat">
            Ask a question about your documents.
          </div>
        )}

        {messages.map((message, index) => (

          <div
            key={index}
            className={
              message.type === "user"
                ? "message user-message"
                : "message ai-message"
            }
          >

            <strong>
              {message.type === "user"
                ? "You"
                : "AI"}
            </strong>

            <p>{message.text}</p>

            {message.type === "ai" && (
              <SourceList
                sources={message.sources}
              />
            )}

          </div>

        ))}

        {loading && (
          <div className="message ai-message">
            <strong>AI</strong>
            <p>Thinking...</p>
          </div>
        )}

      </div>

      <div className="chat-input">

        <textarea
          value={question}
          onChange={(e) =>
            setQuestion(e.target.value)
          }
          onKeyDown={handleKeyDown}
          placeholder="Ask something about your documents..."
        />

        <button
          onClick={handleAsk}
          disabled={loading}
        >
          {loading ? "..." : "Ask"}
        </button>

      </div>

    </div>
  );
}

export default Chat;