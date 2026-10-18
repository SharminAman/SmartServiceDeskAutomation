import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, setUnauthorized } from "./api";
import { GuideFile } from "./components/GuideFile";
import { Shell } from "./layout/Shell";
import { Admin } from "./pages/Admin";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { Requests } from "./pages/Requests";
import type { User } from "./types";

export function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    setUnauthorized(() => setUser(null));
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  if (user === undefined) return <div className="splash">Request Desk</div>;

  return (
    <>
    <GuideFile />
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login onSuccess={setUser} />} />
      <Route element={user ? <Shell user={user} onLogout={() => setUser(null)} /> : <Navigate to="/login" replace />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
    </Routes>
    </>
  );
}
