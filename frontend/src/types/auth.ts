/** Author: Dev2 | Date: 2026-07-22 | Purpose: UI auth model derived from the generated backend contract. */
import type { components } from '../api/types'

export type Role = components['schemas']['UserRole']

export interface AuthUser {
  id: string
  fullName: string
  role: Role
  position: string
  initials: string
}

export type LoginPayload = components['schemas']['LoginRequest']
