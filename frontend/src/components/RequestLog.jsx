import { useEffect, useState } from "react";
import { clearLog, subscribeLog } from "../lib/api.js";
import StatusBadge from "./StatusBadge.jsx";

export default function RequestLog() {
  const [entries, setEntries] = useState([]);
  useEffect(() => subscribeLog(setEntries), []);

  return (
    <section className="log" aria-labelledby="log-title">
      <div className="log-head">
        <h2 id="log-title">Request log</h2>
        {entries.length > 0 && (
          <button className="btn btn-small btn-quiet" onClick={clearLog}>
            Clear
          </button>
        )}
      </div>
      {entries.length === 0 ? (
        <p className="log-empty">Every call this page makes to the API appears here, newest first.</p>
      ) : (
        <ol className="log-list" aria-live="polite">
          {entries.map((e) => (
            <li key={e.id} className="log-item">
              <div className="log-line">
                <span className={`method m-${e.method.toLowerCase()}`}>{e.method}</span>
                <code className="log-path">{e.path}</code>
              </div>
              <div className="log-meta">
                <StatusBadge status={e.status} />
                {e.label && <span className="log-label">{e.label}</span>}
                <span className="log-time">{e.at.toLocaleTimeString()}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
