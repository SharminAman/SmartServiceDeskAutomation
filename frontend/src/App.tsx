import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, setUnauthorized } from "./api";
import { Shell } from "./layout/Shell";
import { Admin } from "./pages/Admin";
import { Dashboard } from "./pages/Dashboard";
import { Guide } from "./pages/Guide";
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
    <Routes>
      <Route path="/guide" element={<Guide signedIn={Boolean(user)} />} />
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login onSuccess={setUser} />} />
      {user ? (
        <Route element={<Shell user={user} onLogout={() => setUser(null)} />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/requests" element={<Requests />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
      ) : (
        <>
          <Route path="/" element={<Guide signedIn={false} />} />
          <Route path="/requests" element={<Navigate to="/login" replace />} />
          <Route path="/admin" element={<Navigate to="/login" replace />} />
        </>
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
