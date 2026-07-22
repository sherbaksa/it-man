/** Author: Dev2 | Date: 2026-07-22 | Purpose: Real backend authentication with memory-only access tokens. */
import { create } from 'zustand'
import {
  apiClient,
  getApiErrorMessage,
  registerAccessTokenListener,
  registerAuthenticationFailureHandler,
  refreshApiAccessToken,
  setApiAccessToken,
} from '../api/client'
import type { components } from '../api/types'
import type { AuthUser, LoginPayload, Role } from '../types/auth'

type LoginResponse = components['schemas']['LoginResponse']
type UserPublic = components['schemas']['UserPublic']

let initializationRequest: Promise<void> | null = null

const rolePositions: Record<Role, string> = {
  Admin: 'Администратор платформы',
  'IT-Head': 'Руководитель IT-отдела',
  Engineer: 'IT-инженер',
  Executive: 'Руководство',
  User: 'Сотрудник',
}

function getInitials(fullName: string) {
  return fullName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'П'
}

function toAuthUser(user: UserPublic): AuthUser {
  return {
    id: user.id,
    fullName: user.full_name,
    role: user.role,
    position: rolePositions[user.role],
    initials: getInitials(user.full_name),
  }
}

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  isInitialized: boolean
  initialize: () => Promise<void>
  login: (payload: LoginPayload) => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  isInitialized: false,
  initialize: async () => {
    if (get().isInitialized) return
    if (!initializationRequest) {
      initializationRequest = (async () => {
        try {
          await refreshApiAccessToken()
          const { data: user } = await apiClient.get<UserPublic>('/api/auth/me')
          set({ user: toAuthUser(user), isAuthenticated: true })
        } catch {
          setApiAccessToken(null)
          set({ user: null, accessToken: null, isAuthenticated: false })
        } finally {
          set({ isInitialized: true })
        }
      })().finally(() => {
        initializationRequest = null
      })
    }
    return initializationRequest
  },
  login: async (payload) => {
    set({ isLoading: true })
    try {
      const { data } = await apiClient.post<LoginResponse>('/api/auth/login', payload)
      setApiAccessToken(data.access_token)
      set({
        user: toAuthUser(data.user),
        accessToken: data.access_token,
        isAuthenticated: true,
        isInitialized: true,
      })
    } catch (error) {
      throw new Error(getApiErrorMessage(error, 'Не удалось выполнить вход'), { cause: error })
    } finally {
      set({ isLoading: false })
    }
  },
  logout: async () => {
    await apiClient.post('/api/auth/logout').catch(() => undefined)
    setApiAccessToken(null)
    set({ user: null, accessToken: null, isAuthenticated: false, isInitialized: true })
  },
}))

registerAccessTokenListener((accessToken) => useAuthStore.setState({ accessToken }))
registerAuthenticationFailureHandler(() => {
  useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false, isInitialized: true })
})
