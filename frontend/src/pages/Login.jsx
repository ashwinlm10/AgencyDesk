import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("admin@pixelpine.com");
  const [password, setPassword] = useState("password123");
  const [memberships, setMemberships] = useState(null);
  const [identityToken, setIdentityToken] = useState(null);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const nav = useNavigate();

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (data.memberships.length === 1) {
        await selectAgency(data.identity_token, data.memberships[0].membership_id);
      } else {
        setIdentityToken(data.identity_token);
        setMemberships(data.memberships);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    }
  }

  async function selectAgency(idToken, membershipId) {
    const { data } = await api.post("/auth/select-agency", {
      identity_token: idToken,
      membership_id: membershipId,
    });
    login(data);
    nav("/projects");
  }

  if (memberships) {
    return (
      <div className="page-narrow">
        <h1>Which agency?</h1>
        <p className="hint" style={{ marginTop: 0, marginBottom: 20 }}>
          This account belongs to more than one agency — pick which one to sign into.
        </p>
        {memberships.map((m) => (
          <button
            key={m.membership_id}
            className="agency-pick-btn"
            onClick={() => selectAgency(identityToken, m.membership_id)}
          >
            <strong>{m.agency_name}</strong>
            <div className="role-pill" style={{ display: "inline-block", marginTop: 6 }}>
              {m.role.replace("_", " ")}
            </div>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="page-narrow">
      <h1 style={{ fontSize: 30, marginBottom: 28 }}>AgencyDesk</h1>
      <form onSubmit={handleLogin} className="card">
        <input
          style={{ display: "block", width: "100%", marginBottom: 10 }}
          value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email"
        />
        <input
          style={{ display: "block", width: "100%", marginBottom: 14 }}
          type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password"
        />
        <button className="btn-primary" style={{ width: "100%" }} type="submit">Log in</button>
      </form>
      {error && <p className="error-text">{error}</p>}
      <p className="hint">
        Seeded accounts (password: password123)<br />
        admin@pixelpine.com · member@pixelpine.com · admin@mapledigital.com<br />
        shared@client.com (belongs to both agencies)
      </p>
    </div>
  );
}
