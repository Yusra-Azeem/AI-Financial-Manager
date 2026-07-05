import { useEffect, useState, useCallback } from "react";
import Dashboard from "./components/Dashboard";
import RecommendationCards from "./components/RecommendationCards";
import Timeline from "./components/Timeline";
import Notifications from "./components/Notifications";
import Chat from "./components/Chat";
import { getAgentState, requestLoanOffer, sendNegotiationMessage } from "./api";

// Swap for real auth/session lookup — kept simple for the demo seed data.
const CUSTOMER_ID = import.meta.env.VITE_DEMO_CUSTOMER_ID || "1";

export default function App() {
  const [state, setState] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [offerLoading, setOfferLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [negotiationRound, setNegotiationRound] = useState(0);

  const loadState = useCallback(async () => {
    try {
      const data = await getAgentState(CUSTOMER_ID);
      setState(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    }
  }, []);

  useEffect(() => {
    loadState();
  }, [loadState]);

  async function handleRequestOffer() {
    setOfferLoading(true);
    try {
      const offer = await requestLoanOffer(CUSTOMER_ID);
      setState((prev) => ({
        ...prev,
        recommendation_card: { ...(prev?.recommendation_card || {}), offer },
      }));
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setOfferLoading(false);
    }
  }

  function handleNegotiate() {
    // Scrolls focus to chat by nudging a message in — the customer types
    // their counter, which the backend routes to the negotiate node.
    document.querySelector(".chat-panel input")?.focus();
  }

  async function handleSend(text) {
    setSending(true);
    const nextRound = negotiationRound + 1;
    setState((prev) => ({
      ...prev,
      messages: [...(prev?.messages || []), { role: "user", content: text }],
    }));
    try {
      const result = await sendNegotiationMessage(CUSTOMER_ID, text, nextRound);
      setNegotiationRound(nextRound);
      setState((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), { role: "assistant", content: result.reply }],
        recommendation_card: result.offer
          ? { ...(prev?.recommendation_card || {}), offer: result.offer }
          : prev?.recommendation_card,
        negotiation_status: result.negotiation_status,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        messages: [
          ...(prev?.messages || []),
          { role: "assistant", content: "Sorry — I couldn't reach the server just now. Please try again." },
        ],
      }));
    } finally {
      setSending(false);
    }
  }

  if (loadError) {
    return (
      <div className="app-shell">
        <header className="app-header">
          <div className="brand">
            Sahayak<span>.</span>
          </div>
        </header>
        <div className="app-body">
          <p className="empty-state">Couldn't load your account right now: {loadError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          Sahayak<span>.</span>
        </div>
        <div className="customer-name">{state?.customer_bundle?.name || "Loading…"}</div>
      </header>

      <div className="app-body">
        <div className="column">
          <Dashboard
            behaviorAnalysis={state?.behavior_analysis}
            spendingPrediction={state?.spending_prediction}
            customer={state?.customer_bundle}
          />
          <RecommendationCards
            card={state?.recommendation_card}
            onRequestOffer={handleRequestOffer}
            onNegotiate={handleNegotiate}
            loading={offerLoading}
          />
          <Timeline entries={buildTimelineEntries(state)} />
        </div>

        <div className="column">
          <Notifications notifications={state?.notifications} />
          <Chat
            messages={state?.messages}
            onSend={handleSend}
            negotiationStatus={state?.negotiation_status}
            sending={sending}
          />
        </div>
      </div>
    </div>
  );
}

// Flattens whatever the backend gives us (life_event + negotiation_history)
// into a single chronological list the Timeline component can render.
function buildTimelineEntries(state) {
  if (!state) return [];
  const entries = [];

  if (state.life_event) {
    entries.push({
      date: state.life_event.detected_at || "Recently",
      title: `Life event: ${state.life_event.type}`,
      description: state.life_event.evidence,
      flagged: true,
    });
  }

  (state.negotiation_history || []).forEach((round) => {
    entries.push({
      date: `Round ${round.round}`,
      title: round.accepted ? "Offer accepted" : "Terms discussed",
      description: round.user_message,
      flagged: false,
    });
  });

  return entries;
}
