import { NavLink, Outlet } from "react-router-dom";
import { useState } from "react";
import { api } from "../api";
import type { User } from "../types";

export function Shell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [open, setOpen] = useState(false);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    onLogout();
  }

  return (
    <div className="shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="mark">
            <i>
              <span />
              <span />
              <span />
            </i>
          </div>
          <div>
            <strong>Request Desk</strong>
            <em>Service triage</em>
          </div>
        </div>
        <nav className="nav">
          <NavLink to="/" end onClick={() => setOpen(false)}>
            Desk
          </NavLink>
          <NavLink to="/requests" onClick={() => setOpen(false)}>
            Requests
          </NavLink>
          <NavLink to="/guide" onClick={() => setOpen(false)}>
            Guide
          </NavLink>
          <NavLink to="/admin" onClick={() => setOpen(false)}>
            Rules
          </NavLink>
        </nav>
        <div className="side-foot">
          <p>Signed in as {user.username}. Request text stays in this database. Nothing is sent to an external service.</p>
          <button className="btn lime" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="mobile-bar">
          <button className="btn small menu-btn" onClick={() => setOpen((value) => !value)}>
            Menu
          </button>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
