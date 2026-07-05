/**
 * mockData.js
 * -----------
 * Stand-in for the /agent/state/:id response so the UI can run and be
 * demoed with zero backend. Shape must match backend/agent/state.py's
 * AgentState (see graph.py -> run_proactive_cycle()).
 *
 * Only used when VITE_USE_MOCK=true (see api.js).
 */
export const MOCK_AGENT_STATE = {
  customer_bundle: {
    name: "Ananya Rao",
  },
  behavior_analysis: {
    avg_monthly_spend: 42500,
    savings_rate: 18,
  },
  spending_prediction: {
    next_month_forecast: 46200,
    cashflow_buffer: 12800,
  },
  life_event: {
    type: "business_startup",
    evidence: "Recurring supplier payments and a new GST-linked account began three weeks ago.",
    confidence: 0.82,
    detected_at: "18 Jun 2026",
  },
  opportunity: {
    type: "business_loan",
    product: "Sahayak Business Growth Loan",
    rationale: "Recent supplier payments suggest working-capital needs for a new venture.",
  },
  recommendation_card: {
    type: "business_loan",
    product: "Sahayak Business Growth Loan",
    pitch:
      "It looks like you've recently started a new venture — congratulations. Based on your current cash flow, a working-capital line could help smooth out supplier payments while the business finds its rhythm. Would you like to see what terms you'd qualify for?",
    offer: {
      amount: 500000,
      interest_rate: 11.5,
      emi: 16560,
      tenure_months: 36,
    },
    explanation:
      "This offer gives you ₹5,00,000 at 11.5% interest, working out to an EMI of ₹16,560 over 36 months. Let me know if these terms work for you, or if you'd like to negotiate.",
  },
  notifications: [
    {
      type: "life_event",
      title: "New life event: business_startup",
      body: "We noticed activity suggesting a new business venture.",
      read: false,
    },
    {
      type: "info",
      title: "Statement ready",
      body: "Your June account statement is now available.",
      read: true,
    },
  ],
  negotiation_history: [],
  negotiation_status: "not_started",
  messages: [
    {
      role: "assistant",
      content:
        "Hi Ananya — it looks like you've recently started a new venture. I've put together a offer that might help with working capital, whenever you'd like to take a look.",
    },
  ],
};

export function mockNegotiationReply(message, round) {
  const accepted = /deal|agree|okay|works|sounds good/i.test(message);
  const counterRate = Math.max(10.5, 11.5 - round * 0.3);
  const counterEmi = Math.round(16560 * (counterRate / 11.5));

  return {
    reply: accepted
      ? `Great — let's lock that in. Final terms: ₹5,00,000 at ${counterRate.toFixed(1)}%, EMI ₹${counterEmi.toLocaleString(
          "en-IN"
        )} over 36 months. I'll send over the agreement for e-sign.`
      : `I hear you. Here's what I can do: ${counterRate.toFixed(1)}% instead of the original rate, bringing your EMI down to ₹${counterEmi.toLocaleString(
          "en-IN"
        )}. Let me know if that works.`,
    offer: {
      amount: 500000,
      interest_rate: Number(counterRate.toFixed(1)),
      emi: counterEmi,
      tenure_months: 36,
    },
    negotiation_status: accepted ? "accepted" : round >= 3 ? "max_rounds_reached" : "in_progress",
  };
}
