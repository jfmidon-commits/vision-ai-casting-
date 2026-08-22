import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  login: (user: User, token: string) => void;
  logout: () => void;
}

const setAuthCookie = (authenticated: boolean) => {
  if (typeof document === "undefined") return;
  if (authenticated) {
    document.cookie = "auth-storage=1; Path=/; Max-Age=2592000; SameSite=Lax; Secure";
  } else {
    document.cookie = "auth-storage=; Path=/; Max-Age=0; SameSite=Lax; Secure";
  }
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => set({ token }),
      login: (user, token) => {
        setAuthCookie(true);
        set({ user, token, isAuthenticated: true });
      },
      logout: () => {
        setAuthCookie(false);
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: "auth-storage",
    }
  )
);
