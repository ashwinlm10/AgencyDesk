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
    <div className="page">
      <div className="topbar">
        <h1>{session.agency_name}</h1>
        <div className="topbar-right">
          <span className="role-pill">{session.role.replace("_", " ")}</span>
          <button className="btn-ghost" onClick={logout}>Log out</button>
        </div>
      </div>

      <div className="section-heading" style={{ marginTop: 0 }}>Projects</div>
      {projects.length === 0 && <p className="hint" style={{ marginTop: 0 }}>No projects visible to you yet.</p>}
      <ul className="project-list">
        {projects.map((p) => (
          <li key={p.id}>
            <Link className="project-row" to={`/projects/${p.id}`}>{p.name}</Link>
          </li>
        ))}
      </ul>

      {isStaff && (
        <>
          <div className="section-heading">New client</div>
          <form onSubmit={createClient} className="card form-row">
            <input style={{ flex: 1 }} value={newClientName} onChange={(e) => setNewClientName(e.target.value)} placeholder="Client name" />
            <button className="btn-primary" type="submit">Add client</button>
          </form>

          <div className="section-heading">New project</div>
          <form onSubmit={createProject} className="card form-row">
            <select value={newClientId} onChange={(e) => setNewClientId(e.target.value)}>
              <option value="">— choose client —</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input style={{ flex: 1 }} value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="Project name" />
            <button className="btn-primary" type="submit">Create project</button>
          </form>
        </>
      )}
    </div>
  );
}
