/** Author: Dev2 | Date: 2026-07-16 | Purpose: Shared mock-auth contracts compatible with the future API. */
export type Role = 'Admin' | 'IT-Head' | 'Engineer' | 'Executive' | 'User'

export interface AuthUser {
  id: string
  login: string
  fullName: string
  role: Role
  position: string
  initials: string
}

export interface LoginPayload {
  login: string
  password: string
}
