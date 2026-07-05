/**
 * Notifications
 * -------------
 * Renders `notifications` from agent state — currently populated by
 * detect_life_event_node (see backend/agent/nodes.py), shape:
 *   { type, title, body, read? }
 */
export default function Notifications({ notifications, onDismiss }) {
  return (
    <section>
      <div className="section-eyebrow">Notifications</div>
      <div className="card">
        {(!notifications || notifications.length === 0) && (
          <p className="empty-state">You're all caught up.</p>
        )}

        {notifications && notifications.length > 0 && (
          <div className="notif-list">
            {notifications.map((n, i) => (
              <div key={i} className={`notif-item ${n.read ? "" : "unread"}`} onClick={() => onDismiss?.(i)}>
                <span className="notif-dot" />
                <div className="notif-body">
                  <div className="notif-title">{n.title}</div>
                  <div className="notif-text">{n.body}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
