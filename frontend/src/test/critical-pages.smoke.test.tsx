/** Author: Dev2 | Date: 2026-07-16 | Purpose: F09 RTL smoke coverage for Login, Inventory and Tickets. */
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '../store/authStore'
import Inventory from '../pages/Inventory'
import Login from '../pages/Login'
import Tickets from '../pages/Tickets'

const engineer = { id: 'mock-engineer', login: 'engineer', fullName: 'Инженер Тестовый', role: 'Engineer' as const, position: 'IT-инженер', initials: 'ИТ' }

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
})
