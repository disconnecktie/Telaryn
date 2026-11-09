// Presents the sole local sign-in boundary without offering public registration.
import "./LoginView.css";
import { useState } from "react";
import { AtlasBrand } from "../components/AtlasBrand";

function LoginView({ error, submitting, onLogin, onCancel }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function submit(event) {
    event.preventDefault();
    onLogin(email, password);
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <AtlasBrand className="login-brand" />
        <p className="detail-label">Private Workspace</p>
        <h1>Welcome back.</h1>
        <p className="login-context">Sign in to continue to your Telaryn workspace.</p>
        <label>
          Email
          <input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          Password
          <input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <p className="login-error" role="alert">{error}</p>}
        <div className="login-actions">
          <button type="button" className="login-cancel-button" onClick={onCancel} disabled={submitting}>Back to Telaryn</button>
          <button type="submit" className="ai-button" disabled={submitting}>
            {submitting ? "Signing In..." : "Sign In"}
          </button>
        </div>
      </form>
    </main>
  );
}

export default LoginView;
