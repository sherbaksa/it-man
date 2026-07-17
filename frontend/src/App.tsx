/** Author: Dev2 | Date: 2026-07-16 | Purpose: Declare application routes for session F01. */
import { Navigate, Route, Routes } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import AppLayout from './components/AppLayout'
import AdminRoute from './components/AdminRoute'
import PrivateRoute from './components/PrivateRoute'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Placeholder from './pages/Placeholder'

const Inventory = lazy(() => import('./pages/Inventory'))
const Tickets = lazy(() => import('./pages/Tickets'))
const Orders = lazy(() => import('./pages/Orders'))
const Monitoring = lazy(() => import('./pages/Monitoring'))
const Admin = lazy(() => import('./pages/Admin'))
const pageFallback = <div className="page-container"><div className="page-loading">Загрузка раздела…</div></div>

const placeholders = [
  ['/maintenance', 'Обслуживание', 'Плановые и текущие работы с оборудованием'],
  ['/reports', 'Отчёты', 'Аналитика и выгрузки по работе IT-отдела'],
] as const

export default function App() {
  return <Routes><Route path="/login" element={<Login />} /><Route element={<PrivateRoute />}><Route element={<AppLayout />}><Route index element={<Dashboard />} /><Route path="/inventory" element={<Suspense fallback={pageFallback}><Inventory /></Suspense>} /><Route path="/tickets" element={<Suspense fallback={pageFallback}><Tickets /></Suspense>} /><Route path="/orders" element={<Suspense fallback={pageFallback}><Orders /></Suspense>} /><Route path="/monitoring" element={<Suspense fallback={pageFallback}><Monitoring /></Suspense>} /><Route element={<AdminRoute />}><Route path="/admin" element={<Suspense fallback={pageFallback}><Admin /></Suspense>} /></Route>{placeholders.map(([path, title, description]) => <Route key={path} path={path} element={<Placeholder title={title} description={description} />} />)}</Route></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes>
}
