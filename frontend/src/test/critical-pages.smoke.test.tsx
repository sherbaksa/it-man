/** Author: Dev2 | Date: 2026-07-22 | Purpose: RTL coverage for F02 auth and critical frontend pages. */
import { fireEvent, render, screen } from '@testing-library/react'
import axios, { AxiosError } from 'axios'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../store/authStore'
import { apiClient, setApiAccessToken } from '../api/client'
import RoleRoute from '../components/RoleRoute'
import Dashboard from '../pages/Dashboard'
import Inventory from '../pages/Inventory'
import Login from '../pages/Login'
import Tickets from '../pages/Tickets'
import { downloadBlob } from '../utils/downloadBlob'

const engineer = { id: 'mock-engineer', fullName: 'Инженер Тестовый', role: 'Engineer' as const, position: 'IT-инженер', initials: 'ИТ' }
const requester = { id: 'mock-user', fullName: 'Сотрудник Тестовый', role: 'User' as const, position: 'Сотрудник', initials: 'СТ' }

beforeEach(() => useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false, isLoading: false, isInitialized: true }))

describe('critical frontend pages', () => {
  it('logs in with the real backend contract response', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      data: {
        access_token: 'real-access-token',
        user: { id: 'admin-id', role: 'Admin', full_name: 'Администратор Системы' },
      },
    })
    render(<MemoryRouter initialEntries={['/login']}><Routes><Route path="/login" element={<Login />} /><Route path="/" element={<div>Главная после входа</div>} /></Routes></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Вход в систему' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Логин'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'secret-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }))
    expect(await screen.findByText('Главная после входа', {}, { timeout: 2000 })).toBeInTheDocument()
    expect(post).toHaveBeenCalledWith('/api/auth/login', { login: 'admin', password: 'secret-password' })
    expect(useAuthStore.getState()).toMatchObject({
      accessToken: 'real-access-token',
      isAuthenticated: true,
      user: { id: 'admin-id', role: 'Admin', fullName: 'Администратор Системы' },
    })
  })

  it('shows the backend error for invalid credentials', async () => {
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Неверный логин или пароль' } },
    })
    render(<MemoryRouter initialEntries={['/login']}><Login /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Логин'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }))
    expect(await screen.findByText('Неверный логин или пароль')).toBeInTheDocument()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('refreshes an expired access token and retries the original request once', async () => {
    const originalAdapter = apiClient.defaults.adapter
    const adapter = vi.fn(async (config) => {
      if (adapter.mock.calls.length === 1) {
        throw new AxiosError('Expired token', 'ERR_BAD_REQUEST', config, undefined, {
          data: { detail: 'Токен недействителен или истёк' },
          status: 401,
          statusText: 'Unauthorized',
          headers: {},
          config,
        })
      }
      return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
    })
    apiClient.defaults.adapter = adapter
    vi.spyOn(axios, 'post').mockResolvedValueOnce({ data: { access_token: 'refreshed-access-token' } })

    try {
      const response = await apiClient.get('/api/users')
      expect(response.data).toEqual({ ok: true })
      expect(adapter).toHaveBeenCalledTimes(2)
      expect(adapter.mock.calls[1][0].headers.get('Authorization')).toBe('Bearer refreshed-access-token')
      expect(useAuthStore.getState().accessToken).toBe('refreshed-access-token')
    } finally {
      apiClient.defaults.adapter = originalAdapter
      setApiAccessToken(null)
    }
  })

  it('restores the authenticated profile through refresh and auth me', async () => {
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false, isInitialized: false })
    vi.spyOn(axios, 'post').mockResolvedValueOnce({ data: { access_token: 'restored-access-token' } })
    const get = vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      data: { id: 'engineer-id', role: 'Engineer', full_name: 'Инженер Тестовый' },
    })

    await useAuthStore.getState().initialize()

    expect(get).toHaveBeenCalledWith('/api/auth/me')
    expect(useAuthStore.getState()).toMatchObject({
      accessToken: 'restored-access-token',
      isAuthenticated: true,
      isInitialized: true,
      user: { id: 'engineer-id', role: 'Engineer', fullName: 'Инженер Тестовый' },
    })
  })

  it('loads the inventory table from the replaceable adapter', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url === '/api/equipment-types') {
        return { data: [{ id: 'type-id', name: 'Принтер' }] }
      }
      return {
        data: {
          items: [{
            id: 'asset-id',
            inventory_number: 'INV-00231',
            type: { id: 'type-id', name: 'Принтер' },
            serial_number: 'SN-HPM404-7841',
            model: 'HP LaserJet Pro M404dn',
            purchase_date: '2020-01-15',
            status: 'in_use',
            location: 'Кабинет 205',
            responsible_user: null,
            ip_address: null,
            hostname: 'print-205',
            monitoring_status: null,
            created_at: '2026-07-16T04:00:00Z',
            updated_at: '2026-07-16T04:00:00Z',
          }],
          total: 1,
        },
      }
    })
    render(<Inventory />)
    expect(screen.getByRole('heading', { name: 'Инвентаризация' })).toBeInTheDocument()
    expect(await screen.findByText('INV-00231', {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('loads the ticket queue for an authenticated engineer', async () => {
    useAuthStore.setState({ user: engineer, accessToken: 'test-access-token', isAuthenticated: true })
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url === '/api/ticket-assignees') return { data: [{ id: engineer.id, full_name: engineer.fullName }] }
      return { data: { items: [{ id: '12345678-1234-1234-1234-123456789abc', title: 'Проверить принтер', description: null, priority: 'high', status: 'new', author: { id: 'author-id', full_name: 'Автор Тестовый' }, assignee: null, asset: null, resolution: null, source: 'web', created_at: '2026-09-02T01:00:00Z', closed_at: null }], total: 1 } }
    })
    render(<MemoryRouter><Tickets /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Заявки' })).toBeInTheDocument()
    expect(await screen.findByText('Заявка 12345678', {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('redirects a web requester role to login because backend web auth forbids it', async () => {
    useAuthStore.setState({ user: requester, accessToken: 'test-access-token', isAuthenticated: true })
    render(<MemoryRouter initialEntries={['/']}><Routes><Route path="/" element={<Dashboard />} /><Route path="/login" element={<div>Вход для сотрудников платформы</div>} /></Routes></MemoryRouter>)
    expect(await screen.findByText('Вход для сотрудников платформы')).toBeInTheDocument()
    expect(screen.queryByText('Активы в работе')).not.toBeInTheDocument()
  })

  it('blocks direct access to a route outside the requester role', async () => {
    useAuthStore.setState({ user: requester, accessToken: 'test-access-token', isAuthenticated: true })
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
