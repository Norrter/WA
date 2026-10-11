// Текущий пользователь и вход/выход

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { auth, users } from "../api";
import { clearTokens, hasSession, onSessionExpired, saveTokens } from "../api/client";
import type { User } from "../api/types";

interface AuthApi {
  user: User | null;
  // true, пока при запуске проверяем сохранённую сессию
  checking: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthApi | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(hasSession());

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    window.location.hash = "/";
  }, []);

  useEffect(() => onSessionExpired(() => setUser(null)), []);

  useEffect(() => {
    if (!hasSession()) return;

    auth
      .me()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setChecking(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    saveTokens(await auth.login(email, password));
    setUser(await auth.me());
  }, []);

  const register = useCallback(
    async (email: string, username: string, password: string) => {
      await users.register({ email, username, password });
      await login(email, password);
    },
    [login],
  );

  return (
    <AuthContext.Provider value={{ user, checking, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthApi {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth должен вызываться внутри AuthProvider");
  }

  return context;
}

// Пользователь точно вошёл (для экранов внутри приложения)
export function useUser(): User {
  const { user } = useAuth();

  if (!user) {
    throw new Error("Нет пользователя");
  }

  return user;
}
