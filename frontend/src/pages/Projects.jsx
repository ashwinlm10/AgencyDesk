import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState([]);
  const [newProjectName, setNewProjectName] = useState("");
  const [newClientId, setNewClientId] = useState("");
  const [newClientName, setNewClientName] = useState("");
  const { session, logout } = useAuth();

  const isStaff = session.role !== "client_user";

  async function load() {
    const { data } = await api.get("/projects");
    setProjects(data);
    if (isStaff) {
      const c = await api.get("/clients");
      setClients(c.data);
    }
  }

  useEffect(() => { load(); }, []);

  async function createClient(e) {
    e.preventDefault();
    await api.post("/clients", { name: newClientName });
    setNewClientName("");
    load();
  }

  async function createProject(e) {
    e.preventDefault();
    if (!newClientId) return;
    await api.post("/projects", { name: newProjectName, client_id: newClientId });
    setNewProjectName("");
    load();
  }

  return (
    <div style={{ maxWidth: 700, margin: "40px auto", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>{session.agency_name}</h1>
        <div>
          <span style={{ marginRight: 12, color: "#666" }}>{session.role.replace("_", " ")}</span>
          <button onClick={logout}>Log out</button>
        </div>
      </div>

      <h2>Projects</h2>
      {projects.length === 0 && <p>No projects visible to you yet.</p>}
      <ul>
        {projects.map((p) => (
          <li key={p.id}>
            <Link to={`/projects/${p.id}`}>{p.name}</Link>
          </li>
        ))}
      </ul>

      {isStaff && (
        <>
          <h3>New client</h3>
          <form onSubmit={createClient} style={{ marginBottom: 20 }}>
            <input value={newClientName} onChange={(e) => setNewClientName(e.target.value)} placeholder="Client name" />
            <button type="submit">Add client</button>
          </form>

          <h3>New project</h3>
          <form onSubmit={createProject}>
            <select value={newClientId} onChange={(e) => setNewClientId(e.target.value)}>
              <option value="">-- choose client --</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="Project name" />
            <button type="submit">Create project</button>
          </form>
        </>
      )}
    </div>
  );
}
