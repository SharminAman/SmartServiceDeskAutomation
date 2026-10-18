import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { GuideFile } from "../components/GuideFile";
import type { DashboardData } from "../types";

function reasonTitle(label: string): string {
  const phrase = label.match(/sensitive phrase:\s*(.+)/i) || label.match(/mentions "([^"]+)"/i);
  if (phrase) return `Sensitive: ${phrase[1].replace(/[."]+$/g, "").trim()}`;
  const text = label.toLowerCase();
  if (text.includes("high priority") || text.includes("priority is high")) return "High priority";
  if (text.includes("completed")) return "Already completed";
  if (text.includes("missing")) return "Missing or invalid information";
  if (text.includes("no category") || text.includes("did not match")) return "No category matched";
  if (text.includes("looks like") || text.includes("category")) return "Category does not match";
  return label;
}

function reasonLine(label: string): string {
  const phrase = label.match(/sensitive phrase:\s*(.+)/i);
  if (phrase) {
    return `The summary mentions "${phrase[1].replace(/[."]+$/g, "").trim()}", which this desk treats as sensitive.`;
  }
  const quoted = label.match(/mentions "([^"]+)"/i);
  if (quoted) return `The summary mentions "${quoted[1]}", which this desk treats as sensitive.`;
  const missing = label.match(/missing or invalid:\s*(.+)/i);
  if (missing) return `${missing[1].replace(/\.+$/g, "").trim()} is missing or not valid.`;
  const text = label.toLowerCase();
  if (text.includes("high priority") || text.includes("priority is high")) {
    return "The priority on the request is High.";
  }
  if (text.includes("completed")) {
    return "The request is already marked Completed, so a new acknowledgement may not be appropriate.";
  }
  if (text.includes("no category") || text.includes("did not match any category")) {
    return "The summary did not match a category rule, so no category could be chosen.";
  }
  const stripped = label.replace(/^A person needs to look at this because\s+/i, "");
  const sentence = stripped.charAt(0).toUpperCase() + stripped.slice(1);
  return sentence.endsWith(".") ? sentence : `${sentence}.`;
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [reasonIndex, setReasonIndex] = useState(0);

  useEffect(() => {
    api<DashboardData>("/api/dashboard")
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <div className="page"><p className="banner error">{error}</p></div>;
  if (!data) return <div className="page">Opening the desk…</div>;

  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  const chosenReason = data.review_reasons[Math.min(reasonIndex, Math.max(0, data.review_reasons.length - 1))];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="kicker">{today}</div>
          <h1>Request queue</h1>
        </div>
        <div className="actions">
          <GuideFile />
          <Link className="btn primary" to="/requests">
            Open requests
          </Link>
        </div>
      </header>

      <section className="stats">
        <Link className="stat" to="/requests">
          <span className="kicker">On the desk</span>
          <b>{data.total}</b>
          <em>requests stored</em>
        </Link>
        <Link className="stat alert" to="/requests?review=yes">
          <span className="kicker">Needs a person</span>
          <b>{data.needs_review}</b>
          <em>flagged for review</em>
        </Link>
        <Link className="stat" to="/requests?match=yes">
          <span className="kicker">Category agrees</span>
          <b>{data.agreed}</b>
          <em>summary matches the type</em>
        </Link>
        <Link className="stat" to="/requests?missing=yes">
          <span className="kicker">Missing information</span>
          <b>{data.missing}</b>
          <em>incomplete or invalid</em>
        </Link>
      </section>

      <section className="layout">
        <article className="panel">
          <h2>By category</h2>
          {data.by_category.length === 0 ? <p className="hint">No requests yet.</p> : null}
          {data.by_category.map((item) => (
            <div className="bar-row" key={item.label}>
              <span>{item.label}</span>
              <div className="track">
                <span style={{ width: `${Math.max(8, (item.count / Math.max(1, data.total)) * 100)}%` }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          ))}
          <h2 style={{ marginTop: 22 }}>Priority</h2>
          {data.by_priority.map((item) => (
            <div className="bar-row" key={item.label}>
              <span>{item.label}</span>
              <div className="track lime">
                <span style={{ width: `${(item.count / Math.max(1, data.total)) * 100}%` }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          ))}
        </article>
        <article className="panel">
          <h2>Why a person is needed</h2>
          {chosenReason ? (
            <ul className="reason-picks">
              {data.review_reasons.map((item, index) => {
                const open = item === chosenReason;
                return (
                  <li key={item.label}>
                    <button
                      type="button"
                      className={open ? "on" : ""}
                      aria-expanded={open}
                      onClick={() => setReasonIndex(index)}
                    >
                      <span>{reasonTitle(item.label)}</span>
                      <strong>{item.count}</strong>
                    </button>
                    {open ? <p>{reasonLine(item.label)}</p> : null}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="hint">Nothing is waiting for a person.</p>
          )}
          <h2 className="panel-next">Rules in force</h2>
          <ol className="rule-rail">
            {data.rules.map((rule, index) => (
              <li className="rule-item" key={rule.category}>
                <i>{index + 1}</i>
                <div>
                  <strong>{rule.category}</strong>
                  <small>{rule.enabled ? rule.keywords.join(" · ") : "Turned off"}</small>
                </div>
              </li>
            ))}
          </ol>
        </article>
      </section>

      <section className="panel attention">
        <h2>Waiting for a person</h2>
        {data.attention.length === 0 ? <p className="hint">Every stored request is clear.</p> : null}
        {data.attention.map((item) => (
          <Link className="row-link" key={item.id} to={`/requests?review=yes&open=${item.id}`}>
            <b>{item.request_id}</b>
            <div>
              <strong>{item.category}</strong>
              <p>{item.request_summary || "No summary"}</p>
            </div>
            <span className="pill warn">{item.priority || "Unset"}</span>
          </Link>
        ))}
      </section>
    </div>
  );
}
