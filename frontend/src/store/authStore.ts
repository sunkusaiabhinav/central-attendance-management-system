import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserProfile } from "@/types";

// ─────────────────────────────────────────────────────────────────────────────
// Zustand Auth Store — persists token and user to localStorage
// ─────────────────────────────────────────────────────────────────────────────

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;

  setToken: (token: string) => void;
  setUser: (user: UserProfile) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      setToken: (token) => set({ token, isAuthenticated: true }),

      setUser: (user) => set({ user }),

      logout: () =>
        set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: "attendance-auth", // localStorage key
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
