import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

const STATUSES = ["todo", "in_progress", "review", "done"];

export default function ProjectBoard() {
  const { projectId } = useParams();
  const [tasks, setTasks] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [title, setTitle] = useState("");
  const [visibility, setVisibility] = useState("internal");
  const { session } = useAuth();
  const isStaff = session.role !== "client_user";

  async function load() {
    const [t, d] = await Promise.all([
      api.get(`/projects/${projectId}/tasks`),
      api.get(`/projects/${projectId}/dashboard`),
    ]);
    setTasks(t.data);
    setDashboard(d.data);
  }

  useEffect(() => { load(); }, [projectId]);

  async function createTask(e) {
    e.preventDefault();
    await api.post(`/projects/${projectId}/tasks`, { title, visibility });
    setTitle("");
    load();
  }

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "sans-serif" }}>
      <Link to="/projects">&larr; all projects</Link>
      <h1>Board</h1>

      {dashboard && (
        <div style={{ background: "#f4f4f4", padding: 12, marginBottom: 20, borderRadius: 6 }}>
          <strong>Dashboard</strong>
          <div>Tasks by status: {Object.entries(dashboard.task_counts_by_status).map(([s, c]) => `${s}: ${c}`).join("  ·  ") || "none"}</div>
          {isStaff && <div>Total hours logged: {dashboard.total_hours}</div>}
        </div>
      )}

      {isStaff && (
        <form onSubmit={createTask} style={{ marginBottom: 20 }}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="New task title" />
          <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
            <option value="internal">internal</option>
            <option value="client_visible">client-visible</option>
          </select>
          <button type="submit">Add task</button>
        </form>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {STATUSES.map((status) => (
          <div key={status}>
            <h4 style={{ textTransform: "capitalize" }}>{status.replace("_", " ")}</h4>
            {tasks.filter((t) => t.status === status).map((t) => (
              <Link
                key={t.id}
                to={`/projects/${projectId}/tasks/${t.id}`}
                style={{
                  display: "block", padding: 8, marginBottom: 8, background: "#fff",
                  border: "1px solid #ddd", borderRadius: 4, textDecoration: "none", color: "#111",
                }}
              >
                {t.title}
                <div style={{ fontSize: 11, color: t.visibility === "internal" ? "#a33" : "#3a3" }}>
                  {t.visibility === "internal" ? "internal" : "client-visible"}
                </div>
              </Link>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
