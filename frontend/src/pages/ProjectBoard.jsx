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
    <div className="page">
      <Link className="back-link" to="/projects">&larr; all projects</Link>
      <h1 style={{ margin: "10px 0 24px" }}>Board</h1>

      {dashboard && (
        <div className="dash-strip">
          <div className="dash-stat">
            <span className="dash-stat-label">By status</span>
            <span className="dash-stat-value" style={{ fontSize: 14, fontWeight: 500 }}>
              {Object.entries(dashboard.task_counts_by_status).map(([s, c]) => `${s.replace("_", " ")}: ${c}`).join("   ·   ") || "none"}
            </span>
          </div>
          {isStaff && (
            <div className="dash-stat">
              <span className="dash-stat-label">Hours logged</span>
              <span className="dash-stat-value">{dashboard.total_hours}</span>
            </div>
          )}
        </div>
      )}

      {isStaff && (
        <form onSubmit={createTask} className="card form-row" style={{ marginBottom: 24 }}>
          <input style={{ flex: 1 }} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="New task title" />
          <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
            <option value="internal">internal</option>
            <option value="client_visible">client-visible</option>
          </select>
          <button className="btn-primary" type="submit">Add task</button>
        </form>
      )}

      <div className="board">
        {STATUSES.map((status) => (
          <div key={status} className="column">
            <div className="column-title">{status.replace("_", " ")}</div>
            {tasks.filter((t) => t.status === status).map((t) => (
              <Link key={t.id} to={`/projects/${projectId}/tasks/${t.id}`} className="task-card">
                {t.title}
                <div>
                  <span className={`tag ${t.visibility === "internal" ? "tag-internal" : "tag-visible"}`}>
                    {t.visibility === "internal" ? "internal" : "client-visible"}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
