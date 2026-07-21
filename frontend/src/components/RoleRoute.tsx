/** Author: Dev2 | Date: 2026-07-21 | Purpose: Mirror backend role restrictions for protected frontend routes. */
import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import type { Role } from '../types/auth'

interface RoleRouteProps {
  allowedRoles: Role[]
  children: ReactNode
}

export default function RoleRoute({ allowedRoles, children }: RoleRouteProps) {
  const user = useAuthStore((state) => state.user)
  return user && allowedRoles.includes(user.role) ? children : <Navigate to="/" replace />
}
