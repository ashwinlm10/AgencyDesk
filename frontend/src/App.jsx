import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Projects from "./pages/Projects";
import ProjectBoard from "./pages/ProjectBoard";
import TaskDetail from "./pages/TaskDetail";

function RequireAuth({ children }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  return children;
}

function Inner() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/projects" element={<RequireAuth><Projects /></RequireAuth>} />
      <Route path="/projects/:projectId" element={<RequireAuth><ProjectBoard /></RequireAuth>} />
      <Route path="/projects/:projectId/tasks/:taskId" element={<RequireAuth><TaskDetail /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Inner />
      </BrowserRouter>
    </AuthProvider>
  );
}
