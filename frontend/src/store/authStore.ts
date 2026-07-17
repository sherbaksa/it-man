/** Author: Dev2 | Date: 2026-07-16 | Purpose: Central in-memory authentication state. */
import { create } from 'zustand'
import { mockLogin } from '../api/mocks'
import type { AuthUser, LoginPayload } from '../types/auth'

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (payload: LoginPayload) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: async (payload) => {
    set({ isLoading: true })
    try {
      const user = await mockLogin(payload)
      set({ user, accessToken: 'mock-access-token', isAuthenticated: true })
    } finally {
      set({ isLoading: false })
    }
  },
  logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
}))
