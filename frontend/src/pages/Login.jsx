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
        // Multiple agencies for this email -- let them pick which context to
        // operate in (this is the "one person, two agencies" flow).
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
      <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
        <h2>Which agency?</h2>
        <p>This account belongs to more than one agency — pick which one to sign into.</p>
        {memberships.map((m) => (
          <button
            key={m.membership_id}
            style={{ display: "block", width: "100%", padding: 12, marginBottom: 8 }}
            onClick={() => selectAgency(identityToken, m.membership_id)}
          >
            {m.agency_name} — {m.role.replace("_", " ")}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
      <h1>AgencyDesk</h1>
      <form onSubmit={handleLogin}>
        <input
          style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }}
          value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email"
        />
        <input
          style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }}
          type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password"
        />
        <button style={{ padding: "8px 16px" }} type="submit">Log in</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <p style={{ fontSize: 12, color: "#666", marginTop: 20 }}>
        Seeded accounts (password: password123): admin@pixelpine.com, member@pixelpine.com,
        admin@mapledigital.com, shared@client.com (belongs to both agencies)
      </p>
    </div>
  );
}
