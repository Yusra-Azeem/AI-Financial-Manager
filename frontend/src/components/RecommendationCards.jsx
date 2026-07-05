/**
 * RecommendationCards
 * -------------------
 * Renders `recommendation_card` from the agent state — the merged output of
 * detect_opportunity + check_policy (see backend/agent/nodes.py). Shape:
 *   {
 *     type, product, pitch,
 *     offer: { amount, interest_rate, emi, tenure_months },
 *     explanation
 *   }
 *
 * "See offer" triggers requestLoanOffer if no offer is priced yet.
 * "Negotiate" hands control to the Chat panel via onNegotiate.
 */
export default function RecommendationCards({ card, onRequestOffer, onNegotiate, loading }) {
  return (
    <section>
      <div className="section-eyebrow">Recommended for you</div>

      {!card && (
        <div className="card">
          <p className="empty-state">No new recommendations right now — check back after your next few transactions.</p>
        </div>
      )}

      {card && (
        <div className="rec-card">
          <div className="rec-kicker">{card.type?.replace(/_/g, " ") || "Opportunity"}</div>
          <h3>{card.product || "Tailored offer"}</h3>
          <p>{card.pitch}</p>

          {card.offer && (
            <>
              <div className="rec-terms">
                <Term label="Amount" value={formatCurrency(card.offer.amount)} />
                <Term label="Rate" value={card.offer.interest_rate != null ? `${card.offer.interest_rate}%` : "—"} />
                <Term label="EMI" value={formatCurrency(card.offer.emi)} />
                <Term label="Tenure" value={card.offer.tenure_months ? `${card.offer.tenure_months} mo` : "—"} />
              </div>
              {card.explanation && <p>{card.explanation}</p>}
            </>
          )}

          <div className="rec-actions">
            {!card.offer && (
              <button className="btn btn-primary" onClick={onRequestOffer} disabled={loading}>
                {loading ? "Pricing offer…" : "See offer"}
              </button>
            )}
            {card.offer && (
              <button className="btn btn-primary" onClick={onNegotiate}>
                Discuss terms
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function Term({ label, value }) {
  return (
    <div className="rec-term">
      <div className="term-label">{label}</div>
      <div className="term-value mono">{value}</div>
    </div>
  );
}

function formatCurrency(value) {
  if (value == null) return "—";
  return `₹${Number(value).toLocaleString("en-IN")}`;
}
