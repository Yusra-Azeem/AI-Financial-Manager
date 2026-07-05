/**
 * api.js
 * ------
 * Thin wrapper around the backend's REST surface (see backend/routes.py):
 *   GET  /customer/:id            -> raw customer profile
 *   GET  /agent/state/:id         -> full proactive agent state bundle
 *                                    (behavior, prediction, life_event,
 *                                    opportunity, recommendation_card,
 *                                    notifications, timeline-able events)
 *   POST /agent/loan-offer        -> { customer_id } -> loan_offer
 *   POST /agent/negotiate         -> { customer_id, message, round } -> counter-offer + reply
 *
 * Vite's dev server proxies /customer and /agent to http://localhost:8000
 * (see vite.config.js), so these calls can just use relative paths.
 *
 * --- Running without a backend ---------------------------------------
 * Set VITE_USE_MOCK=true (in a .env file, or `VITE_USE_MOCK=true npm run dev`)
 * to serve everything from mockData.js instead of hitting the network.
 * No other file needs to change — App.jsx / components don't know or care
 * which mode they're in.
 */
import { MOCK_AGENT_STATE, mockNegotiationReply } from "./mockData";

// In dev, leave VITE_API_BASE_URL unset and let vite.config.js's proxy
// forward /agent and /customer to localhost:8000. In production there is
// no dev server proxy, so this must point at the deployed backend, e.g.
// VITE_API_BASE_URL=https://api.yourdomain.com (set at build time).
const BASE = import.meta.env.VITE_API_BASE_URL || "";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
const MOCK_DELAY_MS = 400; // small delay so loading states are visible in demos

function mockDelay(value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), MOCK_DELAY_MS));
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export function getCustomer(customerId) {
  if (USE_MOCK) return mockDelay(MOCK_AGENT_STATE.customer_bundle);
  return request(`/customer/${customerId}`);
}

export function getAgentState(customerId) {
  if (USE_MOCK) return mockDelay(MOCK_AGENT_STATE);
  return request(`/agent/state/${customerId}`);
}

export function requestLoanOffer(customerId) {
  if (USE_MOCK) return mockDelay(MOCK_AGENT_STATE.recommendation_card.offer);
  return request(`/agent/loan-offer`, {
    method: "POST",
    body: JSON.stringify({ customer_id: customerId }),
  });
}

export function sendNegotiationMessage(customerId, message, round) {
  if (USE_MOCK) return mockDelay(mockNegotiationReply(message, round));
  return request(`/agent/negotiate`, {
    method: "POST",
    body: JSON.stringify({ customer_id: customerId, message, round }),
  });
}

