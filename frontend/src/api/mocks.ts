/** Author: Dev2 | Date: 2026-07-16 | Purpose: Local auth adapter used until backend integration. */
import type { AuthUser, LoginPayload, Role } from '../types/auth'

const roleProfiles: Record<string, Omit<AuthUser, 'id' | 'login'>> = {
  admin: { fullName: 'Администратор Тестовый', role: 'Admin', position: 'Администратор платформы', initials: 'АТ' },
  ithead: { fullName: 'Руководитель ИТ', role: 'IT-Head', position: 'Руководитель IT-отдела', initials: 'РИ' },
  engineer: { fullName: 'Инженер Тестовый', role: 'Engineer', position: 'IT-инженер', initials: 'ИТ' },
  executive: { fullName: 'Руководитель Тестовый', role: 'Executive', position: 'Руководство', initials: 'РТ' },
  user: { fullName: 'Сотрудник Тестовый', role: 'User', position: 'Сотрудник', initials: 'СТ' },
}

export const demoAccounts = Object.entries(roleProfiles).map(([login, profile]) => ({
  login,
  role: profile.role as Role,
}))

export async function mockLogin(payload: LoginPayload): Promise<AuthUser> {
  await new Promise((resolve) => window.setTimeout(resolve, 450))
  const profile = roleProfiles[payload.login.trim().toLowerCase()]
  if (!profile || payload.password !== 'demo') {
    throw new Error('Используйте тестовый логин и пароль demo')
  }
  return { id: `mock-${payload.login}`, login: payload.login.toLowerCase(), ...profile }
}
