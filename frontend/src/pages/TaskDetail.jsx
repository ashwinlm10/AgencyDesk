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
    <div className="page">
      <Link className="back-link" to={`/projects/${projectId}`}>&larr; back to board</Link>
      <h1 style={{ margin: "10px 0 6px" }}>{task.title}</h1>
      {task.description && <p style={{ color: "var(--text-muted)" }}>{task.description}</p>}

      <div className="card-flat" style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 14 }}>
        <span style={{ color: "var(--text-muted)", fontSize: 13 }}>Status</span>
        <strong style={{ textTransform: "capitalize" }}>{task.status.replace("_", " ")}</strong>
        {isStaff && (
          <select value={task.status} onChange={(e) => updateStatus(e.target.value)} style={{ marginLeft: "auto" }}>
            {["todo", "in_progress", "review", "done"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
          </select>
        )}
      </div>

      <div className="section-heading">Comments</div>
      <div className="card-flat">
        {comments.length === 0 && <p style={{ color: "var(--text-faint)", margin: 0, fontSize: 13 }}>No comments yet.</p>}
        {comments.map((c) => (
          <div key={c.id} className="comment">
            <span className={`tag ${c.visibility === "internal" ? "tag-internal" : "tag-visible"}`}>
              {c.visibility === "internal" ? "internal" : "client-visible"}
            </span>
            <div className="comment-body">{c.body}</div>
          </div>
        ))}
      </div>
      <form onSubmit={postComment} className="form-row" style={{ marginTop: 10 }}>
        <input style={{ flex: 1 }} value={commentBody} onChange={(e) => setCommentBody(e.target.value)} placeholder="Write a comment" />
        {isStaff && (
          <select value={commentVisibility} onChange={(e) => setCommentVisibility(e.target.value)}>
            <option value="internal">internal</option>
            <option value="client_visible">client-visible</option>
          </select>
        )}
        <button className="btn-primary" type="submit">Post</button>
      </form>

      {isStaff && (
        <>
          <div className="section-heading">Time entries</div>
          <div className="card-flat">
            {timeEntries.length === 0 && <p style={{ color: "var(--text-faint)", margin: 0, fontSize: 13 }}>No time logged yet.</p>}
            {timeEntries.map((t) => (
              <div key={t.id} className="comment" style={{ fontSize: 14 }}>{t.duration_minutes} min — {t.entry_date}</div>
            ))}
          </div>
          <form onSubmit={logTime} className="form-row" style={{ marginTop: 10 }}>
            <input type="number" value={duration} onChange={(e) => setDuration(e.target.value)} style={{ width: 90 }} />
            <span style={{ alignSelf: "center", color: "var(--text-muted)", fontSize: 13 }}>minutes</span>
            <button className="btn-primary" type="submit">Log time</button>
          </form>
        </>
      )}

      <div className="section-heading">Files</div>
      <div className="card-flat">
        {files.length === 0 && <p style={{ color: "var(--text-faint)", margin: 0, fontSize: 13 }}>No files yet.</p>}
        {files.map((f) => (
          <div key={f.id} className="file-row">
            <span>{f.filename}</span>
            <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className="file-status">{f.approval_status.replace("_", " ")}</span>
              {session.role === "client_user" && f.visibility === "client_visible" && (
                <>
                  <button className="btn-ghost" onClick={() => setApproval(f.id, "approved")}>Approve</button>
                  <button className="btn-ghost" onClick={() => setApproval(f.id, "needs_changes")}>Needs changes</button>
                </>
              )}
            </span>
          </div>
        ))}
      </div>
      {isStaff && <input type="file" onChange={uploadFile} style={{ marginTop: 10 }} />}
    </div>
  );
}
