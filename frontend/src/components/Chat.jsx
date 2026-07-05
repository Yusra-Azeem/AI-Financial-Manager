import { useState, useRef, useEffect } from "react";

/**
 * Chat
 * ----
 * General conversation AND the negotiation UI live in the same panel,
 * since backend/agent/graph.py routes any `pending_user_message` through
 * either the negotiate loop or the chat node depending on state
 * (see agent/router.py:route_entry). This component doesn't need to know
 * which one fired — it just renders `messages` and calls `onSend`.
 *
 * Props:
 *   messages: [{ role: "user" | "assistant", content }]
 *   onSend(text): Promise<void>
 *   negotiationStatus?: "not_started" | "in_progress" | "accepted" | "rejected" | "max_rounds_reached"
 */
export default function Chat({ messages, onSend, negotiationStatus, sending }) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const disabled = negotiationStatus === "accepted" || negotiationStatus === "max_rounds_reached";

  async function handleSubmit(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || disabled) return;
    setDraft("");
    await onSend(text);
  }

  return (
    <section>
      <div className="section-eyebrow">Talk to your relationship manager</div>
      <div className="card chat-panel">
        <div className="chat-messages" ref={scrollRef}>
          {(!messages || messages.length === 0) && (
            <p className="empty-state">Ask a question, or discuss the terms on an offer above.</p>
          )}
          {messages?.map((m, i) => (
            <div key={i} className={`chat-bubble ${m.role}`}>
              {m.content}
            </div>
          ))}
          {sending && <div className="chat-bubble assistant pending">Thinking…</div>}
        </div>

        <form className="chat-input-row" onSubmit={handleSubmit}>
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={disabled ? "This offer is now closed" : "Type a message…"}
            disabled={disabled || sending}
            aria-label="Message"
          />
          <button className="btn btn-primary" type="submit" disabled={disabled || sending || !draft.trim()}>
            Send
          </button>
        </form>
      </div>
    </section>
  );
}
