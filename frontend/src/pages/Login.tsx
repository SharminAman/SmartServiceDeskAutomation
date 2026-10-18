import { FormEvent, useState } from "react";
import { api } from "../api";
import { GuideFile } from "../components/GuideFile";
import type { User } from "../types";

export function Login({ onSuccess }: { onSuccess: (user: User) => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await api<User>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onSuccess(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <section className="login-story">
        <div>
          <div className="mark">
            <i>
              <span />
              <span />
              <span />
            </i>
            Request Desk
          </div>
          <h1>
            Every request, <em>read by a rule.</em>
          </h1>
          <p className="lede">
            Upload a spreadsheet or add one request. The desk checks the fields, chooses a category, writes an
            acknowledgement, and marks anything a person should see.
          </p>
          <div className="tickets" aria-hidden="true">
            <article className="ticket">
              <b className="pill warn">Needs a person</b>
              <b>REQ-004</b>
              <span>System integration · finance workflow</span>
            </article>
            <article className="ticket">
              <b className="pill good">Ready</b>
              <b>REQ-005</b>
              <span>Content and guidance · onboarding guide</span>
            </article>
            <article className="ticket">
              <b className="pill">High</b>
              <b>REQ-006</b>
              <span>Process automation · overdue reminders</span>
            </article>
          </div>
          <GuideFile />
        </div>
        <p className="lede">Synthetic requests only. One admin. Rules live in PostgreSQL.</p>
      </section>
      <section className="login-panel">
        <form className="card" onSubmit={submit}>
          <div className="kicker">Admin desk</div>
          <h2>Sign in</h2>
          <p className="hint">The queue and the rules are both behind this login.</p>
          <label className="field">
            <span>Username</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="banner error">{error}</p> : null}
          <button className="btn primary wide" disabled={busy}>
            {busy ? "Signing in…" : "Enter the desk"}
          </button>
          <p className="demo-note">
            Local demo account <code>admin</code> · <code>RequestDesk!2026</code>
          </p>
        </form>
      </section>
    </main>
  );
}
