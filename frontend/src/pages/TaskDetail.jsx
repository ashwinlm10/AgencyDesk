import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function TaskDetail() {
  const { projectId, taskId } = useParams();
  const [task, setTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [timeEntries, setTimeEntries] = useState([]);
  const [files, setFiles] = useState([]);
  const [commentBody, setCommentBody] = useState("");
  const [commentVisibility, setCommentVisibility] = useState("internal");
  const [duration, setDuration] = useState(30);
  const { session } = useAuth();
  const isStaff = session.role !== "client_user";

  async function load() {
    const [t, c, f] = await Promise.all([
      api.get(`/projects/${projectId}/tasks/${taskId}`),
      api.get(`/projects/${projectId}/tasks/${taskId}/comments`),
      api.get(`/projects/${projectId}/tasks/${taskId}/files`),
    ]);
    setTask(t.data);
    setComments(c.data);
    setFiles(f.data);
    if (isStaff) {
      const te = await api.get(`/projects/${projectId}/tasks/${taskId}/time-entries`);
      setTimeEntries(te.data);
    }
  }

  useEffect(() => { load(); }, [projectId, taskId]);

  async function updateStatus(status) {
    await api.patch(`/projects/${projectId}/tasks/${taskId}`, { status });
    load();
  }

  async function postComment(e) {
    e.preventDefault();
    await api.post(`/projects/${projectId}/tasks/${taskId}/comments`, {
      body: commentBody, visibility: commentVisibility,
    });
    setCommentBody("");
    load();
  }

  async function logTime(e) {
    e.preventDefault();
    await api.post(`/projects/${projectId}/tasks/${taskId}/time-entries`, {
      duration_minutes: Number(duration), entry_date: new Date().toISOString().slice(0, 10),
    });
    load();
  }

  async function uploadFile(e) {
    const f = e.target.files[0];
    if (!f) return;
    const form = new FormData();
    form.append("upload", f);
    form.append("visibility", "internal");
    await api.post(`/projects/${projectId}/tasks/${taskId}/files`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    load();
  }

  async function setApproval(fileId, status) {
    await api.patch(`/projects/${projectId}/tasks/${taskId}/files/${fileId}/approval`, { approval_status: status });
    load();
  }

  if (!task) return null;

  return (
    <div style={{ maxWidth: 700, margin: "40px auto", fontFamily: "sans-serif" }}>
      <Link to={`/projects/${projectId}`}>&larr; back to board</Link>
      <h1>{task.title}</h1>
      <p>{task.description}</p>
      <p>
        Status: <strong>{task.status}</strong>
        {isStaff && (
          <select value={task.status} onChange={(e) => updateStatus(e.target.value)} style={{ marginLeft: 8 }}>
            {["todo", "in_progress", "review", "done"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        )}
      </p>

      <h3>Comments</h3>
      {comments.map((c) => (
        <div key={c.id} style={{ borderBottom: "1px solid #eee", padding: "6px 0" }}>
          <div style={{ fontSize: 11, color: c.visibility === "internal" ? "#a33" : "#3a3" }}>
            {c.visibility === "internal" ? "internal" : "client-visible"}
          </div>
          {c.body}
        </div>
      ))}
      <form onSubmit={postComment} style={{ marginTop: 10 }}>
        <input value={commentBody} onChange={(e) => setCommentBody(e.target.value)} placeholder="Write a comment" style={{ width: "60%" }} />
        {isStaff && (
          <select value={commentVisibility} onChange={(e) => setCommentVisibility(e.target.value)}>
            <option value="internal">internal</option>
            <option value="client_visible">client-visible</option>
          </select>
        )}
        <button type="submit">Post</button>
      </form>

      {isStaff && (
        <>
          <h3>Time entries</h3>
          {timeEntries.map((t) => <div key={t.id}>{t.duration_minutes} min — {t.entry_date}</div>)}
          <form onSubmit={logTime}>
            <input type="number" value={duration} onChange={(e) => setDuration(e.target.value)} style={{ width: 80 }} /> minutes
            <button type="submit">Log time</button>
          </form>
        </>
      )}

      <h3>Files</h3>
      {files.map((f) => (
        <div key={f.id} style={{ marginBottom: 6 }}>
          {f.filename} — <em>{f.approval_status}</em>
          {session.role === "client_user" && f.visibility === "client_visible" && (
            <span style={{ marginLeft: 8 }}>
              <button onClick={() => setApproval(f.id, "approved")}>Approve</button>{" "}
              <button onClick={() => setApproval(f.id, "needs_changes")}>Needs changes</button>
            </span>
          )}
        </div>
      ))}
      {isStaff && <input type="file" onChange={uploadFile} />}
    </div>
  );
}
