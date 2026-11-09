// Dedicated routed sign-in boundary: renders the credential frame without booting the workspace coordinator first.

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getCurrentSession, login } from "../api";
import LoginView from "../views/LoginView";

export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;

    getCurrentSession()
      .then(() => {
        if (active) navigate("/", { replace: true });
      })
      .catch(() => {
        // No active session: keep the credential frame available.
      });

    return () => {
      active = false;
    };
  }, [navigate]);

  async function submitLogin(email, password) {
    setSubmitting(true);
    setError(null);

    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <LoginView
      error={error}
      submitting={submitting}
      onLogin={submitLogin}
      onCancel={() => navigate("/about")}
    />
  );
}
