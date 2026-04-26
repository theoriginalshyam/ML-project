import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";

export default function ProtectedRoutes() {
  const [verified, setVerified] = useState(null);
  const token = (localStorage.getItem("token") || "").replace(/"/g, "");

  useEffect(() => {
    if (!token || token.length < 4) {
      setVerified(false);
      return;
    }

    fetch("http://localhost:5000/v1/auth/verify-token", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({}),
    })
      .then((response) => {
        setVerified(response.ok);
      })
      .catch(() => setVerified(false));
  }, [token]);

  if (verified === null) {
    return <div className="empty-state">Verifying session...</div>;
  }

  return verified ? <Outlet /> : <Navigate to="/" replace />;
}
