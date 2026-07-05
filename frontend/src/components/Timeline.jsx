/**
 * Timeline
 * --------
 * Chronological record of what the agent has noticed and done for this
 * customer: detected life events + negotiation rounds. Each entry gets a
 * small circular "stamp" (numbered like a passbook entry) — flagged
 * entries (a detected life event) get the brick-colored stamp.
 *
 * Expects `entries`: [{ date, title, description, flagged }]
 * sorted oldest -> newest (rendered oldest first, top to bottom).
 */
export default function Timeline({ entries }) {
  return (
    <section>
      <div className="section-eyebrow">Timeline</div>
      <div className="card">
        {(!entries || entries.length === 0) && (
          <p className="empty-state">Nothing recorded yet — this fills in as the agent reviews activity.</p>
        )}

        {entries && entries.length > 0 && (
          <ol className="timeline" style={{ listStyle: "none", margin: 0 }}>
            {entries.map((entry, i) => (
              <li key={i} className={`timeline-entry ${entry.flagged ? "is-flagged" : ""}`}>
                <span className="timeline-stamp">{String(i + 1).padStart(2, "0")}</span>
                <div className="timeline-date">{entry.date}</div>
                <h4>{entry.title}</h4>
                {entry.description && <p>{entry.description}</p>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
