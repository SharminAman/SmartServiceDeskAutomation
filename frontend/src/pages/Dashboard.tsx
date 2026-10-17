import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { DashboardData } from "../types";

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DashboardData>("/api/dashboard")
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <div className="page"><p className="banner error">{error}</p></div>;
  if (!data) return <div className="page">Opening the desk…</div>;

  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="kicker">{today}</div>
          <h1>The queue, already read.</h1>
        </div>
        <div className="actions">
          <Link className="btn" to="/requests">
            Open requests
          </Link>
          <Link className="btn primary" to="/requests?new=1">
            New request
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
          {data.review_reasons.length === 0 ? <p className="hint">Nothing is waiting.</p> : null}
          {data.review_reasons.map((item) => (
            <div className="reason" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.count}</strong>
            </div>
          ))}
          <h2 style={{ marginTop: 22 }}>Rules in force</h2>
          <div className="rule-rail">
            {data.rules.map((rule, index) => (
              <div key={rule.category}>
                <i>{index + 1}</i>
                <div>
                  <strong>{rule.category}</strong>
                  <small>{rule.enabled ? rule.keywords.join(" · ") : "Turned off"}</small>
                </div>
              </div>
            ))}
          </div>
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
