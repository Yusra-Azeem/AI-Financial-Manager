/**
 * Dashboard
 * ---------
 * The passbook "front page": a handful of at-a-glance numbers pulled from
 * the agent state bundle (behavior_analysis + spending_prediction).
 * Purely presentational — all numbers come in as props.
 */
export default function Dashboard({ behaviorAnalysis, spendingPrediction, customer }) {
  const stats = [
    {
      label: "Avg. monthly spend",
      value: formatCurrency(behaviorAnalysis?.avg_monthly_spend),
    },
    {
      label: "Savings rate",
      value: behaviorAnalysis?.savings_rate != null ? `${behaviorAnalysis.savings_rate}%` : "—",
    },
    {
      label: "Next month forecast",
      value: formatCurrency(spendingPrediction?.next_month_forecast),
      accent: true,
    },
    {
      label: "Cashflow buffer",
      value: formatCurrency(spendingPrediction?.cashflow_buffer),
    },
  ];

  return (
    <section>
      <div className="section-eyebrow">Account snapshot</div>
      <div className="card">
        <div className="summary-grid">
          {stats.map((s) => (
            <div key={s.label} className={`summary-stat ${s.accent ? "accent" : ""}`}>
              <div className="label">{s.label}</div>
              <div className="value mono">{s.value}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function formatCurrency(value) {
  if (value == null) return "—";
  return `₹${Number(value).toLocaleString("en-IN")}`;
}
