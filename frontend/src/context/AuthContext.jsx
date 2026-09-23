import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    const raw = localStorage.getItem("session");
    return raw ? JSON.parse(raw) : null;
  });

  function login(data) {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("session", JSON.stringify(data));
    setSession(data);
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("session");
    setSession(null);
  }

  return (
    <AuthContext.Provider value={{ session, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
