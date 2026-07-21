/** Author: Dev2 | Date: 2026-07-16 | Purpose: F09 RTL smoke coverage for Login, Inventory and Tickets. */
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../store/authStore'
import RoleRoute from '../components/RoleRoute'
import Dashboard from '../pages/Dashboard'
import Inventory from '../pages/Inventory'
import Login from '../pages/Login'
import Tickets from '../pages/Tickets'
import { downloadBlob } from '../utils/downloadBlob'

const engineer = { id: 'mock-engineer', login: 'engineer', fullName: 'Инженер Тестовый', role: 'Engineer' as const, position: 'IT-инженер', initials: 'ИТ' }
const requester = { id: 'mock-user', login: 'user', fullName: 'Сотрудник Тестовый', role: 'User' as const, position: 'Сотрудник', initials: 'СТ' }

beforeEach(() => useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false, isLoading: false }))

describe('critical frontend pages', () => {
  it('logs in with the default demonstration account', async () => {
    render(<MemoryRouter initialEntries={['/login']}><Routes><Route path="/login" element={<Login />} /><Route path="/" element={<div>Главная после входа</div>} /></Routes></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Вход в систему' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }))
    expect(await screen.findByText('Главная после входа', {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('loads the inventory table from the replaceable adapter', async () => {
    render(<Inventory />)
    expect(screen.getByRole('heading', { name: 'Инвентаризация' })).toBeInTheDocument()
    expect(await screen.findByText('INV-00231', {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('loads the ticket queue for an authenticated engineer', async () => {
    useAuthStore.setState({ user: engineer, accessToken: 'mock-access-token', isAuthenticated: true })
    render(<MemoryRouter><Tickets /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Заявки' })).toBeInTheDocument()
    expect(await screen.findByText('INC-1250', {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('redirects a requester dashboard to their own tickets', async () => {
    useAuthStore.setState({ user: requester, accessToken: 'mock-access-token', isAuthenticated: true })
    render(<MemoryRouter initialEntries={['/']}><Routes><Route path="/" element={<Dashboard />} /><Route path="/tickets" element={<div>Личные заявки</div>} /></Routes></MemoryRouter>)
    expect(await screen.findByText('Личные заявки')).toBeInTheDocument()
    expect(screen.queryByText('Активы в работе')).not.toBeInTheDocument()
  })

  it('shows a requester only their own tickets', async () => {
    useAuthStore.setState({ user: requester, accessToken: 'mock-access-token', isAuthenticated: true })
    render(<MemoryRouter><Tickets /></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Мои заявки' }, { timeout: 2000 })).toBeInTheDocument()
    expect(await screen.findByText('INC-1250', {}, { timeout: 2000 })).toBeInTheDocument()
    expect(screen.queryByText('INC-1249')).not.toBeInTheDocument()
  })

  it('blocks direct access to a route outside the requester role', async () => {
    useAuthStore.setState({ user: requester, accessToken: 'mock-access-token', isAuthenticated: true })
    render(<MemoryRouter initialEntries={['/inventory']}><Routes><Route path="/" element={<div>Безопасная страница</div>} /><Route path="/inventory" element={<RoleRoute allowedRoles={['Admin', 'IT-Head', 'Engineer']}><div>Служебная инвентаризация</div></RoleRoute>} /></Routes></MemoryRouter>)
    expect(await screen.findByText('Безопасная страница')).toBeInTheDocument()
    expect(screen.queryByText('Служебная инвентаризация')).not.toBeInTheDocument()
  })

  it('downloads a generated file without navigating the current page', () => {
    vi.useFakeTimers()
    const createObjectURL = vi.fn(() => 'blob:test-report')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL })

    downloadBlob(new Blob(['report']), 'assets-test.xlsx')

    const link = document.querySelector<HTMLAnchorElement>('a[download="assets-test.xlsx"]')
    expect(link).toHaveAttribute('href', 'blob:test-report')
    expect(link).toHaveAttribute('target', '_blank')
    expect(click).toHaveBeenCalledOnce()
    vi.runAllTimers()
    expect(document.querySelector('a[download="assets-test.xlsx"]')).not.toBeInTheDocument()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test-report')
    vi.useRealTimers()
  })
})
