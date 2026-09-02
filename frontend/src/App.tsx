/** Author: Dev2 | Date: 2026-07-22 | Purpose: Declare protected routes and restore the F02 auth session. */
import { Navigate, Route, Routes } from 'react-router-dom'
import { lazy, Suspense, useEffect } from 'react'
import AppLayout from './components/AppLayout'
import AdminRoute from './components/AdminRoute'
import PrivateRoute from './components/PrivateRoute'
import RoleRoute from './components/RoleRoute'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Placeholder from './pages/Placeholder'
import type { Role } from './types/auth'
import { useAuthStore } from './store/authStore'

const Inventory = lazy(() => import('./pages/Inventory'))
const Tickets = lazy(() => import('./pages/Tickets'))
const Orders = lazy(() => import('./pages/Orders'))
const Monitoring = lazy(() => import('./pages/Monitoring'))
const Admin = lazy(() => import('./pages/Admin'))
const pageFallback = <div className="page-container"><div className="page-loading">Загрузка раздела…</div></div>
const staffRoles: Role[] = ['Admin', 'IT-Head', 'Engineer', 'Executive']
const technicalRoles: Role[] = ['Admin', 'IT-Head', 'Engineer']

const placeholders = [
  ['/maintenance', 'Обслуживание', 'Плановые и текущие работы с оборудованием', technicalRoles],
  ['/reports', 'Отчёты', 'Аналитика и выгрузки по работе IT-отдела', ['Admin', 'IT-Head', 'Executive'] satisfies Role[]],
] as const

export default function App() {
  const initialize = useAuthStore((state) => state.initialize)
  const isInitialized = useAuthStore((state) => state.isInitialized)

  useEffect(() => {
    void initialize()
  }, [initialize])

  if (!isInitialized) return <div className="page-loading">Проверка сессии…</div>

  return <Routes><Route path="/login" element={<Login />} /><Route element={<PrivateRoute />}><Route element={<AppLayout />}><Route index element={<Dashboard />} /><Route path="/inventory" element={<RoleRoute allowedRoles={technicalRoles}><Suspense fallback={pageFallback}><Inventory /></Suspense></RoleRoute>} /><Route path="/tickets" element={<RoleRoute allowedRoles={technicalRoles}><Suspense fallback={pageFallback}><Tickets /></Suspense></RoleRoute>} /><Route path="/orders" element={<RoleRoute allowedRoles={staffRoles}><Suspense fallback={pageFallback}><Orders /></Suspense></RoleRoute>} /><Route path="/monitoring" element={<RoleRoute allowedRoles={technicalRoles}><Suspense fallback={pageFallback}><Monitoring /></Suspense></RoleRoute>} /><Route element={<AdminRoute />}><Route path="/admin" element={<Suspense fallback={pageFallback}><Admin /></Suspense>} /></Route>{placeholders.map(([path, title, description, roles]) => <Route key={path} path={path} element={<RoleRoute allowedRoles={[...roles]}><Placeholder title={title} description={description} /></RoleRoute>} />)}</Route></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes>
}
