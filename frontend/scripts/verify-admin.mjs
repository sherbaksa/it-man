/** Author: Dev2 | Date: 2026-07-16 | Purpose: Validate F09 local CRUD and secret-free integration contracts. */
globalThis.window = { setTimeout }
const api = await import(new URL('../src/api/admin.ts', import.meta.url))

const initial = await api.getAdminSnapshot()
if (initial.users.length < 5 || initial.departments.length < 1 || initial.templates.length < 1) throw new Error('Admin snapshot is incomplete')
if (initial.integrations.some((item) => 'secret' in item || 'password' in item || 'token' in item)) throw new Error('Integration response exposes a secret-like field')

const created = await api.saveAdminUser({ login: 'qa-user', fullName: 'Тестовый Пользователь', role: 'User', departmentId: initial.departments[0].id })
if (!created.id || created.departmentName !== initial.departments[0].name) throw new Error('User creation failed')
const disabled = await api.setAdminUserActive(created.id, false)
if (disabled.isActive) throw new Error('User deactivation failed')

const directory = await api.saveDirectoryItem('departments', 'Тестовое подразделение')
if (!directory.id) throw new Error('Directory creation failed')
await api.deleteDirectoryItem('departments', directory.id)

const template = await api.setTemplateEnabled(initial.templates[0].id, false)
if (template.isEnabled) throw new Error('Template toggle failed')

console.log(`F09 validation passed: ${initial.users.length} users, CRUD operations, templates and secret-free integrations are valid.`)
