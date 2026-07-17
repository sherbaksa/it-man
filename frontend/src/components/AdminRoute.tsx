/** Author: Dev2 | Date: 2026-07-16 | Purpose: Enforce Admin-only access when the route is opened directly. */
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function AdminRoute() {
  const user = useAuthStore((state) => state.user)
  return user?.role === 'Admin' ? <Outlet /> : <Navigate to="/" replace />
}
